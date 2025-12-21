import pytest
from fastapi import status
from app.models import User, LogEntry
from app.neon_auth import create_access_token

@pytest.fixture
def admin_user(db):
    user = User(email="admin@example.com", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def regular_user(db):
    user = User(email="user@example.com", role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_token(admin_user):
    return create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role})

@pytest.fixture
def user_token(regular_user):
    return create_access_token(data={"sub": str(regular_user.id), "email": regular_user.email, "role": regular_user.role})

def test_get_logs_as_admin(client, admin_token, db):
    # Add a mock log
    log = LogEntry(level="INFO", event="test_event", user_email="test@example.com")
    db.add(log)
    db.commit()

    response = client.get(
        "/api/v1/admin/logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["event"] == "test_event"

def test_get_logs_filtering(client, admin_token, db):
    # Add logs with different levels
    db.add(LogEntry(level="INFO", event="info_event", user_email="user1@example.com"))
    db.add(LogEntry(level="ERROR", event="error_event", user_email="user2@example.com"))
    db.commit()

    # Filter by level
    response = client.get(
        "/api/v1/admin/logs?level=ERROR",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    assert all(d["level"] == "ERROR" for d in data)
    assert any(d["event"] == "error_event" for d in data)

    # Filter by email
    response = client.get(
        "/api/v1/admin/logs?user_email=user1",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    assert all("user1" in d["user_email"] for d in data)

    # Filter by event
    response = client.get(
        "/api/v1/admin/logs?event=info",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    assert all("info" in d["event"].lower() for d in data)

def test_get_logs_sorting(client, admin_token, db):
    db.add(LogEntry(level="INFO", event="a_event", user_email="a@example.com"))
    db.add(LogEntry(level="INFO", event="z_event", user_email="z@example.com"))
    db.commit()

    # Sort by event ASC
    response = client.get(
        "/api/v1/admin/logs?sort_by=event&order=asc",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = [d for d in response.json() if d["event"] in ["a_event", "z_event"]]
    assert data[0]["event"] == "a_event"
    assert data[1]["event"] == "z_event"

def test_list_users_as_admin(client, admin_token, regular_user):
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    emails = [u["email"] for u in data]
    assert regular_user.email in emails

def test_list_users_filtering_sorting(client, admin_token, regular_user, admin_user):
    # Filter by role
    response = client.get(
        "/api/v1/admin/users?role=admin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    assert all(u["role"] == "admin" for u in data)

    # Filter by email
    response = client.get(
        "/api/v1/admin/users?email=regular",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    assert all("regular" in u["email"] for u in data)

    # Sort by id DESC
    response = client.get(
        "/api/v1/admin/users?sort_by=id&order=desc",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    assert data[0]["id"] > data[1]["id"]

def test_admin_routes_forbidden_for_regular_user(client, user_token):
    routes = ["/api/v1/admin/logs", "/api/v1/admin/users"]
    for route in routes:
        response = client.get(
            route,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

def test_admin_routes_unauthorized(client):
    routes = ["/api/v1/admin/logs", "/api/v1/admin/users"]
    for route in routes:
        response = client.get(route)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
