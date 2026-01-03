import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Organization
from app.database import get_db
from app.neon_auth import get_current_user, UserContext, get_user_context

client = TestClient(app)

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def org_admin():
    org = Organization(id=uuid.uuid4(), name="Admin Org", slug="admin-org", plan="free", is_active=True)
    user = User(id=1, email="admin@example.com", role="admin", org_id=org.id)
    user.organization = org
    return user, org

@pytest.fixture
def normal_user():
    return User(id=2, email="user@example.com", role="user", org_id=None)

# --- Organizations Router Ultra Gaps ---

def test_join_org_already_in_org(mock_db):
    """Line 336: Already associated with an organization."""
    user = User(id=1, email="test@example.com", org_id=uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post("/api/v1/organizations/join/some-slug")
    assert response.status_code == 400
    assert "already associated" in response.json()["detail"]
    app.dependency_overrides = {}

def test_join_org_not_found(mock_db):
    """Line 344: Organization with slug not found."""
    user = User(id=1, email="test@example.com", org_id=None)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.post("/api/v1/organizations/join/ghost-slug")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    app.dependency_overrides = {}

def test_approve_member_rbac(mock_db, org_admin):
    """Line 377: Only admins can approve members."""
    # current_user is NOT admin
    user = User(id=2, email="user@example.com", role="user")
    admin_user, org = org_admin
    
    app.dependency_overrides[get_current_user] = lambda: user
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    response = client.post("/api/v1/organizations/members/1/approve")
    assert response.status_code == 403
    assert "Only admins" in response.json()["detail"]
    app.dependency_overrides = {}

def test_approve_member_not_found(mock_db, org_admin):
    """Line 381: User not found in this organization."""
    admin_user, org = org_admin
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.post("/api/v1/organizations/members/999/approve")
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]
    app.dependency_overrides = {}

def test_approve_member_already_active(mock_db, org_admin):
    """Line 384: User is already active."""
    admin_user, org = org_admin
    target_user = User(id=2, membership_status="active", org_id=org.id)
    
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    mock_db.query.return_value.filter.return_value.first.return_value = target_user
    
    response = client.post("/api/v1/organizations/members/2/approve")
    assert response.status_code == 200
    assert "already active" in response.json()["message"]
    app.dependency_overrides = {}

def test_approve_member_tier_limit(mock_db, org_admin):
    """Line 392: Tier limit reached."""
    admin_user, org = org_admin
    target_user = User(id=2, membership_status="pending", org_id=org.id)
    
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    # First call to filter().first() gets target_user
    # Second call to filter().count() (triggered by line 389) gets count
    mock_db.query.return_value.filter.return_value.first.return_value = target_user
    mock_db.query.return_value.filter.return_value.count.return_value = 10 # Limit is 10
    
    with patch("app.routers.organizations.get_plan_features", return_value={"max_users": 10}):
        response = client.post("/api/v1/organizations/members/2/approve")
        assert response.status_code == 403
        assert "Tier limit" in response.json()["detail"]
    
    app.dependency_overrides = {}

# --- Admin Router Gaps ---

def test_admin_update_user_org_not_found(mock_db):
    """Line 173-174 in admin.py (Organization not found)."""
    super_admin = User(id=99, role="super_admin")
    target_user = User(id=1, email="target@example.com")
    
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import get_current_admin
    app.dependency_overrides[get_current_admin] = lambda: super_admin
    
    # first() called for User, then for Organization
    mock_db.query.return_value.filter.return_value.first.side_effect = [target_user, None]
    
    response = client.patch("/api/v1/admin/users/1", json={"org_id": str(uuid.uuid4())})
    assert response.status_code == 404
    assert "Organization not found" in response.json()["detail"]
    app.dependency_overrides = {}

# --- Organizations Router Extra Gaps ---

def test_reject_member_rbac(mock_db, org_admin):
    """Line 421: Only admins can manage members."""
    user = User(id=2, email="user@example.com", role="user")
    admin_user, org = org_admin
    app.dependency_overrides[get_current_user] = lambda: user
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    response = client.post("/api/v1/organizations/members/1/reject")
    assert response.status_code == 403
    app.dependency_overrides = {}

def test_reject_member_not_found(mock_db, org_admin):
    """Line 425: User not found in this organization."""
    admin_user, org = org_admin
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.post("/api/v1/organizations/members/999/reject")
    assert response.status_code == 404
    app.dependency_overrides = {}

def test_reject_member_self(mock_db, org_admin):
    """Line 429: Cannot reject/remove yourself."""
    admin_user, org = org_admin
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    mock_db.query.return_value.filter.return_value.first.return_value = admin_user
    
    response = client.post(f"/api/v1/organizations/members/{admin_user.id}/reject")
    assert response.status_code == 400
    assert "Cannot reject/remove yourself" in response.json()["detail"]
    app.dependency_overrides = {}

def test_get_member_assessments_rbac(mock_db, org_admin):
    """Line 466: Only organization admins can view member assessments."""
    user = User(id=2, email="user@example.com", role="user")
    admin_user, org = org_admin
    app.dependency_overrides[get_current_user] = lambda: user
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    response = client.get("/api/v1/organizations/me/members/1/assessments")
    assert response.status_code == 403
    app.dependency_overrides = {}

def test_get_member_assessments_not_found(mock_db, org_admin):
    """Line 478: Member not found in this organization."""
    admin_user, org = org_admin
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.neon_auth import require_org
    app.dependency_overrides[require_org] = lambda: org
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/organizations/me/members/999/assessments")
    assert response.status_code == 404
    app.dependency_overrides = {}
