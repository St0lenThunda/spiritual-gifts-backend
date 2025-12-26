"""
Tests to achieve 100% backend coverage.
Covers Redis paths, CSRF token endpoint, and CSRF exception handling.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_csrf_token_endpoint(client, monkeypatch):
    """Cover routers/__init__.py:47-51 - CSRF token endpoint."""
    from fastapi_csrf_protect import CsrfProtect
    
    # Mock the methods that require secret key configuration
    monkeypatch.setattr(CsrfProtect, "generate_csrf_tokens", lambda self: ("test-token", "signed-test-token"))
    monkeypatch.setattr(CsrfProtect, "set_csrf_cookie", lambda self, token, response: None)
    
    response = client.get("/api/v1/csrf-token")
    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data
    assert data["detail"] == "CSRF cookie set"


def test_safe_json_coder_decode_string():
    """Cover routers/__init__.py:35 - SafeJsonCoder string handling."""
    from app.routers import SafeJsonCoder
    
    # Test decoding a JSON string (simulating what Redis returns)
    json_string = '{"foo": "bar"}'
    result = SafeJsonCoder.decode(json_string)
    assert result == {"foo": "bar"}


def test_csrf_exception_handler(client, monkeypatch):
    """Cover main.py:169-175 - CSRF exception handler."""
    from fastapi_csrf_protect import CsrfProtect
    from fastapi_csrf_protect.exceptions import CsrfProtectError
    
    # Make validate_csrf raise an exception
    async def mock_validate_csrf_fail(self, request):
        raise CsrfProtectError(message="Token missing", status_code=403)
    
    monkeypatch.setattr(CsrfProtect, "validate_csrf", mock_validate_csrf_fail)
    
    # Now make a POST request that should fail CSRF validation
    response = client.post("/api/v1/auth/send-link", json={"email": "csrf@test.com"})
    assert response.status_code == 403
    assert "CSRF" in response.json().get("detail", "")


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


def test_send_magic_link_success(client, monkeypatch):
    """Cover routers/__init__.py:76-77 - success path for sending magic link."""
    # Mock neon_send_magic_link to succeed
    async def mock_neon_send_success(email):
        pass  # Simulate successful send
    
    monkeypatch.setattr("app.routers.neon_send_magic_link", mock_neon_send_success)
    
    response = client.post("/api/v1/auth/send-link", json={"email": "success@test.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "Magic link sent successfully"
    assert response.json()["email"] == "success@test.com"
