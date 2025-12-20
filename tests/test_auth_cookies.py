import os

# Set dummy environment variables for settings initialization
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
os.environ["NEON_API_KEY"] = "dummy"
os.environ["NEON_PROJECT_ID"] = "dummy"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import app.database
app.database.engine = engine
app.database.SessionLocal = TestingSessionLocal

from app.main import app
from app.database import Base, get_db
from app.models import User

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_dev_login_sets_cookie(client):
    """Test that dev-login sets the access_token cookie."""
    response = client.post("/auth/dev-login", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert "access_token" in response.cookies
    # Sub must be string for JWT but user ID is int
    # We don't need to check the exact token here, just that it's set
    assert response.cookies["access_token"] is not None

def test_authenticated_route_with_cookie(client):
    """Test that /auth/me works with the access_token cookie."""
    # First login to get the cookie
    login_response = client.post("/auth/dev-login", json={"email": "test@example.com"})
    assert login_response.status_code == 200
    
    # In httpx/starlette TestClient, cookies are persisted if we use the same client instance
    # But for clarity, we can check if it works
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_authenticated_route_without_cookie_fails(client):
    """Test that /auth/me fails without a cookie or header."""
    # Fresh client should have no cookies
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
