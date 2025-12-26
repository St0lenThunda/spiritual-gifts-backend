import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock
from app.neon_auth import get_current_admin
from app.models import User, Organization
import pytest_asyncio

@pytest.mark.asyncio
async def test_super_admin_access_allowed_email():
    # User is admin AND allowed email
    user = User(id=1, email="tonym415@gmail.com", role="admin")
    
    result = await get_current_admin(user)
    assert result == user

@pytest.mark.asyncio
async def test_super_admin_access_allowed_org():
    # User is admin AND allowed org
    org = Organization(id="uuid", slug="neon-evangelion")
    user = User(id=2, email="other@example.com", role="admin", organization=org)
    
    result = await get_current_admin(user)
    assert result == user

@pytest.mark.asyncio
async def test_denied_regular_admin():
    # User is admin BUT wrong org
    org = Organization(id="uuid", slug="grace-community")
    user = User(id=3, email="pastor@grace.com", role="admin", organization=org)
    
    with pytest.raises(HTTPException) as excinfo:
        await get_current_admin(user)
    
    assert excinfo.value.status_code == 403
    assert "System Administrator privileges required" in excinfo.value.detail

@pytest.mark.asyncio
async def test_denied_non_admin_role():
    # User is allowed email BUT wrong role
    user = User(id=4, email="tonym415@gmail.com", role="user")
    
    with pytest.raises(HTTPException) as excinfo:
        await get_current_admin(user)
        
    assert excinfo.value.status_code == 403
    assert "Administrative privileges required" in excinfo.value.detail
