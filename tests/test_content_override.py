import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Denomination, ScriptureSet, Organization
from app.services import load_gifts

client = TestClient(app)

def test_get_gifts_with_scripture_override(db):
    # 1. Setup Data
    # Identify a gift to override. E.g. "Administration" usually has specific verses.
    # Load base gifts to know a valid key.
    base_gifts = load_gifts('en')
    target_gift = "Administration"
    assert target_gift in base_gifts, "Target gift must exist in base data"

    # Create Scripture Set with override
    new_verses = ["Override 1:1", "Test 2:2"]
    sset = ScriptureSet(
        name="Override Set",
        verses={target_gift: new_verses}
    )
    db.add(sset)
    db.flush()

    # Create Denomination
    denom = Denomination(
        slug="override_denom",
        display_name="Override Denom",
        default_currency="USD",
        scripture_set_id=sset.id
    )
    db.add(denom)
    db.flush()

    # Create Organization linked to Denomination
    org = Organization(
        name="Test Org",
        slug="test-org-override",
        denomination_id=denom.id
    )
    db.add(org)
    db.commit()

    # Debug: Check type
    saved_sset = db.query(ScriptureSet).filter_by(id=sset.id).first()
    print(f"DEBUG: saved_sset.verses type: {type(saved_sset.verses)}")
    print(f"DEBUG: saved_sset.verses content: {saved_sset.verses}")
    # assert isinstance(saved_sset.verses, dict) # SQLite might return None or str?

    # 2. Call API
    response = client.get(f"/api/v1/gifts?org_slug={org.slug}&locale=en")
    assert response.status_code == 200
    data = response.json()

    # 3. Verify Override
    assert target_gift in data
    scriptures = data[target_gift]["scriptures"]
    
    # Expect the NEW verses, not the default ones
    assert scriptures == new_verses
    assert "Override 1:1" in scriptures

def test_get_gifts_without_override(db):
    # Verify default behavior for comparison
    base_gifts = load_gifts('en')
    target_gift = "Administration"
    
    # Generic Org (no denom or default denom without overrides)
    # Just creating org without denom for now (if nullable)
    # Or create a denom without scripture set
    org = Organization(
        name="Default Org",
        slug="default-org-test",
        denomination_id=None
    )
    db.add(org)
    db.commit()

    response = client.get(f"/api/v1/gifts?org_slug={org.slug}&locale=en")
    assert response.status_code == 200
    data = response.json()

    # Should match base items
    assert data[target_gift]["scriptures"] == base_gifts[target_gift]["scriptures"]
