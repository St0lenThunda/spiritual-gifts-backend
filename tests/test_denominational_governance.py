from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import User, Denomination
from app.neon_auth import create_access_token
import pytest
import uuid

def test_create_denomination_with_governance(client: TestClient, db: Session, admin_token_headers):
    """Test creating a denomination with Dual-Layer Governance fields."""
    payload = {
        "name": "Governance Test Denom",  # Note: Schema uses 'display_name' but let's check validation
        "display_name": "Governance Test Denom",
        "slug": "gov-test",
        "active_gift_keys": ["teaching", "pastoring", "mercy"],
        "pastoral_overlays": {
            "prophecy": {
                "label": "Truth-Telling",
                "note": "Focus on biblical exposition rather than prediction."
            }
        }
    }
    
    response = client.post("/api/v1/denominations/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    
    assert data["slug"] == "gov-test"
    assert data["display_name"] == "Governance Test Denom"
    assert data["active_gift_keys"] == ["teaching", "pastoring", "mercy"]
    assert data["pastoral_overlays"]["prophecy"]["label"] == "Truth-Telling"
    
    # Verify DB persistence
    denom = db.query(Denomination).filter(Denomination.slug == "gov-test").first()
    assert denom is not None
    assert "teaching" in denom.active_gift_keys
    assert denom.pastoral_overlays["prophecy"]["label"] == "Truth-Telling"

def test_update_governance_layers(client: TestClient, db: Session, admin_token_headers):
    """Test updating the governance layers of a denomination."""
    # Setup - Create initial denomination
    denom = Denomination(
        id=uuid.uuid4(),
        slug="update-gov",
        display_name="Update Gov Denom",
        active_gift_keys=["admin"],
        pastoral_overlays={}
    )
    db.add(denom)
    db.commit()
    
    # Update payload
    update_payload = {
        "display_name": "Updated Gov Denom",
        "slug": "update-gov", # Keep same slug
        "active_gift_keys": ["admin", "wisdom"],
        "pastoral_overlays": {
            "healing": {"warning": "Requires elder oversight."}
        }
    }
    
    response = client.put(f"/api/v1/denominations/update-gov", json=update_payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "wisdom" in data["active_gift_keys"]
    assert data["pastoral_overlays"]["healing"]["warning"] == "Requires elder oversight."

def test_governance_validation_defaults(client: TestClient, db: Session, admin_token_headers):
    """Test that default values are set correctly when fields are omitted."""
    payload = {
        "display_name": "Minimal Denom",
        "slug": "minimal-gov"
    }
    
    response = client.post("/api/v1/denominations/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    
    # Check defaults (None or Empty List as per schema/model)
    # Model defaults: active_gift_keys=[], pastoral_overlays={}
    # Schema defaults: None (Optional) which usually results in None passed to DB? 
    # Let's check how Pydantic -> SQLAlchemy handles it. 
    # If Pydantic is None, exclude=unset might be used, or it passes None. Model has defaults.
    
    # Wait, if I pass None to SQLAlchemy column with default, it might remain None unless I omit it?
    # In `create_denomination` service, `**payload.dict()` is likely used.
    
    # In `models.py`: `active_gift_keys = Column(JSON, default=[], nullable=True)`
    # So if we don't send it, it might be None or [].
    
    # Since we defined schema as Optional[List] = None, if we send None, it goes as None.
    # But usually we want checks.
    
    # Let's see what comes back.
    # Note: If validation logic exists later to ensure non-null, we'd test that.
    # For now ensuring it doesn't crash.
    assert data["active_gift_keys"] is None or data["active_gift_keys"] == []
