
import pytest
from app.models import Denomination, ScriptureSet

@pytest.fixture
def sample_denom(db):
    denom = Denomination(
        slug="api-test-denom",
        display_name="API Test Denom",
        logo_url="url",
        default_currency="USD",
        active_gift_keys=[],
        pastoral_overlays={}
    )
    db.add(denom)
    db.commit()
    db.refresh(denom)
    return denom

@pytest.fixture
def sample_scripture_set(db):
    ss = ScriptureSet(name="API Test Set", verses={"prophecy": ["romans 12:6"]})
    db.add(ss)
    db.commit()
    db.refresh(ss)
    return ss

def test_get_denominations_public(client, sample_denom):
    """Public users should be able to list denominations."""
    response = client.get("/api/v1/denominations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(d["slug"] == "api-test-denom" for d in data)

def test_get_denomination_by_slug_public(client, sample_denom):
    """Public users should be able to get denomination by slug."""
    response = client.get(f"/api/v1/denominations/{sample_denom.slug}")
    assert response.status_code == 200
    assert response.json()["display_name"] == "API Test Denom"

def test_create_denomination_admin_only(client, admin_token_headers):
    """Admins can create denominations."""
    payload = {
        "slug": "new-admin-denom",
        "display_name": "New Admin Denom",
        "logo_url": "url",
        "default_currency": "USD",
        "active_gift_keys": [],
        "pastoral_overlays": {}
    }
    response = client.post("/api/v1/denominations/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    assert response.json()["slug"] == "new-admin-denom"

def test_create_denomination_forbidden(client):
    """Non-admins cannot create denominations."""
    payload = {"slug": "fail", "display_name": "Fail", "logo_url": "u", "default_currency": "USD", "active_gift_keys": [], "pastoral_overlays": {}}
    response = client.post("/api/v1/denominations/", json=payload)
    assert response.status_code == 401 # Unauthorized (not logged in)

    # Logged in but not admin? (Need normal user token fixture if strict RBAC, assuming basic 401/403)
    # For now, just unauth check is sufficient to prove protection

def test_update_denomination_admin_only(client, admin_token_headers, sample_denom):
    """Admins can update denominations."""
    payload = {
        "slug": sample_denom.slug, # Keep slug same
        "display_name": "Updated API Name",
        "logo_url": "url",
        "default_currency": "USD",
        "active_gift_keys": [],
        "pastoral_overlays": {}
    }
    response = client.put(f"/api/v1/denominations/{sample_denom.slug}", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated API Name"

def test_delete_denomination_admin_only(client, admin_token_headers, sample_denom):
    """Admins can delete denominations."""
    response = client.delete(f"/api/v1/denominations/{sample_denom.slug}", headers=admin_token_headers)
    assert response.status_code == 204
    
    # Verify gone
    response = client.get(f"/api/v1/denominations/{sample_denom.slug}")
    assert response.status_code == 404

def test_scripture_set_endpoints(client, admin_token_headers, sample_scripture_set):
    """Test full CRUD for scripture sets via API."""
    
    # 1. List
    response = client.get("/api/v1/denominations/scripture-sets/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 2. Get One
    response = client.get(f"/api/v1/denominations/scripture-sets/{sample_scripture_set.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "API Test Set"
    
    # 3. Create
    payload = {"name": "New API Set", "verses": {"a": ["b"]}}
    response = client.post("/api/v1/denominations/scripture-sets/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    new_id = response.json()["id"]
    
    # 4. Update
    payload["name"] = "Updated API Set"
    response = client.put(f"/api/v1/denominations/scripture-sets/{new_id}", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    
    # 5. Delete
    response = client.delete(f"/api/v1/denominations/scripture-sets/{new_id}", headers=admin_token_headers)
    assert response.status_code == 204
