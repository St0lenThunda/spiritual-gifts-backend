from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import LogEntry, User

class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        user: User,
        action: str,
        target_type: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None,
        level: str = "INFO"
    ):
        """
        Log a significant action to the database.
        
        Args:
            db: Database session
            user: The user performing the action
            action: Description of the action (e.g., "update_org", "invite_user")
            target_type: The type of entity being affected (e.g., "organization", "user")
            target_id: The ID of the target entity
            details: Additional context data
            level: Log level
        """
        log = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            event=action,
            user_id=user.id,
            user_email=user.email,
            org_id=user.org_id,
            path=f"audit:{target_type}:{target_id}",
            method="AUDIT",
            context=details or {}
        )
        db.add(log)
        # We don't commit here to allow transaction rollbacks if the main action fails
        return log
