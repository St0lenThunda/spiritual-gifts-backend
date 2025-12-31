import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import Organization, User, AuditLog
from app.neon_auth import UserContext

client = TestClient(app)

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_admin():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "admin@example.com"
    user.role = "admin"
    user.org_id = uuid.uuid4()
    user.membership_status = "active"
    return user

@pytest.fixture
def mock_org(mock_admin):
    org = MagicMock(spec=Organization)
    org.id = mock_admin.org_id
    org.name = "Test Org"
    org.plan = "ministry"
    org.is_active = True
    return org

class TestBulkActions:
    @pytest.fixture(autouse=True)
    def setup_auth(self, mock_admin, mock_org, mock_db):
        from app.database import get_db
        from app.neon_auth import get_current_user, require_org
        
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[require_org] = lambda: mock_org
        
        yield
        app.dependency_overrides.clear()

    def test_bulk_approve_success(self, mock_admin, mock_org, mock_db):
        # Mock pending members
        user2 = MagicMock(spec=User)
        user2.id = 2
        user2.membership_status = "pending"
        user2.org_id = mock_org.id
        
        user3 = MagicMock(spec=User)
        user3.id = 3
        user3.membership_status = "pending"
        user3.org_id = mock_org.id

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Mock sequence of calls: count then all pending users
        # 1. count() for tier check (total active members)
        # 2. filter(...).all() for finding users to approve
        mock_query.count.return_value = 1 # Only admin is active
        mock_query.all.return_value = [user2, user3]

        response = client.post(
            "/api/v1/organizations/members/bulk-approve",
            json={"user_ids": [2, 3]}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Successfully approved 2 members"
        assert user2.membership_status == "active"
        assert user3.membership_status == "active"
        assert mock_db.commit.called

    def test_bulk_reject_success(self, mock_admin, mock_org, mock_db):
        user2 = MagicMock(spec=User)
        user2.id = 2
        user2.org_id = mock_org.id
        
        user3 = MagicMock(spec=User)
        user3.id = 3
        user3.org_id = mock_org.id

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [user2, user3]

        response = client.post(
            "/api/v1/organizations/members/bulk-reject",
            json={"user_ids": [2, 3]}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Successfully removed/rejected 2 members"
        assert user2.org_id is None
        assert user2.membership_status == "active" # Reset to individual
        assert user2.role == "user"
        assert mock_db.commit.called

    def test_bulk_approve_locked_on_free_tier(self, mock_admin, mock_org, mock_db):
        # Free plan doesn't support bulk actions at all
        mock_org.plan = "free"
        
        response = client.post(
            "/api/v1/organizations/members/bulk-approve",
            json={"user_ids": [10, 11]}
        )

        assert response.status_code == 403
        assert "bulk actions are not available on the free plan" in response.json()["detail"].lower()

    def test_bulk_approve_tier_limit_on_ministry(self, mock_admin, mock_org, mock_db):
        # Ministry plan supports bulk actions but has a limit (e.g., 100 users)
        mock_org.plan = "ministry"
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # 100 active members already
        mock_query.count.return_value = 100
        
        user100 = MagicMock(spec=User)
        user100.id = 100
        mock_query.all.return_value = [user100]

        response = client.post(
            "/api/v1/organizations/members/bulk-approve",
            json={"user_ids": [100]}
        )

        assert response.status_code == 403
        assert "tier limit reached" in response.json()["detail"].lower()

    def test_update_member_role_success(self, mock_admin, mock_org, mock_db):
        user2 = MagicMock(spec=User)
        user2.id = 2
        user2.org_id = mock_org.id
        user2.role = "user"
        user2.email = "user2@example.com"
        user2.membership_status = "active"
        user2.created_at = datetime.utcnow()
        user2.last_login = None
        user2.global_preferences = {}

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = user2

        response = client.patch(
            "/api/v1/organizations/members/2",
            json={"role": "admin"}
        )

        assert response.status_code == 200
        assert user2.role == "admin"
        assert mock_db.commit.called
