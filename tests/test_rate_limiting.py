# Using fixtures from conftest.py

def test_rate_limiting_send_link(client):
    """Test that /auth/send-link is rate limited."""
    email = "test@example.com"
    
    # First 3 requests should succeed (status 200 or 500 depending on Neon Auth mock)
    # Since we are using dummy keys, it will likely return 500 from the catch block
    # OR we can mock neon_send_magic_link if we want to be cleaner.
    # But for rate limiting, slowapi runs BEFORE the endpoint logic.
    
    for i in range(3):
        response = client.post("/auth/send-link", json={"email": email})
        # It might be 500 because of dummy keys, but it shouldn't be 429
        assert response.status_code != 429
        
    # 4th request should be rate limited
    response = client.post("/auth/send-link", json={"email": email})
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text
