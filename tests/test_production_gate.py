import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set dummy environment variables for settings initialization
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
os.environ["NEON_API_KEY"] = "dummy"
os.environ["NEON_PROJECT_ID"] = "dummy"

import app.database
from app.config import settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app.database.engine = engine
app.database.SessionLocal = TestingSessionLocal

from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

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
