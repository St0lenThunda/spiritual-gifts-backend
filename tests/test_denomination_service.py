
import pytest
from app.services.denomination_service import (
    create_denomination,
    get_denomination_by_slug,
    list_denominations,
    update_denomination,
    delete_denomination,
    create_scripture_set,
    get_scripture_set,
    list_scripture_sets,
    update_scripture_set,
    delete_scripture_set
)
from app.schemas import DenominationCreate, ScriptureSetCreate

def test_denomination_crud_lifecycle(db):
    """Test full create, read, update, delete lifecycle for denominations."""
    
    # Create
    payload = DenominationCreate(
        slug="test-denom",
        display_name="Test Denomination",
        logo_url="http://logo",
        default_currency="USD",
        active_gift_keys=["teaching", "mercy"],
        pastoral_overlays={"teaching": "Prophecy"}
    )
    denom = create_denomination(db, payload)
    assert denom.id is not None
    assert denom.slug == "test-denom"
    
    # Read (By Slug)
    fetched = get_denomination_by_slug(db, "test-denom")
    assert fetched.id == denom.id
    assert fetched.display_name == "Test Denomination"
    
    # Read (List)
    all_denoms = list_denominations(db)
    assert len(all_denoms) >= 1
    assert any(d.slug == "test-denom" for d in all_denoms)
    
    # Update
    update_payload = DenominationCreate(
        slug="test-denom-updated",
        display_name="Updated Name",
        logo_url="http://new-logo",
        default_currency="CAD",
        active_gift_keys=["mercy"],
        pastoral_overlays={}
    )
    updated = update_denomination(db, denom, update_payload)
    assert updated.slug == "test-denom-updated"
    assert updated.display_name == "Updated Name"
    
    # Read New Slug
    assert get_denomination_by_slug(db, "test-denom") is None
    assert get_denomination_by_slug(db, "test-denom-updated") is not None
    
    # Delete
    delete_denomination(db, updated)
    assert get_denomination_by_slug(db, "test-denom-updated") is None

def test_scripture_set_crud_lifecycle(db):
    """Test full create, read, update, delete lifecycle for scripture sets."""
    
    # Create
    payload = ScriptureSetCreate(
        name="Test Set",
        verses={"john_3_16": "For God so loved..."}
    )
    ss = create_scripture_set(db, payload)
    assert ss.id is not None
    assert ss.name == "Test Set"
    
    # Read (By ID)
    fetched = get_scripture_set(db, ss.id)
    assert fetched.name == "Test Set"
    assert fetched.verses["john_3_16"] == "For God so loved..."
    
    # Read (List)
    all_sets = list_scripture_sets(db)
    assert len(all_sets) >= 1
    assert any(s.id == ss.id for s in all_sets)
    
    # Update
    update_payload = ScriptureSetCreate(
        name="Updated Set",
        verses={"gen_1_1": "In the beginning"}
    )
    updated = update_scripture_set(db, ss, update_payload)
    assert updated.name == "Updated Set"
    assert "gen_1_1" in updated.verses
    
    # Delete
    delete_scripture_set(db, updated)
    assert get_scripture_set(db, ss.id) is None
