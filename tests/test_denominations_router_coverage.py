import pytest
from unittest.mock import MagicMock, call, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Organization
from app.database import get_db
from app.neon_auth import get_current_user
from uuid import uuid4

client = TestClient(app)

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_user_admin():
    user = MagicMock(spec=User)
    user.role = "admin"
    return user

@pytest.fixture
def mock_user_normal():
    user = MagicMock(spec=User)
    user.role = "user"
    return user

# --- Tests ---

def test_create_denomination_not_admin(mock_db, mock_user_normal):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_normal
    
    response = client.post(
        "/api/v1/denominations/",
        json={"slug": "new-denom", "display_name": "New"}
    )
    assert response.status_code == 403
    assert "Only admins" in response.json()["detail"]
    app.dependency_overrides = {}

def test_create_denomination_slug_conflict(mock_db, mock_user_admin):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    with patch("app.routers.denominations.get_denomination_by_slug", return_value=True):
        response = client.post(
            "/api/v1/denominations/",
            json={"slug": "duplicate", "display_name": "Duplicate"}
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    app.dependency_overrides = {}

def test_update_denomination_not_admin(mock_db, mock_user_normal):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_normal
    
    response = client.put(
        "/api/v1/denominations/slug",
        json={"slug": "slug", "display_name": "Name"}
    )
    assert response.status_code == 403
    app.dependency_overrides = {}

def test_update_denomination_not_found(mock_db, mock_user_admin):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    with patch("app.routers.denominations.get_denomination_by_slug", return_value=None):
        response = client.put(
            "/api/v1/denominations/missing",
            json={"slug": "missing", "display_name": "Missing"}
        )
        assert response.status_code == 404
    app.dependency_overrides = {}

def test_update_denomination_slug_conflict(mock_db, mock_user_admin):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    mock_denom = MagicMock()
    
    # First call returns denom (found), second call returns existing conflict for new slug
    with patch("app.routers.denominations.get_denomination_by_slug", side_effect=[mock_denom, MagicMock()]):
        response = client.put(
            "/api/v1/denominations/old-slug",
            json={"slug": "new-conflict-slug", "display_name": "New Name"}
        )
        assert response.status_code == 409
    app.dependency_overrides = {}

def test_delete_denomination_not_admin(mock_db, mock_user_normal):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_normal
    
    response = client.delete("/api/v1/denominations/slug")
    assert response.status_code == 403
    app.dependency_overrides = {}

def test_delete_denomination_not_found(mock_db, mock_user_admin):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    with patch("app.routers.denominations.get_denomination_by_slug", return_value=None):
        response = client.delete("/api/v1/denominations/missing")
        assert response.status_code == 404
    app.dependency_overrides = {}

def test_get_one_scripture_set_not_found(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    
    with patch("app.routers.denominations.get_scripture_set", return_value=None):
        response = client.get(f"/api/v1/denominations/scripture-sets/{uuid4()}")
        assert response.status_code == 404
    app.dependency_overrides = {}

def test_create_scripture_set_not_admin(mock_db, mock_user_normal):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_normal
    
    response = client.post(
        "/api/v1/denominations/scripture-sets/",
        json={"name": "Test Set"}
    )
    assert response.status_code == 403
    app.dependency_overrides = {}

def test_update_scripture_set_not_found(mock_db, mock_user_admin):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    with patch("app.routers.denominations.get_scripture_set", return_value=None):
        response = client.put(
            f"/api/v1/denominations/scripture-sets/{uuid4()}",
            json={"name": "Updated Set"}
        )
        assert response.status_code == 404
    app.dependency_overrides = {}

def test_delete_scripture_set_not_found(mock_db, mock_user_admin):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    
    with patch("app.routers.denominations.get_scripture_set", return_value=None):
        response = client.delete(f"/api/v1/denominations/scripture-sets/{uuid4()}")
        assert response.status_code == 404
    app.dependency_overrides = {}
