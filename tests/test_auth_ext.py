import pytest
from fastapi import status
from app.neon_auth import create_access_token

def test_get_me_unauthorized(client):
    """Test accessing protected route without token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"

def test_get_me_invalid_token(client):
    """Test accessing protected route with invalid token."""
    client.cookies.set("access_token", "invalid-token")
    response = client.get("/api/v1/auth/me")
    client.cookies.clear()
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"

def test_logout_success(client, test_user):
    """Test logout clears the cookie."""
    # First login (mocked or dev-login)
    login_response = client.post("/api/v1/auth/dev-login", json={"email": test_user.email})
    assert login_response.status_code == 200
    assert "access_token" in client.cookies
    
    # Logout
    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert "access_token" not in client.cookies

def test_get_current_user_not_found(client):
    """Test token for non-existent user."""
    # Create token for user ID 9999 (unlikely to exist)
    token = create_access_token(data={"sub": "9999"})
    client.cookies.set("access_token", token)
    response = client.get("/api/v1/auth/me")
    client.cookies.clear()
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "User not found"

def test_get_current_user_invalid_payload(client):
    """Test token with missing 'sub' claim."""
    token = create_access_token(data={"not_sub": "value"})
    client.cookies.set("access_token", token)
    response = client.get("/api/v1/auth/me")
    client.cookies.clear()
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"
