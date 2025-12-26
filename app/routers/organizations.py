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
)
from ..services.survey_service import SurveyService
from ..neon_auth import get_current_user

router = APIRouter(prefix="/organizations", tags=["Organizations"])


async def get_current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Organization:
    """
    Dependency to get the current user's organization.
    Raises 404 if user is not part of any organization.
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
    
    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )
    
    return org


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
    
    db.commit()
    db.refresh(org)
    
    return org


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    org: Organization = Depends(get_current_org)
):
    """Get the current user's organization."""
    return org


@router.patch("/me", response_model=OrganizationResponse)
async def update_my_organization(
    org_data: OrganizationUpdate,
    org: Organization = Depends(get_current_org),
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
    
    db.commit()
    db.refresh(org)
    
    return org


@router.get("/me/members", response_model=List[dict])
async def list_organization_members(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """List all members of the current organization."""
    members = db.query(User).filter(User.org_id == org.id).all()
    
    return [
        {
            "id": m.id,
            "email": m.email,
            "role": m.role,
            "created_at": m.created_at,
            "last_login": m.last_login
        }
        for m in members
    ]


@router.post("/me/invite", status_code=status.HTTP_202_ACCEPTED)
async def invite_member(
    invite: OrganizationMemberInvite,
    org: Organization = Depends(get_current_org),
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


@router.get("/me/analytics")
async def get_organization_analytics(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Get aggregated analytics for the current organization.
    Available to all organization members, but typically used by admins.
    """
    return SurveyService.get_org_analytics(db, org_id=org.id)


@router.get("/me/members/{member_id}/assessments")
async def get_member_assessments(
    member_id: int,
    org: Organization = Depends(get_current_org),
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
    
    # Get member's assessments
    from ..models import Survey
    assessments = db.query(Survey).filter(
        Survey.user_id == member_id,
        Survey.org_id == org.id
    ).order_by(Survey.created_at.desc()).all()
    
    # Format response with top gift for each assessment
    result = []
    for assessment in assessments:
        scores = assessment.scores or {}
        top_gift = max(scores, key=scores.get) if scores else None
        top_score = scores.get(top_gift, 0) if top_gift else 0
        
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
