import pytest
from fastapi import HTTPException, status
from unittest.mock import MagicMock, patch
from app.neon_auth import get_user_context, UserContext
from app.models import Organization, User
from app.services.auth_service import AuthService

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.mark.asyncio
async def test_demo_org_read_only_enforcement(mock_db_session):
    # Setup
    demo_org = Organization(id="demo-id", name="Demo", is_demo=True, is_active=True)
    user = User(id=1, email="test@demo.com", role="user", organization=demo_org)
    
    # Mock Request
    request = MagicMock()
    request.cookies.get.return_value = "fake-token"
    request.method = "POST" # Write operation
    
    # Mock dependencies
    with patch("app.neon_auth.verify_token", return_value={"sub": "1"}), \
         patch("app.neon_auth.logger"):
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = user
        
        # Expect 403 Forbidden
        with pytest.raises(HTTPException) as excinfo:
            await get_user_context(request=request, credentials=None, db=mock_db_session)
        
        assert excinfo.value.status_code == 403
        assert "demo organization" in excinfo.value.detail

@pytest.mark.asyncio
async def test_demo_org_read_allowed(mock_db_session):
    # Setup
    demo_org = Organization(id="demo-id", name="Demo", is_demo=True, is_active=True)
    user = User(id=1, email="test@demo.com", role="user", organization=demo_org)
    
    # Mock Request
    request = MagicMock()
    request.cookies.get.return_value = "fake-token"
    request.method = "GET" # Read operation
    
    # Mock dependencies
    with patch("app.neon_auth.verify_token", return_value={"sub": "1"}), \
         patch("app.neon_auth.logger"):
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = user
        
        # Should NOT raise exception
        context = await get_user_context(request=request, credentials=None, db=mock_db_session)
        assert context.organization.id == "demo-id"

def test_auth_service_auto_assigns_demo_org(mock_db_session):
    # Setup
    demo_org = Organization(id="demo-id", slug="grace-community", name="Grace Community")
    
    # Mock DB queries
    # First query checks for user (returns None)
    # Second query finds Demo Org
    mock_db_session.query.side_effect = [
        MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))), # User query
        MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=demo_org))))  # Org query
    ]
    
    # Execute
    user = AuthService.get_or_create_user(mock_db_session, "newuser@example.com")
    
    # Verify
    assert user.org_id == "demo-id"
    mock_db_session.add.assert_called_once()
