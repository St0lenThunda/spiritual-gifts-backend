from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from app.models import LogEntry, User, AuditLog

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
        safe_details = jsonable_encoder(details) if details else {}
        # Create user-facing AuditLog
        audit = AuditLog(
            timestamp=datetime.utcnow(),
            actor_id=user.id,
            org_id=user.org_id, 
            action=action,
            resource=f"{target_type}:{target_id}",
            details=safe_details
            # Let me re-check model definition in Step 2194 lines 104-121.
            # It has: actor_id, org_id, action, resource, timestamp.
            # It DOES NOT HAVE 'details' column!
            # But LogEntry HAS context/details.
            # I need to add 'details' column to AuditLog model first? 
            # Or map 'context' to 'details'? 
            # Wait, router/audit.py (Step 2134) line 97 accesses `log.details`.
            # If `AuditLog` model doesn't have `details`, that router code would fail if it ran.
            # But earlier verification test PASSED?
            # Why did verification test pass?
            # Test Step 2136: 
            # `log = db.query(AuditLog).filter(AuditLog.action == "test_action_123").first()`
            # It didn't check details column existence explicitly on the object, just existence of row.
            # AND I used `AuditService.log_action` in the test. 
            # `AuditService.log_action` writes `LogEntry`.
            # So `db.query(AuditLog)` in the test should have returned NONE if they are different tables!
            
            # Wait. Step 2136 test code:
            # `log = db.query(AuditLog)...`
            # If AuditService writes LogEntry (table `log_entries`), then `db.query(AuditLog)` (table `audit_logs`) should find NOTHING.
            # The test SHOULD have failed.
            # Did I misread Step 2141 output? "The command completed successfully." with no stderr.
            # Pytest exit code 0 means tests passed.
            # If `log` was None, `assert log is not None` would fail.
            # This implies `AuditService` IS writing to `AuditLog`.
            # Let me re-read `AuditService.py` (Step 2190).
            # Line 29: `log = LogEntry(...)`.
            # Line 4: `from app.models import LogEntry, User`.
            # It does NOT import AuditLog.
            
            # HOW DID THE TEST PASS? 
            # Maybe `LogEntry` and `AuditLog` point to the SAME table?
            # Step 2194:
            # LogEntry: `__tablename__ = "log_entries"`
            # AuditLog: `__tablename__ = "audit_logs"`
            # They are DIFFERENT.
            
            # Possibility: The test file I wrote imports `AuditLog` but maybe `AuditService` was modified in previous sessions?
            # Step 2190 SHOWS `AuditService` using `LogEntry`.
            
            # Is it possible the test failed but I missed it? 
            # "The command completed successfully." usually implies exit code 0.
            # If assertions failed, it would be exit code 1.
            
            # Let me re-verify the test failure by running it again and looking closely.
            # Or maybe I am reading an old version of `AuditService`?
            # No, `view_file` is authoritative.
            
            # Okay, I will fix `AuditService` to write to `AuditLog`.
            # AND I need to check if `AuditLog` has a `details` column. 
            # Step 2194 lines 104-121 does NOT show `details` column. 
            # Router line 97 accesses `log.details`. This returns an AttributeError at runtime if not present.
            # So the router IS broken?
            
            # I must add `details` column to `AuditLog` model first.
        )
        db.add(audit)
        
        # Create system-facing LogEntry (redundancy required by user)
        system_log = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            event=action,
            user_id=user.id,
            user_email=user.email,
            org_id=user.org_id,
            context=safe_details,
            path="audit_service", # Generic path
            method="AUDIT"
        )
        db.add(system_log)
        
        return audit
