import pytest
import time
from unittest.mock import MagicMock, patch, ANY
from fastapi import FastAPI
from app.main import lifespan

@pytest.mark.asyncio
async def test_lifespan_db_retry_success():
    """Test db initialization retry loop succeeds on 2nd attempt."""
    app = MagicMock(spec=FastAPI)
    
    # Mock Base.metadata.create_all to fail then succeed
    with patch("app.main.Base.metadata.create_all") as mock_create_all, \
         patch("app.main.settings") as mock_settings, \
         patch("app.main.logger") as mock_logger, \
         patch("time.sleep") as mock_sleep, \
         patch("app.database.SessionLocal") as mock_session:
        
        mock_settings.ENV = "development"
        mock_settings.REDIS_ENABLED = False
        
        # Second attempt succeeds
        mock_create_all.side_effect = [Exception("name resolution error"), None]
        
        async with lifespan(app):
            pass
            
        assert mock_create_all.call_count == 2
        mock_logger.info.assert_any_call(ANY)

@pytest.mark.asyncio
async def test_lifespan_db_retry_exhausted():
    """Test db initialization retry loop raises after max retries."""
    app = MagicMock(spec=FastAPI)
    
    with patch("app.main.Base.metadata.create_all") as mock_create_all, \
         patch("app.main.settings") as mock_settings, \
         patch("app.main.logger") as mock_logger, \
         patch("time.sleep") as mock_sleep:
        
        mock_settings.ENV = "development"
        mock_create_all.side_effect = Exception("dns failure")
        
        with pytest.raises(Exception) as exc:
            async with lifespan(app):
                pass
        
        assert "dns failure" in str(exc.value)
        # Should have tried 5 times
        assert mock_create_all.call_count == 5

@pytest.mark.asyncio
async def test_lifespan_super_admin_elevation_fails_gracefully():
    """Test that failed super admin check doesn't crash startup."""
    app = MagicMock(spec=FastAPI)
    
    with patch("app.main.Base.metadata.create_all"), \
         patch("app.main.settings") as mock_settings, \
         patch("app.main.logger") as mock_logger, \
         patch("app.database.SessionLocal") as mock_session:
        
        mock_settings.ENV = "development"
        mock_settings.REDIS_ENABLED = False
        
        # Mock SessionLocal() to raise
        mock_session.side_effect = Exception("DB down")
        
        async with lifespan(app):
            pass
            
        # Should log warning but not raise
        mock_logger.warning.assert_any_call(ANY)

@pytest.mark.asyncio
async def test_lifespan_db_initialization_non_dns_error():
    """Test that non-DNS errors in create_all raise immediately."""
    app = MagicMock(spec=FastAPI)
    
    with patch("app.main.Base.metadata.create_all") as mock_create_all, \
         patch("app.main.settings") as mock_settings, \
         patch("app.main.logger") as mock_logger:
        
        mock_settings.ENV = "development"
        mock_create_all.side_effect = Exception("Syntax error near (")
        
        with pytest.raises(Exception) as exc:
            async with lifespan(app):
                pass
        
        assert "Syntax error" in str(exc.value)
        # Should NOT retry
        assert mock_create_all.call_count == 1
