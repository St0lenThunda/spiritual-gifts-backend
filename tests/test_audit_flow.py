from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, Base, engine
from app.models import User, Organization, AuditLog
from app.services.audit_service import AuditService
from uuid import uuid4

def test_audit_flow():
    # Setup
    # Create tables if not exist (using test db usually)
    # Drop table to ensure new schema (details column) is applied
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS audit_logs"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as db:
        # 1. Create dummy Org and User
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Audit Test Org",
            slug=f"audit-test-{org_id}",
            plan="ministry", # Entitled
            is_active=True
        )
        db.add(org)
        
        user = User(
            email=f"tester-{org_id}@example.com",
            role="admin",
            org_id=org_id,
            membership_status="active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 2. Log an action
        AuditService.log_action(
            db=db,
            user=user,
            action="test_action_123",
            target_type="organization",
            target_id=str(org.id),
            details={"foo": "bar"}
        )
        
        # 3. Verify it exists in DB
        log = db.query(AuditLog).filter(AuditLog.action == "test_action_123").first()
        assert log is not None
        assert log.org_id == org_id
        assert log.actor_id == user.id
        
        # 4. Clean up
        db.delete(log)
        db.delete(user)
        db.delete(org)
        db.commit()
