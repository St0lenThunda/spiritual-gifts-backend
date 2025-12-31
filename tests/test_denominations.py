import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import Denomination, ScriptureSet, User, Organization
from app.database import get_db

client = TestClient(app)

def test_list_denominations(db):
    # Seed data
    sset = ScriptureSet(name="Default Set", verses={})
    db.add(sset)
    db.flush()
    denom = Denomination(
        slug="spiritual_gifts", 
        display_name="Spiritual Gifts", 
        default_currency="USD",
        scripture_set_id=sset.id
    )
    db.add(denom)
    db.commit()

    response = client.get("/api/v1/denominations/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(d['slug'] == 'spiritual_gifts' for d in data)

def test_get_denomination_by_slug(db):
    # Seed data
    sset = ScriptureSet(name="Default Set", verses={})
    db.add(sset)
    db.flush()
    denom = Denomination(
        slug="spiritual_gifts", 
        display_name="Spiritual Gifts", 
        default_currency="USD",
        scripture_set_id=sset.id
    )
    db.add(denom)
    db.commit()

    slug = "spiritual_gifts"
    response = client.get(f"/api/v1/denominations/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data['slug'] == slug
    assert "scripture_set" in data

def test_create_denomination_unauthorized(db):
    # Try to create without admin auth
    payload = {
        "slug": "new-denom",
        "display_name": "New Denom",
        "default_currency": "USD"
    }
    response = client.post("/api/v1/denominations/", json=payload)
    # Expect 401 or 403 depending on auth setup, likely 401 if no token provided
    assert response.status_code in [401, 403]

# Mocking admin user would require more setup typically found in conftest.py
# Assuming we have a way to authenticate as admin, but given complexity, 
# main coverage is reading for now.
