# Using fixtures from conftest.py
import pytest


@pytest.fixture(autouse=True)
def reset_limiter_before_test():
    """Reset limiter before each test to avoid state pollution."""
    from app.limiter import limiter
    limiter.reset()
    yield


def test_rate_limiting_send_link(client, monkeypatch):
    """Test that /api/v1/auth/send-link is rate limited."""
    # Mock neon_send_magic_link to avoid network calls
    async def mock_neon_send(email):
        pass
    
    monkeypatch.setattr("app.routers.neon_send_magic_link", mock_neon_send)
    
    email = "ratelimit-test@example.com"
    
    # First 3 requests should succeed
    for i in range(3):
        response = client.post("/api/v1/auth/send-link", json={"email": email})
        assert response.status_code == 200, f"Request {i+1} should succeed, got {response.status_code}"
        
    # 4th request should be rate limited
    response = client.post("/api/v1/auth/send-link", json={"email": email})
    assert response.status_code == 429
