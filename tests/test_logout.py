from fastapi.testclient import TestClient
from app.main import app

def test_logout_clears_cookie(client):
    """Test that /api/v1/auth/logout clears the access_token cookie."""
    # 1. Login to get the cookie
    login_response = client.post("/api/v1/auth/dev-login", json={"email": "logout-test@example.com"})
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    
    # 2. Verify we can access a protected route
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    
    # 3. Call logout
    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Successfully logged out"}
    
    # 4. Verify cookie is indicated as deleted in the Set-Cookie header
    # In TestClient/httpx, this usually results in the cookie being removed from client.cookies
    assert "access_token" not in client.cookies
    
    # 5. Verify subsequent access is unauthorized
    me_again_response = client.get("/api/v1/auth/me")
    assert me_again_response.status_code == 401
