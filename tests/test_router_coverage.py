import pytest
import respx
import httpx
from app.neon_auth import NEON_AUTH_URL

@pytest.mark.asyncio
@respx.mock
async def test_send_magic_link_router_success(client):
    """Test successful magic link sending via router."""
    respx.post(f"{NEON_AUTH_URL}/auth/v1/otp").mock(return_value=httpx.Response(200, json={"message": "ok"}))
    
    response = client.post("/api/v1/auth/send-link", json={"email": "router_test@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "Magic link sent successfully"

@pytest.mark.asyncio
@respx.mock
async def test_verify_magic_link_router_success(client, db):
    """Test successful magic link verification via router."""
    email = "router_verify@example.com"
    mock_data = {
        "user": {"email": email}
    }
    respx.post(f"{NEON_AUTH_URL}/auth/v1/token").mock(return_value=httpx.Response(200, json=mock_data))
    
    response = client.post("/api/v1/auth/verify", json={"token": "valid-token"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "access_token" in client.cookies

@pytest.mark.asyncio
@respx.mock
async def test_verify_magic_link_fallback_email(client):
    """Test magic link verification with fallback email (missing user object)."""
    email = "fallback@example.com"
    mock_data = {
        "email": email
    }
    respx.post(f"{NEON_AUTH_URL}/auth/v1/token").mock(return_value=httpx.Response(200, json=mock_data))
    
    response = client.post("/api/v1/auth/verify", json={"token": "fallback-token"})
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
@respx.mock
async def test_verify_magic_link_missing_email(client):
    """Test magic link verification failure due to missing email."""
    respx.post(f"{NEON_AUTH_URL}/auth/v1/token").mock(return_value=httpx.Response(200, json={}))
    
    response = client.post("/api/v1/auth/verify", json={"token": "invalid-token"})
    assert response.status_code == 400
    assert "Email missing" in response.json()["detail"]

@pytest.mark.asyncio
async def test_verify_magic_link_invalid_pydantic(client):
    """Test validation error for empty token."""
    response = client.post("/api/v1/auth/verify", json={"token": ""})
    assert response.status_code == 422

def test_list_user_surveys_router(client, test_user):
    """Test retrieving user surveys via router."""
    # Submit a survey first
    client.post(
        "/api/v1/survey/submit", 
        json={"answers": {"1": 5}, "scores": {"Administration": 5}},
        cookies={"access_token": client.cookies.get("access_token")} # Wait, we need to be logged in
    )
    
    # Simpler: use dev-login to get session
    client.post("/api/v1/auth/dev-login", json={"email": test_user.email})
    
    response = client.get("/api/v1/user/surveys")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_static_data_endpoints(client):
    """Test public static data endpoints."""
    # Questions
    resp = client.get("/api/v1/questions")
    assert resp.status_code == 200
    assert "assessment" in resp.json()
    
    # Gifts
    resp = client.get("/api/v1/gifts")
    assert resp.status_code == 200
    assert len(resp.json()) > 0
    
    # Scriptures
    resp = client.get("/api/v1/scriptures")
    assert resp.status_code == 200
    assert len(resp.json()) > 0
