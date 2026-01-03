from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import User, Organization
from app.services.audit_service import AuditService
from datetime import datetime
import pytest

def test_reproduce_audit_crash():
    db = SessionLocal()
    try:
        # Create Dummy User/Org
        user = db.query(User).first()
        if not user:
            # Create if empty
            user = User(email="repro@test.com", role="admin")
            db.add(user)
            db.commit()
            db.refresh(user)
            
        print(f"Using user: {user.id}")
        
        # Action
        details_dict = {"email": "nathan.c@harvestpoint.church", "bulk": True}
        
        print("Logging action...")
        AuditService.log_action(
            db=db,
            user=user,
            action="repro_action",
            target_type="user",
            target_id="999",
            details=details_dict
        )
        
        print("Committing...")
        db.commit()
        print("Success!")
        
    except Exception as e:
        print(f"FAILED: {e}")
        pytest.fail(f"Crash reproduced: {e}")
    finally:
        db.close()
