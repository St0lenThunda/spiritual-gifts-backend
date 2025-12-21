# Using fixtures from conftest.py
from app.config import settings

def test_dev_login_allowed_in_development(client, monkeypatch):
    """Test that dev-login is allowed when ENV=development."""
    monkeypatch.setattr(settings, "ENV", "development")
    response = client.post("/auth/dev-login", json={"email": "dev@example.com"})
    # Status should be 200 (or 500 if dependencies fail, but NOT 403)
    # Since we are using mock DB, it should be 200
    assert response.status_code == 200

def test_dev_login_prohibited_in_production(client, monkeypatch):
    """Test that dev-login is prohibited when ENV=production."""
    monkeypatch.setattr(settings, "ENV", "production")
    response = client.post("/auth/dev-login", json={"email": "prod@example.com"})
    assert response.status_code == 403
    assert "strictly prohibited" in response.json()["detail"]
