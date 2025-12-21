import pytest
from app.models import LogEntry, User
from app.neon_auth import get_current_admin

@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User(email="admin@example.com", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_get_logs_pagination(client, db, admin_user):
    # Override get_current_admin dependency
    from app.main import app
    app.dependency_overrides[get_current_admin] = lambda: admin_user

    # Seed logs
    logs = []
    from datetime import datetime
    for i in range(25):
        logs.append(LogEntry(
            level="INFO",
            event="test_event",
            user_email=f"user{i}@example.com",
            path="/api/test",
            method="GET",
            status_code=200,
            timestamp=datetime.utcnow(), 
            # Note: timestamp might be auto-set, but let's be explicit if model allows
            # If model defaults to func.now(), adding manually is fine.
        ))
    db.add_all(logs)
    db.commit()

    # Page 1 (Limit 10) - Filter by our specific test event to avoid middleware logs
    response = client.get("/api/v1/admin/logs?page=1&limit=10&event=test_event")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 10
    assert data["total"] == 25
    assert len(data["items"]) == 10
    
    # Page 3 (Limit 10) -> Should have 5 items
    response = client.get("/api/v1/admin/logs?page=3&limit=10&event=test_event")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 3
    assert len(data["items"]) == 5

def test_get_users_pagination(client, db, admin_user):
    # Override get_current_admin dependency
    from app.main import app
    app.dependency_overrides[get_current_admin] = lambda: admin_user

    # Seed users (1 admin already exists)
    for i in range(25):
        db.add(User(email=f"user{i}@example.com", role="user"))
    db.commit()

    # Total should be 26 (1 admin + 25 users)
    
    # Page 1 (Limit 5)
    response = client.get("/api/v1/admin/users?page=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 26
    assert len(data["items"]) == 5
    
    # Check default sort (asc by id)
    # First item should be admin (id 1 usually)
    assert data["items"][0]["email"] == "admin@example.com"
