"""
Audit Log router for accessing organizational audit history.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from ..database import get_db
from ..models import AuditLog, User, Organization
from ..neon_auth import get_current_user
from ..services.entitlements import get_plan_features, FEATURE_AUDIT_LOGS

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/logs")
async def get_audit_logs(
    org_id: Optional[UUID] = None,
    actor_id: Optional[int] = None,
    action: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit history.
    - SuperAdmins can see all logs or filter by any org.
    - Org Admins can ONLY see logs for their own org.
    - Requires FEATURE_AUDIT_LOGS entitlement (except for SuperAdmins).
    """
    
    # 1. Determine Access Level
    is_super_admin = False
    is_admin = False
    
    # Check for Roles
    if current_user.role == "super_admin":
        is_super_admin = True
    elif current_user.role == "admin":
        is_admin = True
    
    # Check for System Admin logic for Neon Evangelion (if needed)
    if not is_super_admin and current_user.organization and current_user.organization.slug == "neon-evangelion":
        is_super_admin = True
        
    # Enforce Role-Based Access: Only admins and super admins can view logs
    if not is_super_admin and not is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can view audit logs")
        
    # 2. Enforce Entitlement (unless super admin)
    if not is_super_admin:
        if not current_user.organization:
            raise HTTPException(status_code=403, detail="Must belong to an organization")
            
        features = get_plan_features(current_user.organization.plan)
        if not features.get(FEATURE_AUDIT_LOGS, False):
            raise HTTPException(
                status_code=403, 
                detail=f"Audit Logs are not available on the {current_user.organization.plan} plan."
            )
            
        # 3. Enforce Scoping for non-super admins
        # They MUST filter by their own org_id
        if org_id and str(org_id) != str(current_user.org_id):
            raise HTTPException(status_code=403, detail="Cannot view logs for other organizations")
            
        # Force the org_id to be their own
        query_org_id = current_user.org_id
    else:
        # Super admin can query whatever they passed in
        query_org_id = org_id

    # 4. Build Query
    query = db.query(AuditLog).options(
        joinedload(AuditLog.actor),
        joinedload(AuditLog.organization)
    )
    
    if query_org_id:
        query = query.filter(AuditLog.org_id == query_org_id)
        
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
        
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        
    # Sort by timestamp desc
    query = query.order_by(AuditLog.timestamp.desc())
    
    # 5. Pagination
    total = query.count()
    offset = (page - 1) * limit
    logs = query.offset(offset).limit(limit).all()
    
    # 6. Format Response
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "timestamp": log.timestamp,
            "action": log.action,
            "resource": log.resource,
            "details": log.details, # Assuming frontend handles JSON
            "actor": {
                "id": log.actor.id,
                "email": log.actor.email,
                "role": log.actor.role
            } if log.actor else None,
            "organization": {
                "id": log.organization.id,
                "name": log.organization.name,
                "slug": log.organization.slug
            } if log.organization else None
        })
        
    return {
        "items": results,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
