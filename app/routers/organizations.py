"""
Organization router for multi-tenant operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..database import get_db
from ..models import Organization, User
from ..schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationMemberInvite,
    OrganizationMemberUpdate,
    OrganizationBulkAction,
    UserResponse,
)
from ..services.survey_service import SurveyService
from ..services.audit_service import AuditService
from ..neon_auth import get_current_user, require_org
from ..services.entitlements import get_plan_features, FEATURE_USERS
from ..logging_setup import logger

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new organization.
    The creating user becomes the organization admin.
    """
    # Check if slug is already taken
    existing = db.query(Organization).filter(Organization.slug == org_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with slug '{org_data.slug}' already exists"
        )
    
    # Create organization
    org = Organization(
        name=org_data.name,
        slug=org_data.slug,
        plan="free"
    )
    db.add(org)
    db.flush()  # Get the org.id
    
    # Associate user with organization as admin
    current_user.org_id = org.id
    current_user.role = "admin"
    current_user.membership_status = "active"
    
    db.commit()
    db.refresh(org)
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="create_org",
        target_type="organization",
        target_id=str(org.id),
        details={"name": org.name, "slug": org.slug}
    )
    
    # Add entitlements to response
    response_org = OrganizationResponse.model_validate(org)
    response_org.entitlements = get_plan_features(org.plan)
    
    return response_org


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's organization.
    Allowed for pending members too so they can see what they applied to.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with any organization"
        )
        
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    response_org = OrganizationResponse.model_validate(org)
    response_org.entitlements = get_plan_features(org.plan)
    return response_org


@router.patch("/me", response_model=OrganizationResponse)
async def update_my_organization(
    org_data: OrganizationUpdate,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current organization.
    Only admins can update organization details.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can update organization details"
        )
    
    if org_data.name is not None:
        org.name = org_data.name
    
    if org_data.branding is not None:
        org.branding = org_data.branding
    
    db.commit()
    db.refresh(org)
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="update_org",
        target_type="organization",
        target_id=str(org.id),
        details=org_data.model_dump(exclude_unset=True)
    )
    
    response_org = OrganizationResponse.model_validate(org)
    response_org.entitlements = get_plan_features(org.plan)
    
    return response_org


@router.get("/me/members", response_model=List[dict])
async def list_organization_members(
    org: Organization = Depends(require_org),
    db: Session = Depends(get_db)
):
    """List all members of the current organization with basic stats."""
    members = db.query(User).filter(User.org_id == org.id).all()
    
    # Pre-fetch assessments for this org members to avoid N+1
    from ..models import Survey
    
    member_ids = [m.id for m in members]
    
    # improved query: fetch surveys for these users regardless of org_id
    # This ensures historical/standalone assessments are included
    org_surveys = db.query(Survey).filter(
        Survey.user_id.in_(member_ids)
    ).order_by(Survey.created_at.desc()).all()
    
    # Map user_id -> list of surveys
    user_surveys = {}
    for survey in org_surveys:
        if survey.user_id not in user_surveys:
            user_surveys[survey.user_id] = []
        user_surveys[survey.user_id].append(survey)
    
    result = []
    for m in members:
        member_surveys = user_surveys.get(m.id, [])
        assessment_count = len(member_surveys)
        
        top_gift = None
        if member_surveys:
            latest_survey = member_surveys[0]
            scores = latest_survey.scores or {}
            if scores:
                # Filter out 'overall' before finding max
                valid_scores = {k: v for k, v in scores.items() if k.lower() != 'overall'}
                if valid_scores:
                    top_gift = max(valid_scores, key=valid_scores.get)
        
        result.append({
            "id": m.id,
            "email": m.email,
            "role": m.role,
            "membership_status": m.membership_status,
            "created_at": m.created_at,
            "last_login": m.last_login,
            "assessment_count": assessment_count,
            "top_gift": top_gift
        })
        
    return result


@router.post("/me/invite", status_code=status.HTTP_202_ACCEPTED)
async def invite_member(
    invite: OrganizationMemberInvite,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invite a new member to the organization.
    Only admins can invite members.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can invite members"
        )
    
    # Tier Enforcement: Check member count
    features = get_plan_features(org.plan)
    max_users = features.get(FEATURE_USERS, 10)
    current_member_count = db.query(User).filter(User.org_id == org.id).count()
    
    if current_member_count >= max_users:
        logger.warning("tier_limit_reached", org_id=str(org.id), limit=max_users, current=current_member_count)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your {org.plan} plan is limited to {max_users} members. Please upgrade to invite more."
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == invite.email).first()
    
    if existing_user:
        if existing_user.org_id == org.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization"
            )
        # TODO: Handle user already in another org
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of another organization"
        )
    
    # TODO: Send invitation email
    # For now, just return success - email integration comes later
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="invite_member",
        target_type="organization",
        target_id=str(org.id),
        details={"email": invite.email, "role": invite.role}
    )
    
    return {
        "message": f"Invitation sent to {invite.email}",
        "status": "pending"
    }


@router.get("/check-slug/{slug}")
async def check_slug_availability(
    slug: str,
    db: Session = Depends(get_db)
):
    """Check if an organization slug is available."""
    existing = db.query(Organization).filter(Organization.slug == slug.lower()).first()
    
    reserved = ["www", "api", "app", "admin", "auth", "billing", "help", "support"]
    is_reserved = slug.lower() in reserved
    
    return {
        "slug": slug.lower(),
        "available": existing is None and not is_reserved,
        "reason": "reserved" if is_reserved else ("taken" if existing else None)
    }


@router.get("/search", response_model=List[dict])
async def search_organizations(
    q: str,
    db: Session = Depends(get_db)
):
    """
    Search for organizations by name or slug.
    Returns a list of matching organizations (public info only).
    """
    if len(q) < 2:
        return []
        
    orgs = db.query(Organization).filter(
        (Organization.name.ilike(f"%{q}%")) | 
        (Organization.slug.ilike(f"%{q}%"))
    ).limit(10).all()
    
    return [
        {
            "name": org.name,
            "slug": org.slug
        }
        for org in orgs
    ]


@router.get("/me/analytics")
async def get_organization_analytics(
    org: Organization = Depends(require_org),
    db: Session = Depends(get_db)
):
    """
    Get aggregated analytics for the current organization.
    Available to all organization members, but typically used by admins.
    """
    return SurveyService.get_org_analytics(db, org_id=org.id)


@router.post("/join/{slug}", status_code=status.HTTP_202_ACCEPTED)
async def join_organization(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request to join an organization.
    The user's status will be set to 'pending' until an admin approves.
    """
    # Check if user already has an org
    if current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already associated with an organization"
        )
    
    # Find org
    org = db.query(Organization).filter(Organization.slug == slug.lower()).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with slug '{slug}' not found"
        )
    
    # Associate user
    current_user.org_id = org.id
    current_user.membership_status = "pending"
    current_user.role = "user"
    
    db.commit()
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="join_request",
        target_type="organization",
        target_id=str(org.id),
        details={"slug": slug}
    )
    
    return {"message": f"Join request sent to {org.name}", "status": "pending"}


@router.post("/members/{user_id}/approve", status_code=status.HTTP_200_OK)
async def approve_member(
    user_id: int,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a pending member."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can approve members")
    
    user = db.query(User).filter(User.id == user_id, User.org_id == org.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this organization")
    
    if user.membership_status == "active":
        return {"message": "User is already active"}
    
    # Tier Check again during approval
    features = get_plan_features(org.plan)
    max_users = features.get(FEATURE_USERS, 10)
    current_member_count = db.query(User).filter(User.org_id == org.id, User.membership_status == "active").count()
    
    if current_member_count >= max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tier limit of {max_users} active members reached. Please upgrade."
        )

    user.membership_status = "active"
    db.commit()
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="approve_member",
        target_type="user",
        target_id=str(user.id),
        details={"email": user.email}
    )
    
    return {"message": f"User {user.email} approved"}


@router.post("/members/{user_id}/reject", status_code=status.HTTP_200_OK)
async def reject_member(
    user_id: int,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a pending member or remove an active member."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage members")
    
    user = db.query(User).filter(User.id == user_id, User.org_id == org.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this organization")
    
    # If rejecting their own request or removing self (handled by separate leave logic usually, but here for admin)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot reject/remove yourself")

    user.org_id = None
    user.membership_status = "active" # Reset for their next attempt/standalone use
    user.role = "user"
    
    db.commit()
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="reject_member",
        target_type="user",
        target_id=str(user.id),
        details={"email": user.email}
    )
    
    return {"message": f"User {user.email} removed/rejected"}


@router.get("/me/members/{member_id}/assessments")
async def get_member_assessments(
    member_id: int,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get assessment history for a specific organization member.
    Only admins can access member assessment data.
    """
    # Verify current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can view member assessments"
        )
    
    # Verify the member belongs to the same organization
    member = db.query(User).filter(
        User.id == member_id,
        User.org_id == org.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization"
        )
    
    # Get member's assessments - fetch all for this user regardless of org context
    from ..models import Survey
    assessments = db.query(Survey).filter(
        Survey.user_id == member_id
    ).order_by(Survey.created_at.desc()).all()
    
    # Format response with top gift for each assessment
    result = []
    for assessment in assessments:
        scores = assessment.scores or {}
        # Filter out 'overall' before finding max
        valid_scores = {k: v for k, v in scores.items() if k.lower() != 'overall'}
        top_gift = max(valid_scores, key=valid_scores.get) if valid_scores else None
        top_score = valid_scores.get(top_gift, 0) if top_gift else 0
        
        result.append({
            "id": assessment.id,
            "created_at": assessment.created_at,
            "scores": scores,
            "top_gift": top_gift,
            "top_score": top_score
        })
    
    return {
        "member": {
            "id": member.id,
            "email": member.email,
            "role": member.role,
            "created_at": member.created_at,
            "last_login": member.last_login
        },
        "assessments": result,
        "total_assessments": len(result)
    }

@router.patch("/members/{user_id}", response_model=UserResponse)
async def update_organization_member(
    user_id: int,
    member_data: OrganizationMemberUpdate,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a member's role within the organization.
    Only accessible by organization administrators.
    """
    # Ensure current user is an admin of this org
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only organization admins can update members")
        
    user = db.query(User).filter(User.id == user_id, User.org_id == org.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found in your organization")
        
    if member_data.role:
        user.role = member_data.role
        
    db.commit()
    db.refresh(user)
    
    AuditService.log_action(
        db=db,
        user=current_user,
        action="member_updated_by_org_admin",
        target_type="user",
        target_id=str(user.id),
        details={
            "target_user_email": user.email,
            "new_role": user.role
        },
        level="INFO"
    )
    
    return user


@router.post("/members/bulk-approve", status_code=status.HTTP_200_OK)
async def bulk_approve_members(
    action: OrganizationBulkAction,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve multiple pending members."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can approve members")
    
    # Tier Check
    features = get_plan_features(org.plan)
    max_users = features.get(FEATURE_USERS, 10)
    current_active_count = db.query(User).filter(User.org_id == org.id, User.membership_status == "active").count()
    
    available_slots = max_users - current_active_count
    
    users = db.query(User).filter(
        User.id.in_(action.user_ids), 
        User.org_id == org.id,
        User.membership_status == "pending"
    ).all()
    
    if not users:
        return {"message": "No pending members found to approve", "approved_count": 0}
    
    if len(users) > available_slots:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tier limit reached. You only have {available_slots} slots available, but tried to approve {len(users)} users."
        )
    
    approved_emails = []
    for user in users:
        user.membership_status = "active"
        approved_emails.append(user.email)
        
        AuditService.log_action(
            db=db,
            user=current_user,
            action="approve_member",
            target_type="user",
            target_id=str(user.id),
            details={"email": user.email, "bulk": True}
        )
    
    db.commit()
    return {"message": f"Successfully approved {len(approved_emails)} members", "approved_count": len(approved_emails)}


@router.post("/members/bulk-reject", status_code=status.HTTP_200_OK)
async def bulk_reject_members(
    action: OrganizationBulkAction,
    org: Organization = Depends(require_org),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject multiple members."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage members")
    
    users = db.query(User).filter(
        User.id.in_(action.user_ids), 
        User.org_id == org.id
    ).all()
    
    rejected_count = 0
    for user in users:
        # Prevent self-rejection
        if user.id == current_user.id:
            continue
            
        user.org_id = None
        user.membership_status = "active"
        user.role = "user"
        rejected_count += 1
        
        AuditService.log_action(
            db=db,
            user=current_user,
            action="reject_member",
            target_type="user",
            target_id=str(user.id),
            details={"email": user.email, "bulk": True}
        )
    
    db.commit()
    return {"message": f"Successfully removed/rejected {rejected_count} members", "rejected_count": rejected_count}
