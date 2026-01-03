"""
Admin router for Spiritual Gifts Assessment.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..neon_auth import get_current_admin, get_org_admin, UserContext, get_user_context
from ..database import get_db
from ..models import LogEntry, User, Organization
from .. import schemas
from ..services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/logs")
async def get_system_logs(
    level: str = None,
    user_email: str = None,
    event: str = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    page: int = 1,
    limit: int = 20,
    context: UserContext = Depends(get_user_context),
    current_admin: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve system logs from the database with filtering, sorting, and pagination.
    Only accessible by administrators.
    """
    query = db.query(LogEntry)
    
    # Super admins see all logs
    is_super_admin = current_admin.role == "super_admin"
    
    if not is_super_admin and current_admin.organization:
        # Fallback for Neon Evangelion org members (Legacy)
        allowed_org_slugs = ["neon-evangelion"]
        if current_admin.organization.slug in allowed_org_slugs:
            is_super_admin = True
    
    if not is_super_admin and context.organization:
        # Filter logs by organization ID
        query = query.filter(LogEntry.org_id == context.organization.id)
    
    # Filtering
    if level:
        query = query.filter(LogEntry.level == level.upper())
    if user_email:
        query = query.filter(LogEntry.user_email.ilike(f"%{user_email}%"))
    if event:
        query = query.filter(LogEntry.event.ilike(f"%{event}%"))
        
    # Sorting
    if order.lower() == "desc":
        sort_attr = getattr(LogEntry, sort_by).desc()
    else:
        sort_attr = getattr(LogEntry, sort_by).asc()
        
    # Calculate totals
    total = query.count()
    pages = (total + limit - 1) // limit
    
    # Pagination
    offset = (page - 1) * limit
    logs = query.order_by(sort_attr).offset(offset).limit(limit).all()
    
    # Convert to dict for easier response handling
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "level": log.level,
            "event": log.event,
            "user_email": log.user_email,
            "path": log.path,
            "method": log.method,
            "status_code": log.status_code,
            "exception": log.exception,
            "context": log.context
        })
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }

@router.get("/users")
async def list_all_users(
    role: str = None,
    email: str = None,
    org_id: str = None,
    sort_by: str = "id",
    order: str = "asc",
    page: int = 1,
    limit: int = 20,
    context: UserContext = Depends(get_user_context),
    current_admin: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """
    List all users in the system with filtering, sorting, and pagination.
    Only accessible by administrators.
    """
    query = db.query(User)
    
    # Super admins see all users
    is_super_admin = current_admin.role == "super_admin"
    
    if not is_super_admin and current_admin.organization:
        # Fallback for Neon Evangelion org members (Legacy)
        allowed_org_slugs = ["neon-evangelion"]
        if current_admin.organization.slug in allowed_org_slugs:
            is_super_admin = True
    
    if not is_super_admin and context.organization:
        query = query.filter(User.org_id == context.organization.id)
    
    # Filtering
    if role:
        query = query.filter(User.role == role.lower())
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if org_id and is_super_admin:
        from uuid import UUID
        try:
            org_uuid = UUID(org_id)
            query = query.filter(User.org_id == org_uuid)
        except ValueError:
            pass  # Invalid UUID, ignore filter
        
    # Sorting
    if order.lower() == "desc":
        sort_attr = getattr(User, sort_by).desc()
    else:
        sort_attr = getattr(User, sort_by).asc()

    # Calculate totals
    total = query.count()
    pages = (total + limit - 1) // limit

    # Pagination
    offset = (page - 1) * limit
    users = query.order_by(sort_attr).offset(offset).limit(limit).all()
        
    return {
        "items": users,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }

@router.patch("/users/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: int,
    user_data: schemas.UserUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update a user's role, organization, or membership status.
    Only accessible by system administrators.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_data.role is not None:
        user.role = user_data.role
        
    if user_data.org_id is not None:
        # Verify organization exists
        org = db.query(Organization).filter(Organization.id == user_data.org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        user.org_id = user_data.org_id
        
    if user_data.membership_status is not None:
        user.membership_status = user_data.membership_status
        
    db.commit()
    db.refresh(user)
    
    AuditService.log_action(
        db=db,
        user=current_admin,
        action="user_updated_by_admin",
        target_type="user",
        target_id=str(user.id),
        details={
            "target_user_email": user.email,
            "updates": user_data.model_dump(exclude_unset=True)
        },
        level="INFO"
    )
    
    return user

@router.get("/schema", response_model=dict)
async def get_db_schema(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    Generates a Mermaid ERD string representing the database schema.
    Only accessible by administrators.
    """
    from sqlalchemy.inspection import inspect
    from ..database import Base
    
    mermaid_lines = ["erDiagram"]
    
    # We want to inspect all models registered with Base
    for table_name, table in Base.metadata.tables.items():
        # Entity start
        mermaid_lines.append(f"    {table_name} {{")
        
        for column in table.columns:
            # Map SQL types to simplified Mermaid/Java types
            col_type = str(column.type).split('(')[0].lower()
            if 'int' in col_type:
                type_label = "int"
            elif 'string' in col_type or 'varchar' in col_type or 'text' in col_type:
                type_label = "string"
            elif 'datetime' in col_type or 'timestamp' in col_type:
                type_label = "datetime"
            elif 'json' in col_type:
                type_label = "json"
            else:
                type_label = col_type
                
            pk_label = "PK" if column.primary_key else ""
            fk_label = "FK" if column.foreign_keys else ""
            labels = f"{pk_label} {fk_label}".strip()
            
            mermaid_lines.append(f"        {type_label} {column.name} {labels}")
            
        mermaid_lines.append("    }")

    # Identify relationships
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            for fk in column.foreign_keys:
                target_table = fk.column.table.name
                # Simple ERD relationship: 1-to-many usually
                # table_name contains the FK, so it's the "many" side
                # target_table is the "one" side
                mermaid_lines.append(f"    {target_table} ||--o{{ {table_name} : \"{column.name}\"")

    return {"mermaid": "\n".join(mermaid_lines)}

# ============================================================================
# Organization Management (Super Admin Only)
# ============================================================================

@router.get("/organizations")
async def list_all_organizations(
    sort_by: str = "name",
    order: str = "asc",
    page: int = 1,
    limit: int = 25,
    plan: str = None,
    is_active: str = None,
    search: str = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all organizations in the system with sorting, filtering, and pagination.
    Only accessible by super administrators.
    """
    query = db.query(Organization)
    
    # Filtering
    if plan:
        query = query.filter(Organization.plan == plan)
    if is_active is not None and is_active != '':
        query = query.filter(Organization.is_active == (is_active.lower() == 'true'))
    if search:
        query = query.filter(
            (Organization.name.ilike(f"%{search}%")) | 
            (Organization.slug.ilike(f"%{search}%"))
        )
    
    # Sorting
    if order.lower() == "desc":
        sort_attr = getattr(Organization, sort_by).desc()
    else:
        sort_attr = getattr(Organization, sort_by).asc()
    
    # Calculate totals
    total = query.count()
    pages = (total + limit - 1) // limit
    
    # Pagination
    offset = (page - 1) * limit
    orgs = query.order_by(sort_attr).offset(offset).limit(limit).all()
    
    # Convert to dict with member counts
    items = []
    for org in orgs:
        member_count = db.query(User).filter(User.org_id == org.id).count()
        items.append({
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "is_active": org.is_active,
            "is_demo": org.is_demo,
            "member_count": member_count,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            "stripe_customer_id": org.stripe_customer_id
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }

@router.get("/organizations/{org_id}")
async def get_organization_details(
    org_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a single organization.
    Only accessible by super administrators.
    """
    from uuid import UUID
    try:
        org_uuid = UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID")
    
    org = db.query(Organization).filter(Organization.id == org_uuid).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    member_count = db.query(User).filter(User.org_id == org.id).count()
    
    result = {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "is_active": org.is_active,
        "is_demo": org.is_demo,
        "member_count": member_count,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
        "stripe_customer_id": org.stripe_customer_id,
        "denomination": None
    }
    
    # Include denomination if present
    if org.denomination:
        result["denomination"] = {
            "id": str(org.denomination.id),
            "display_name": org.denomination.display_name,
            "slug": org.denomination.slug,
            "default_currency": org.denomination.default_currency
        }
    
    return result


@router.post("/organizations")
async def create_organization(
    org_data: schemas.OrganizationCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new organization.
    Only accessible by super administrators.
    """
    # Check if slug is already taken
    existing = db.query(Organization).filter(Organization.slug == org_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organization with slug '{org_data.slug}' already exists"
        )
    
    org = Organization(
        name=org_data.name,
        slug=org_data.slug,
        plan="free"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    AuditService.log_action(
        db=db,
        user=current_admin,
        action="admin_create_org",
        target_type="organization",
        target_id=str(org.id),
        details={"name": org.name, "slug": org.slug}
    )
    
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "is_active": org.is_active,
        "created_at": org.created_at.isoformat() if org.created_at else None
    }

@router.patch("/organizations/{org_id}")
async def update_organization(
    org_id: str,
    org_data: schemas.OrganizationUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update an organization.
    Only accessible by super administrators.
    """
    from uuid import UUID
    try:
        org_uuid = UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID")
    
    org = db.query(Organization).filter(Organization.id == org_uuid).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org_data.name is not None:
        org.name = org_data.name
    if org_data.branding is not None:
        org.branding = org_data.branding
    if hasattr(org_data, 'plan') and org_data.plan is not None:
        org.plan = org_data.plan
    if hasattr(org_data, 'is_active') and org_data.is_active is not None:
        org.is_active = org_data.is_active
    
    db.commit()
    db.refresh(org)
    
    AuditService.log_action(
        db=db,
        user=current_admin,
        action="admin_update_org",
        target_type="organization",
        target_id=str(org.id),
        details=org_data.model_dump(exclude_unset=True)
    )
    
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "is_active": org.is_active,
        "updated_at": org.updated_at.isoformat() if org.updated_at else None
    }
