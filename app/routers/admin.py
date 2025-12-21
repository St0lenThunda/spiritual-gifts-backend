"""
Admin router for Spiritual Gifts Assessment.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..neon_auth import get_current_admin
from ..database import get_db
from ..models import LogEntry, User
from .. import schemas

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/logs", response_model=List[dict])
async def get_system_logs(
    level: str = None,
    user_email: str = None,
    event: str = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    limit: int = 100,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve system logs from the database with filtering and sorting.
    Only accessible by administrators.
    """
    query = db.query(LogEntry)
    
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
        
    logs = query.order_by(sort_attr).limit(limit).all()
    
    # Convert to dict for easier response handling
    result = []
    for log in logs:
        result.append({
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
    return result

@router.get("/users", response_model=List[schemas.UserResponse])
async def list_all_users(
    role: str = None,
    email: str = None,
    sort_by: str = "id",
    order: str = "asc",
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all users in the system with filtering and sorting.
    Only accessible by administrators.
    """
    query = db.query(User)
    
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
        
    return query.order_by(sort_attr).all()

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
