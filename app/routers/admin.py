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
    limit: int = 100,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve system logs from the database.
    Only accessible by administrators.
    """
    logs = db.query(LogEntry).order_by(LogEntry.timestamp.desc()).limit(limit).all()
    
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
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all users in the system.
    Only accessible by administrators.
    """
    return db.query(User).all()
