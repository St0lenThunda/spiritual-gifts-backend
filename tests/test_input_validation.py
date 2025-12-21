import pytest
# Using fixtures from conftest.py
from app.neon_auth import get_current_user
from app.models import User
from datetime import datetime

@pytest.fixture(autouse=True)
def override_user(client):
    """Specific override for this test file."""
    def _override():
        return User(id=1, email="test@example.com", created_at=datetime.utcnow())
    from app.main import app
    app.dependency_overrides[get_current_user] = _override
    yield
    # conftest.py handles clearing overrides

def test_survey_validation_valid(client):
    """Test that valid survey data is accepted."""
    from app.database import get_db as real_get_db
    # Re-apply override if needed or just rely on global
    response = client.post("/api/v1/survey/submit", json={
        "answers": {1: 5, 2: 3, 3: 1},
        "notes": "Test notes"
    })
    # Now it should be 200
    assert response.status_code == 200

def test_survey_validation_invalid_score_high(client):
    """Test that survey data with score > 5 is rejected with 422."""
    response = client.post("/api/v1/survey/submit", json={
        "answers": {1: 6},
        "notes": "Test notes"
    })
    assert response.status_code == 422
    assert "less than or equal to 5" in response.text or "Score for question 1 must be between 1 and 5" in response.text

def test_survey_validation_invalid_score_low(client):
    """Test that survey data with score < 1 is rejected with 422."""
    response = client.post("/api/v1/survey/submit", json={
        "answers": {1: 0},
        "notes": "Test notes"
    })
    assert response.status_code == 422
    assert "greater than or equal to 1" in response.text or "Score for question 1 must be between 1 and 5" in response.text

def test_survey_validation_empty_answers(client):
    """Test that empty answers dict is rejected."""
    response = client.post("/api/v1/survey/submit", json={
        "answers": {},
        "notes": "Test notes"
    })
    assert response.status_code == 422
    assert "Answers cannot be empty" in response.text
