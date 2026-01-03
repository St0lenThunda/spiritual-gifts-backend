import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import User, Organization
from app.neon_auth import get_current_user

client = TestClient(app)

@pytest.fixture
def mock_user(db: Session):
    org = Organization(name="Test Org", slug="test-org", plan="church")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    user = User(email="user@test.com", role="user", org_id=org.id, membership_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def mock_admin(db: Session):
    org = Organization(name="Admin Org", slug="admin-org", plan="church")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    user = User(email="admin@test.com", role="admin", org_id=org.id, membership_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_get_audit_logs_forbidden_for_regular_user(db: Session, mock_user: User):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    response = client.get("/api/v1/audit/logs")
    assert response.status_code == 403
    assert "Only administrators can view audit logs" in response.json()["detail"]
    app.dependency_overrides = {}

def test_get_audit_logs_allowed_for_admin(db: Session, mock_admin: User):
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    response = client.get("/api/v1/audit/logs")
    # Even if no logs exist, it should not be 403
    assert response.status_code == 200
    app.dependency_overrides = {}
