import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Organization, Survey
from app.services.survey_service import SurveyService

client = TestClient(app)

def test_aggregated_analytics_normalization(db, client):
    # 1. Setup
    org = Organization(name="Norm Org", slug="norm-org")
    db.add(org)
    
    admin = User(email="admin_norm@example.com", role="admin", membership_status="active")
    db.add(admin)
    db.flush()
    admin.org_id = org.id
    
    # 2. Add Surveys with specific scores
    # We want to verified that the 'top_gifts' aggregation works correctly.
    # Scores are usually stored as {"GiftName": value}.
    # We assume the frontend sends consistent keys, but let's verify aggregation groups them.
    
    # s1: Faith is top (25 > 20)
    s1 = Survey(user_id=admin.id, org_id=org.id, answers={}, scores={"Administration": 20, "Faith": 25, "overall": 100})
    # s2: Administration is top (18 > 12)
    s2 = Survey(user_id=admin.id, org_id=org.id, answers={}, scores={"Administration": 18, "Mercy": 12, "Overall": 90}) 
    
    db.add_all([s1, s2])
    db.commit()
    
    # Mock Auth
    from app.neon_auth import get_user_context, UserContext
    def mock_context():
        db.refresh(admin)
        return UserContext(user=admin, organization=org, role="admin")
    app.dependency_overrides[get_user_context] = mock_context
    
    # 3. Call Analytics
    response = client.get("/api/v1/organizations/me/analytics")
    assert response.status_code == 200
    data = response.json()
    
    # 4. Verify Gift Distribution (Top Gifts)
    # Expected: Faith x 1, Administration x 1
    dist = data.get("top_gifts_distribution", {})
    
    assert "Administration" in dist
    assert dist["Administration"] == 1
    assert "Faith" in dist
    assert dist["Faith"] == 1
    
    # Verify Averages Keys (Normalization check for all keys)
    avgs = data.get("gift_averages", {})
    assert "Administration" in avgs
    assert "Mercy" in avgs
    lowercase_keys = [k for k in avgs.keys() if k.islower() and k != "other"]
    assert len(lowercase_keys) == 0, f"Found non-normalized keys in averages: {lowercase_keys}"

def test_language_switch_does_not_change_keys(db, client):
    # If the user switches language, the API might return localized keys OR standard keys.
    # Standard practice: API returns standard keys (IDs/English), Frontend localizes.
    # Let's verify analytics endpoints don't start returning "Administración" just because locale=es.
    
    # Setup same as above
    org = Organization(name="Lang Org", slug="lang-org")
    db.add(org)
    admin = User(email="admin_lang@example.com", role="admin", membership_status="active")
    db.add(admin)
    db.flush() # Ensure ID
    admin.org_id = org.id
    
    s1 = Survey(user_id=admin.id, org_id=org.id, answers={}, scores={"Administration": 20})
    db.add(s1)
    db.commit()
    
    # Mock Auth
    from app.neon_auth import get_user_context, UserContext
    def mock_context():
        db.refresh(admin)
        return UserContext(user=admin, organization=org, role="admin")
    app.dependency_overrides[get_user_context] = mock_context
    
    # Call with ES Locale
    headers = {"Accept-Language": "es"}
    response = client.get("/api/v1/organizations/me/analytics", headers=headers)
    
    data = response.json()
    dist = data.get("top_gifts_distribution", {})
    
    # SHOULD still be "Administration" (Standard Key), not "Administración"
    assert "Administration" in dist
    assert "Administración" not in dist
