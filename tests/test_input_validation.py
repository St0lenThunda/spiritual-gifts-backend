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

from app.database import Base, get_db
from app.neon_auth import get_current_user
from app.models import User

def override_get_current_user():
    return User(id=1, email="test@example.com")

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

from app.database import Base

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_survey_validation_valid(client):
    """Test that valid survey data is accepted."""
    from app.database import get_db as real_get_db
    # Re-apply override if needed or just rely on global
    response = client.post("/survey/submit", json={
        "answers": {1: 5, 2: 3, 3: 1},
        "notes": "Test notes"
    })
    # Now it should be 200
    assert response.status_code == 200

def test_survey_validation_invalid_score_high(client):
    """Test that survey data with score > 5 is rejected with 422."""
    response = client.post("/survey/submit", json={
        "answers": {1: 6},
        "notes": "Test notes"
    })
    assert response.status_code == 422
    assert "less than or equal to 5" in response.text or "Score for question 1 must be between 1 and 5" in response.text

def test_survey_validation_invalid_score_low(client):
    """Test that survey data with score < 1 is rejected with 422."""
    response = client.post("/survey/submit", json={
        "answers": {1: 0},
        "notes": "Test notes"
    })
    assert response.status_code == 422
    assert "greater than or equal to 1" in response.text or "Score for question 1 must be between 1 and 5" in response.text

def test_survey_validation_empty_answers(client):
    """Test that empty answers dict is rejected."""
    response = client.post("/survey/submit", json={
        "answers": {},
        "notes": "Test notes"
    })
    assert response.status_code == 422
    assert "Answers cannot be empty" in response.text
