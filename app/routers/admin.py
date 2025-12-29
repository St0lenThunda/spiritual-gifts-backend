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
    
    # Org admins can only see logs from their organization's users
    # Super admins see all logs
    allowed_emails = ["tonym415@gmail.com"]
    allowed_org_slugs = ["neon-evangelion"]
    is_super_admin = current_admin.email in allowed_emails
    if not is_super_admin and current_admin.organization:
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
    
    # Org admins can only see users from their organization
    # Super admins see all users
    allowed_emails = ["tonym415@gmail.com"]
    allowed_org_slugs = ["neon-evangelion"]
    is_super_admin = current_admin.email in allowed_emails
    if not is_super_admin and current_admin.organization:
        if current_admin.organization.slug in allowed_org_slugs:
            is_super_admin = True
    
    if not is_super_admin and context.organization:
        query = query.filter(User.org_id == context.organization.id)
    
    # Filtering
    if role:
        query = query.filter(User.role == role.lower())
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
        
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
