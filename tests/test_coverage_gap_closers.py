
import pytest
import pytest
from app.logging_setup import mask_email
from app.routers import router
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.routers.admin import get_db_schema
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base



def test_mask_email_exception():
    """Cover logging_setup.py:32-33"""
    # We need to trigger line 32: except Exception: return email
    # This happens if line 26 raises: local_part, domain = email.split("@", 1)
    # 
    # If we pass a string that has "@" so it passes check at line 22...
    # ...but fails split? String split always works.
    # UNLESS email is NOT a string but behaves like one for 'in'?
    
    class FakeStr:
        def __init__(self, val):
            self.val = val
        def __bool__(self):
            return True
        def __contains__(self, item):
            return True  # Passes '"@" in email' check
        def split(self, *args):
            raise ValueError("Boom") # Fails here
        def __str__(self):
            return "fake-email"
            
    # However logging_setup.py:22 might convert to bool? 'if not email'
    # And 'if "@" not in email'.
    
    fake = FakeStr("foo")
    # type hint says str, but runtime doesn't enforce.
    # expected result: correct exception handling -> returns original object
    assert mask_email(fake) == fake

@pytest.mark.asyncio
async def test_magic_link_verify_missing_email(monkeypatch):
    """Cover routers/__init__.py:72, 77-78"""
    from app.routers import verify_magic_link
    from app import schemas
    
    # Mock dependencies
    mock_neon_response = {"user": {}} 
    
    async def mock_neon_verify(token):
        return mock_neon_response
        
    monkeypatch.setattr("app.routers.neon_verify_magic_link", mock_neon_verify)
    
    req = schemas.TokenVerifyRequest(token="bad-token")
    
    # Need fully mocked dependencies since we are calling router function directly
    # db can be MagicMock
    
    with pytest.raises(HTTPException) as exc:
        await verify_magic_link(req, MagicMock(), MagicMock(), MagicMock())
    assert exc.value.status_code == 400
    assert "Email missing" in exc.value.detail

def test_erd_unknown_column_type(monkeypatch):
    """Cover routers/admin.py:152"""
    from sqlalchemy import Boolean
    Base = declarative_base()
    class BoolTable(Base):
        __tablename__ = "bool_table"
        id = Column(Integer, primary_key=True)
        is_active = Column(Boolean)
        
    with patch("app.database.Base") as mock_base:
        mock_base.metadata.tables = BoolTable.metadata.tables
        
        import asyncio
        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(get_db_schema())
        loop.close()
        
        assert "boolean" in res["mermaid"]


