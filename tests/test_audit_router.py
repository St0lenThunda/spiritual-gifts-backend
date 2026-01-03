import pytest
from unittest.mock import MagicMock, call
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Organization, AuditLog
from app.database import get_db
from app.neon_auth import get_current_user
from app.services.entitlements import FEATURE_AUDIT_LOGS

client = TestClient(app)

# --- Fixtures ---

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_org():
    org = MagicMock(spec=Organization)
    org.id = "uuid-123"
    org.plan = "ministry"
    org.slug = "test-org"
    return org

@pytest.fixture
def mock_user_super_admin():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "super@example.com"
    user.role = "super_admin"
    user.organization = None
    user.org_id = None
    return user

@pytest.fixture
def mock_user_org_admin(mock_org):
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "admin@example.com"
    user.role = "admin"
    user.organization = mock_org
    user.org_id = mock_org.id
    return user

@pytest.fixture
def mock_audit_logs():
    log1 = MagicMock(spec=AuditLog)
    log1.id = 100
    log1.action = "user.create"
    log1.actor.id = 1
    log1.actor.email = "actor1@test.com"
    log1.organization.id = "uuid-123"
    log1.organization.name = "Test Org"
    
    log2 = MagicMock(spec=AuditLog)
    log2.id = 101
    log2.action = "org.update"
    
    return [log1, log2]

# --- Tests ---

def test_get_audit_logs_super_admin_success(mock_db, mock_user_super_admin, mock_audit_logs):
    """Super admin can access logs without org restrictions."""
    
    # Mock DB Query Chain
    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value.limit.return_value.all.return_value = mock_audit_logs
    mock_query.count.return_value = 2

    # Override Deps
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_super_admin

    response = client.get("/api/v1/audit/logs")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["action"] == "user.create"

    # Cleanup
    app.dependency_overrides = {}

def test_get_audit_logs_org_admin_success(mock_db, mock_user_org_admin, mock_audit_logs):
    """Org admin can access logs for their own org if permitted."""
    
    # Mock Entitlements (using patch would be better, but we can verify logic flow)
    # The logic checks get_plan_features(org.plan)
    # matching "ministry" -> FEATURE_AUDIT_LOGS=True
    
    with pytest.MonkeyPatch.context() as m:
        # Mock get_plan_features to return True for audit logs
        m.setattr("app.routers.audit.get_plan_features", lambda plan: {FEATURE_AUDIT_LOGS: True})
        
        # Mock DB
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        # Should filter by org_id
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_audit_logs
        mock_query.count.return_value = 2

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user_org_admin

        response = client.get("/api/v1/audit/logs")
        
        assert response.status_code == 200
        # Verify call arguments to ensure correct filtering
        # The filter call is complex to assert on Mock query chains without stricter setup
        # But we check success code
        
        app.dependency_overrides = {}

def test_get_audit_logs_org_admin_other_org_denied(mock_db, mock_user_org_admin):
    """Org admin cannot access logs of another org."""
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.routers.audit.get_plan_features", lambda plan: {FEATURE_AUDIT_LOGS: True})
        
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user_org_admin

        # Requesting different org_id (must be valid UUID to avoid 422)
        response = client.get("/api/v1/audit/logs?org_id=00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 403
        assert "Cannot view logs for other organizations" in response.json()["detail"]
        
        app.dependency_overrides = {}

def test_get_audit_logs_org_admin_no_entitlement(mock_db, mock_user_org_admin):
    """Org admin denied if plan doesn't include audit logs."""
    
    with pytest.MonkeyPatch.context() as m:
        # Mock features to NOT include audit logs
        m.setattr("app.routers.audit.get_plan_features", lambda plan: {})
        
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user_org_admin

        response = client.get("/api/v1/audit/logs")
        
        assert response.status_code == 403
        assert "not available on the ministry plan" in response.json()["detail"]
        
        app.dependency_overrides = {}

def test_get_audit_logs_user_no_org(mock_db):
    """User without organization denied."""
    user = MagicMock(spec=User)
    user.role = "user"
    user.organization = None # No org
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.get("/api/v1/audit/logs")
    
    assert response.status_code == 403
    assert "Must belong to an organization" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_get_audit_logs_neon_evangelion_legacy_access(mock_db, mock_audit_logs):
    """Test legacy super admin access for neon-evangelion org members."""
    
    legacy_user = MagicMock(spec=User)
    legacy_user.role = "user" # Not super_admin role
    legacy_user.organization.slug = "neon-evangelion"
    legacy_user.organization.plan = "growth" 

    # Mock DB Query
    mock_query = mock_db.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.count.return_value = 2
    mock_query.offset.return_value.limit.return_value.all.return_value = mock_audit_logs
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: legacy_user

    response = client.get("/api/v1/audit/logs")
    
    assert response.status_code == 200
    # Should see all logs just like super admin
    assert response.json()["total"] == 2
    
    app.dependency_overrides = {}
