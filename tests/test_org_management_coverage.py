import pytest
from unittest.mock import MagicMock, call, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Organization
from app.database import get_db
from app.neon_auth import get_current_user, require_org
from app.services.entitlements import FEATURE_BULK_ACTIONS

client = TestClient(app)

# --- Fixtures ---

@pytest.fixture
def mock_db():
    return MagicMock()

import uuid

@pytest.fixture
def mock_org():
    org = MagicMock(spec=Organization)
    org.id = uuid.uuid4()
    org.slug = "existing-slug"
    org.name = "Test Organization"
    org.plan = "ministry"
    org.branding = {}
    org.denomination_id = None
    org.created_at = "2023-01-01T00:00:00"
    org.updated_at = "2023-01-01T00:00:00"
    org.stripe_customer_id = "cus_test"
    org.theme_id = None
    org.is_demo = False
    org.is_active = True
    org.denomination = None
    return org

@pytest.fixture
def mock_user_admin(mock_org):
    user = MagicMock(spec=User)
    user.role = "admin"
    user.org_id = mock_org.id
    user.organization = mock_org
    return user

# --- Tests ---

def test_create_organization_slug_conflict(mock_db, mock_user_admin):
    """Test creating org with existing slug."""
    # Setup query to return existing org
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    response = client.post(
        "/api/v1/organizations",
        json={"name": "New Org", "slug": "existing-slug"}
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_get_my_organization_no_association(mock_db):
    """Test get_my_organization when user has no org_id."""
    user = MagicMock(spec=User)
    user.org_id = None
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.get("/api/v1/organizations/me")
    
    assert response.status_code == 404
    assert "not associated" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_get_my_organization_not_found(mock_db):
    """Test get_my_organization when org_id exists but DB record missing."""
    user = MagicMock(spec=User)
    user.org_id = "uuid-ghost"
    
    # Return None for org query
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.get("/api/v1/organizations/me")
    
    assert response.status_code == 404
    assert "Organization not found" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_update_organization_denomination(mock_db, mock_org, mock_user_admin):
    """Test updating organization denomination."""
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    app.dependency_overrides[require_org] = lambda: mock_org
    
    with patch("app.routers.organizations.AuditService.log_action"), \
         patch("app.routers.organizations.get_plan_features", return_value={"feature": True}):
        response = client.patch(
            "/api/v1/organizations/me",
            json={"denomination_id": "00000000-0000-0000-0000-000000000000"}
        )
        
        if response.status_code != 200:
            print(f"Response: {response.text}")
            
        assert response.status_code == 200
        assert str(mock_org.denomination_id) == "00000000-0000-0000-0000-000000000000"
        mock_db.commit.assert_called()
    
    app.dependency_overrides = {}

def test_bulk_action_activate_success(mock_db, mock_org, mock_user_admin):
    """Test successful bulk activation action."""
    
    # Mock Features for Bulk Actions
    with patch("app.routers.organizations.get_plan_features", return_value={FEATURE_BULK_ACTIONS: True}), \
         patch("app.routers.organizations.AuditService.log_action"):
        
        # Mock Members
        user1 = MagicMock(spec=User, id=101, membership_status="pending")
        user2 = MagicMock(spec=User, id=102, membership_status="pending")
        
        mock_db.query.return_value.filter.return_value.all.return_value = [user1, user2]
        # Valid active count to allow approval
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user_admin
        app.dependency_overrides[require_org] = lambda: mock_org
        
        response = client.post(
            "/api/v1/organizations/members/bulk-approve",
            json={"user_ids": [101, 102], "action": "approve"}
        )
        
        assert response.status_code == 200
        assert user1.membership_status == "active"
        assert user2.membership_status == "active"
        
    app.dependency_overrides = {}

def test_bulk_action_delete_not_allowed(mock_db, mock_org, mock_user_admin):
    """Test bulk delete action (not allowed usually or specific check)."""
    # Assuming delete is valid action, checking logic flow
    pass
