import pytest
from app.models import AuditLog, User, Organization
from datetime import datetime

@pytest.fixture
def org(db):
    """Create a demo organization for testing."""
    org = Organization(name="Test Org", slug="test-org", plan="church")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

@pytest.fixture
def user(db, org):
    """Create a demo user linked to the organization."""
    user = User(email="audit_user@example.com", role="admin", org_id=org.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_audit_log_creation(db, user, org):
    """Verify that an AuditLog entry can be created and persisted correctly."""
    entry = AuditLog(
        actor_id=user.id,
        org_id=org.id,
        action="test_action",
        resource="test_resource",
        timestamp=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Retrieve from DB and assert fields
    fetched = db.query(AuditLog).filter(AuditLog.id == entry.id).first()
    assert fetched is not None
    assert fetched.actor_id == user.id
    assert fetched.org_id == org.id
    assert fetched.action == "test_action"
    assert fetched.resource == "test_resource"
    assert isinstance(fetched.timestamp, datetime)
