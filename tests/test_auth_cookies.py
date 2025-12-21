# Using fixtures from conftest.py

def test_dev_login_sets_cookie(client):
    """Test that dev-login sets the access_token cookie."""
    response = client.post("/api/v1/auth/dev-login", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert "access_token" in response.cookies
    # Sub must be string for JWT but user ID is int
    # We don't need to check the exact token here, just that it's set
    assert response.cookies["access_token"] is not None

def test_authenticated_route_with_cookie(client):
    """Test that /api/v1/auth/me works with the access_token cookie."""
    # First login to get the cookie
    login_response = client.post("/api/v1/auth/dev-login", json={"email": "test@example.com"})
    assert login_response.status_code == 200
    
    # In httpx/starlette TestClient, cookies are persisted if we use the same client instance
    # But for clarity, we can check if it works
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_authenticated_route_without_cookie_fails(client):
    """Test that /api/v1/auth/me fails without a cookie or header."""
    # Fresh client should have no cookies
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
