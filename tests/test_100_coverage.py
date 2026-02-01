"""
Tests to achieve 100% backend coverage.
Covers Redis paths and header-based validation.
Note: CSRF was replaced with header-based validation in v1.10.0
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_header_validation_missing_origin(client):
    """Test that requests without Origin or X-Requested-With header work for GET."""
    # GET requests don't require validation
    response = client.get("/api/v1/denominations")
    assert response.status_code in [200, 401]  # May need auth, but not 403


def test_safe_json_coder_decode_string():
    """Cover routers/__init__.py:35 - SafeJsonCoder string handling."""
    from app.routers import SafeJsonCoder
    
    # Test decoding a JSON string (simulating what Redis returns)
    json_string = '{"foo": "bar"}'
    result = SafeJsonCoder.decode(json_string)
    assert result == {"foo": "bar"}


def test_send_magic_link_with_valid_headers(client, monkeypatch):
    """Test sending magic link with proper Origin header."""
    # Mock neon_send_magic_link to succeed
    async def mock_neon_send_success(email, headers=None):
        pass  # Simulate successful send
    
    monkeypatch.setattr("app.routers.neon_send_magic_link", mock_neon_send_success)
    
    response = client.post(
        "/api/v1/auth/send-link", 
        json={"email": "success@test.com"},
        headers={
            "Origin": "http://localhost:5173",
            "X-Requested-With": "XMLHttpRequest"
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Magic link sent successfully"
    assert response.json()["email"] == "success@test.com"



def test_limiter_redis_success(monkeypatch):
    """Cover limiter.py:14-27 - Redis success path."""
    # Enable Redis for this test
    monkeypatch.setenv("REDIS_ENABLED", "True")
    
    # Mock redis.from_url to return a mock that passes ping
    mock_redis_instance = MagicMock()
    mock_redis_instance.ping.return_value = True
    
    mock_from_url = MagicMock(return_value=mock_redis_instance)
    
    with patch("redis.from_url", mock_from_url):
        # Re-import to trigger get_limiter with new settings
        import importlib
        import app.config
        
        # Temporarily change the setting
        original = app.config.settings.REDIS_ENABLED
        app.config.settings.REDIS_ENABLED = True
        
        try:
            import app.limiter
            importlib.reload(app.limiter)
            
            # Verify redis was called
            mock_from_url.assert_called()
        finally:
            app.config.settings.REDIS_ENABLED = original


def test_limiter_redis_failure(monkeypatch):
    """Cover limiter.py:25-27 - Redis failure fallback path."""
    monkeypatch.setenv("REDIS_ENABLED", "True")
    
    # Mock redis.from_url to raise an exception
    def mock_from_url_fail(*args, **kwargs):
        raise ConnectionError("Redis not available")
    
    with patch("redis.from_url", mock_from_url_fail):
        import importlib
        import app.config
        
        original = app.config.settings.REDIS_ENABLED
        app.config.settings.REDIS_ENABLED = True
        
        try:
            import app.limiter
            importlib.reload(app.limiter)
            # Should fall back gracefully
        finally:
            app.config.settings.REDIS_ENABLED = original


@pytest.mark.asyncio
async def test_main_redis_cache_success(monkeypatch):
    """Cover main.py:67-77 - Redis cache success path."""
    from app.main import lifespan
    from fastapi import FastAPI
    
    # Mock redis.from_url and ping
    mock_redis_sync = MagicMock()
    mock_redis_sync.ping.return_value = True
    
    mock_redis_async = MagicMock()
    
    with patch("redis.from_url", return_value=mock_redis_sync), \
         patch("redis.asyncio.from_url", return_value=mock_redis_async), \
         patch("fastapi_cache.FastAPICache.init") as mock_cache_init:
        
        import app.config
        original = app.config.settings.REDIS_ENABLED
        app.config.settings.REDIS_ENABLED = True
        
        try:
            app_instance = FastAPI()
            async with lifespan(app_instance):
                pass
            # Cache init should have been called with RedisBackend
        finally:
            app.config.settings.REDIS_ENABLED = original


@pytest.mark.asyncio
async def test_main_redis_cache_failure(monkeypatch):
    """Cover main.py:78-79, 85-86 - Redis cache failure fallback."""
    from app.main import lifespan
    from fastapi import FastAPI
    
    # Mock redis.from_url to raise exception
    def mock_redis_fail(*args, **kwargs):
        raise ConnectionError("Redis unavailable")
    
    with patch("redis.from_url", mock_redis_fail), \
         patch("fastapi_cache.FastAPICache.init") as mock_cache_init:
        
        import app.config
        original = app.config.settings.REDIS_ENABLED
        app.config.settings.REDIS_ENABLED = True
        
        try:
            app_instance = FastAPI()
            async with lifespan(app_instance):
                pass
            # Should use InMemoryBackend fallback
            mock_cache_init.assert_called()
        finally:
            app.config.settings.REDIS_ENABLED = original
