import pytest
from app.models import Organization, Survey, User
from app.services.survey_service import SurveyService

def test_org_analytics_empty(client, db, test_user):
    # Setup: Create org and assign user
    org = Organization(name="Test Org", slug="test-org", plan="growth")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    test_user.org_id = org.id
    test_user.role = "admin"
    db.commit()

    # Login
    client.post("/api/v1/auth/dev-login", json={"email": test_user.email})

    # Act
    response = client.get("/api/v1/organizations/me/analytics")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total_assessments"] == 0
    assert data["gift_averages"] == {}

def test_org_analytics_with_data(client, db, test_user):
    # Setup: Create org and assign user
    org = Organization(name="Test Org Data", slug="test-org-data", plan="growth")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    test_user.org_id = org.id
    test_user.role = "admin"
    db.commit()

    # Login
    client.post("/api/v1/auth/dev-login", json={"email": test_user.email})

    # Create surveys
    survey1 = Survey(
        user_id=test_user.id,
        org_id=org.id,
        scores={"Teaching": 10, "Leading": 5}
    )
    survey2 = Survey(
        user_id=test_user.id,
        org_id=org.id,
        scores={"Teaching": 20, "Leading": 15}
    )
    db.add(survey1)
    db.add(survey2)
    db.commit()

    # Act
    response = client.get("/api/v1/organizations/me/analytics")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total_assessments"] == 2
    # Teaching avg: (10+20)/2 = 15.0
    # Leading avg: (5+15)/2 = 10.0
    assert data["gift_averages"]["Teaching"] == 15.0
    assert data["gift_averages"]["Leading"] == 10.0
    
    # Top Gifts: Survey1=Teaching (10 vs 5), Survey2=Teaching (20 vs 15). Teaching count = 2
    assert data["top_gifts_distribution"]["Teaching"] == 2
