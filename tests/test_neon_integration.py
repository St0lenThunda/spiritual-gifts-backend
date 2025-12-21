import pytest
import respx
import httpx
from app.neon_auth import neon_signup, neon_send_magic_link, neon_verify_magic_link, NEON_AUTH_URL

@pytest.mark.asyncio
@respx.mock
async def test_neon_signup_success():
    respx.post(f"{NEON_AUTH_URL}/auth/v1/signup").mock(return_value=httpx.Response(200, json={"id": "user123", "email": "test@example.com"}))
    response = await neon_signup("test@example.com")
    assert response["email"] == "test@example.com"

@pytest.mark.asyncio
@respx.mock
async def test_neon_signup_failure():
    respx.post(f"{NEON_AUTH_URL}/auth/v1/signup").mock(return_value=httpx.Response(400, json={"error": "invalid_email"}))
    with pytest.raises(httpx.HTTPStatusError):
        await neon_signup("invalid-email")

@pytest.mark.asyncio
@respx.mock
async def test_neon_send_magic_link_success():
    respx.post(f"{NEON_AUTH_URL}/auth/v1/otp").mock(return_value=httpx.Response(200, json={"message": "ok"}))
    response = await neon_send_magic_link("test@example.com")
    assert response["message"] == "ok"

@pytest.mark.asyncio
@respx.mock
async def test_neon_verify_magic_link_success():
    mock_data = {
        "access_token": "abc",
        "user": {"email": "test@example.com"}
    }
    respx.post(f"{NEON_AUTH_URL}/auth/v1/token").mock(return_value=httpx.Response(200, json=mock_data))
    response = await neon_verify_magic_link("valid-otp")
    assert response["user"]["email"] == "test@example.com"
