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
