from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Organization, Denomination, Survey
import uuid
import pytest

def test_questions_filtering_by_governance(client: TestClient, db: Session):
    """Test that /questions endpoint respects denomination whitelist."""
    # 1. Setup Denomination with whitelist
    active_keys = ["Knowledge", "Administration"]
    denom = Denomination(
        id=uuid.uuid4(),
        slug="filter-questions-denom",
        display_name="Filtered Denom",
        active_gift_keys=active_keys
    )
    db.add(denom)
    db.commit()

    # 2. Setup Organization linked to Denom
    org = Organization(
        id=uuid.uuid4(),
        name="Filtered Org",
        slug="filtered-org",
        denomination_id=denom.id,
        plan="church"
    )
    db.add(org)
    db.commit()

    # 3. Fetch questions for this org
    response = client.get("/api/v1/questions?org_slug=filtered-org")
    assert response.status_code == 200
    data = response.json()
    
    questions = data["assessment"]["questions"]
    # Verify all returned questions belong to the whitelisted gifts
    for q in questions:
        assert q["gift"] in active_keys
    
    # Verify we actually have questions (base set has 80, we should have 16)
    assert len(questions) == 16

def test_gifts_overlay_and_filtering(client: TestClient, db: Session):
    """Test that /gifts endpoint respects whitelist and applies pastoral overlays."""
    # 1. Setup Denomination with whitelist and overlay
    active_keys = ["Evangelism", "Giving"]
    pastoral_note = "Ecclesiastical guidance for Giving."
    denom = Denomination(
        id=uuid.uuid4(),
        slug="overlay-gifts-denom",
        display_name="Overlay Denom",
        active_gift_keys=active_keys,
        pastoral_overlays={
            "Giving": {"note": pastoral_note}
        }
    )
    db.add(denom)
    db.commit()

    # 2. Setup Organization
    org = Organization(
        id=uuid.uuid4(),
        name="Overlay Org",
        slug="overlay-org",
        denomination_id=denom.id,
        plan="church"
    )
    db.add(org)
    db.commit()

    # 3. Fetch gifts
    response = client.get("/api/v1/gifts?org_slug=overlay-org")
    assert response.status_code == 200
    data = response.json()
    
    # Verify whitelist
    assert len(data) == 2
    assert "Evangelism" in data
    assert "Giving" in data
    
    # Verify overlay
    assert data["Giving"]["pastoral_context"]["note"] == pastoral_note

def test_discernment_whitelisting_on_submission(client: TestClient, db: Session, user_token_headers):
    """Test that survey submission discernment respects the org's whitelist."""
    # 1. Setup whitelist denomination
    # Only "Teaching" is active. Even if scores for "Administration" are high, it should be filtered out.
    active_keys = ["Teaching"]
    denom = Denomination(
        id=uuid.uuid4(),
        slug="discern-denom",
        display_name="Discernment Denom",
        active_gift_keys=active_keys
    )
    db.add(denom)
    db.commit()

    # 2. Setup Org and link User
    org = Organization(
        id=uuid.uuid4(),
        name="Discern Org",
        slug="discern-org",
        denomination_id=denom.id,
        plan="church"
    )
    db.add(org)
    db.commit()

    # Update user to be in this org
    user = db.query(User).filter(User.email == "test@example.com").first()
    user.org_id = org.id
    db.commit()

    # 3. Submit assessment with high scores across many gifts
    answers = {}
    # Base set has 80 questions. 
    # Administration keys: 1, 11, 21, 31, 41, 51, 61, 71
    # Teaching keys: 8, 18, 28, 38, 48, 58, 68, 78
    for i in range(1, 81):
        answers[str(i)] = 5 # All 5s
    
    payload = {
        "answers": answers,
        "assessment_version": "1.0"
    }
    
    response = client.post("/api/v1/survey/submit", json=payload, headers=user_token_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Discernment should ONLY include "Teaching" because it's the only one in the whitelist
    discernment = data["discernment"]
    assert "Teaching" in discernment["high_indicators"]
    assert "Administration" not in discernment["high_indicators"]
    assert len(discernment["high_indicators"]) == 1

def test_org_analytics_filtering(client: TestClient, db: Session):
    """Test that organization analytics respect the denomination whitelist."""
    # 1. Setup Denomination
    active_keys = ["Prophecy", "Wisdom"]
    denom = Denomination(
        id=uuid.uuid4(),
        slug="analytics-denom",
        display_name="Analytics Denom",
        active_gift_keys=active_keys
    )
    db.add(denom)
    db.commit()

    # 2. Setup Organization
    org = Organization(
        id=uuid.uuid4(),
        name="Analytics Org",
        slug="analytics-org",
        denomination_id=denom.id,
        plan="church"
    )
    db.add(org)
    db.commit()

    # 3. Add a couple of surveys with fixed scores
    user = User(email="analyst@example.com", role="user", org_id=org.id)
    db.add(user)
    db.commit()

    # Administration score: 40, Prophecy score: 40
    survey = Survey(
        user_id=user.id,
        org_id=org.id,
        answers={},
        scores={"Administration": 40.0, "Prophecy": 40.0, "Wisdom": 20.0},
        discernment={},
        assessment_version="1.0"
    )
    db.add(survey)
    db.commit()

    # 4. Fetch analytics as a super admin
    # Create super admin
    super_admin = User(email="super@example.com", role="super_admin", org_id=org.id)
    db.add(super_admin)
    db.commit()
    
    from app.neon_auth import create_access_token
    token = create_access_token({"sub": str(super_admin.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/v1/organizations/me/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Verify gift_averages only includes whitelisted gifts
    averages = data["gift_averages"]
    assert "Prophecy" in averages
    assert "Wisdom" in averages
    assert "Administration" not in averages
    
    # Verify top_gifts_distribution
    dist = data["top_gifts_distribution"]
    assert "Prophecy" in dist
    assert "Administration" not in dist
