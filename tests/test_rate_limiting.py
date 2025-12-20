import os

# Set dummy environment variables for settings initialization
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
os.environ["NEON_API_KEY"] = "dummy"
os.environ["NEON_PROJECT_ID"] = "dummy"

import pytest
from fastapi.testclient import TestClient

import app.database
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

app.database.engine = engine
app.database.SessionLocal = TestingSessionLocal

from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

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
