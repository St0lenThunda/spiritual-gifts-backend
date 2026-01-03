import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, SurveyDraft, Organization
import uuid
from app.neon_auth import create_access_token

@pytest.fixture
def token_headers(test_user):
    """Return auth headers for the test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_org(db):
    org = Organization(name="Test Org", slug="test-org", plan="fellowship")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

def test_survey_draft_flow(client: TestClient, db: Session, test_user: User, token_headers):
    """Test the complete survey draft lifecycle."""
    # 1. Initially no draft
    response = client.get("/api/v1/survey/draft", headers=token_headers)
    assert response.status_code == 404

    # 2. Create a draft
    draft_data = {
        "answers": {"1": 5, "2": 4},
        "current_step": 1,
        "assessment_version": "1.0"
    }
    response = client.post("/api/v1/survey/draft", json=draft_data, headers=token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["answers"] == {"1": 5, "2": 4}
    assert data["current_step"] == 1

    # 3. Update the draft
    update_data = {
        "answers": {"1": 5, "2": 4, "3": 3},
        "current_step": 2,
        "assessment_version": "1.0"
    }
    response = client.post("/api/v1/survey/draft", json=update_data, headers=token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["answers"] == {"1": 5, "2": 4, "3": 3}
    assert data["current_step"] == 2

    # 4. Get the draft
    response = client.get("/api/v1/survey/draft", headers=token_headers)
    assert response.status_code == 200
    assert response.json()["answers"] == {"1": 5, "2": 4, "3": 3}

    # 5. Deleting the draft
    response = client.delete("/api/v1/survey/draft", headers=token_headers)
    assert response.status_code == 200
    
    # 6. Verify deleted
    response = client.get("/api/v1/survey/draft", headers=token_headers)
    assert response.status_code == 404

def test_survey_submission_clears_draft(client: TestClient, db: Session, test_user: User, token_headers):
    """Test that submitting a survey clears the draft."""
    # Create a draft
    client.post("/api/v1/survey/draft", json={
        "answers": {"1": 5},
        "current_step": 1,
        "assessment_version": "1.0"
    }, headers=token_headers)
    
    # Submit a survey
    survey_data = {
        "answers": {str(i): 3 for i in range(1, 81)},
        "assessment_version": "1.0"
    }
    response = client.post("/api/v1/survey/submit", json=survey_data, headers=token_headers)
    assert response.status_code == 200
    
    # Verify draft is gone
    response = client.get("/api/v1/survey/draft", headers=token_headers)
    assert response.status_code == 404

def test_org_analytics_draft_count(client: TestClient, db: Session, test_user: User, test_org: Organization, token_headers):
    """Test that org analytics includes the correct draft count."""
    # Set org_id for user
    test_user.org_id = test_org.id
    db.commit()

    # Create a draft linked to org
    client.post("/api/v1/survey/draft", json={
        "answers": {"1": 5},
        "current_step": 1,
        "assessment_version": "1.0"
    }, headers=token_headers)
    
    # Fetch analytics
    response = client.get("/api/v1/organizations/me/analytics", headers=token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["in_progress_drafts"] == 1
