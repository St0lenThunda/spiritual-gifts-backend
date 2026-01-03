import pytest
from fastapi import status
from app.models import User, LogEntry, Organization
from app.neon_auth import create_access_token

@pytest.fixture
def test_org(db):
    org = Organization(name="Test Org", slug="test-org", plan="ministry", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

@pytest.fixture
def admin_user(db, test_org):
    user = User(email="tonym415@gmail.com", role="admin", org_id=test_org.id, membership_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def regular_user(db, test_org):
    user = User(email="user@example.com", role="user", org_id=test_org.id, membership_status="active")
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

def test_get_logs_as_admin(client, admin_token, db, test_org):
    # Add a mock log
    log = LogEntry(level="INFO", event="test_event", user_email="test@example.com", org_id=test_org.id)
    db.add(log)
    db.commit()

    response = client.get(
        "/api/v1/admin/logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["event"] == "test_event"

def test_get_logs_filtering(client, admin_token, db, test_org):
    # Add logs with different levels
    db.add(LogEntry(level="INFO", event="info_event", user_email="user1@example.com", org_id=test_org.id))
    db.add(LogEntry(level="ERROR", event="error_event", user_email="user2@example.com", org_id=test_org.id))
    db.commit()

    # Filter by level
    response = client.get(
        "/api/v1/admin/logs?level=ERROR",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = data["items"]
    assert all(d["level"] == "ERROR" for d in items)
    assert any(d["event"] == "error_event" for d in items)

    # Filter by email
    response = client.get(
        "/api/v1/admin/logs?user_email=user1",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = data["items"]
    assert all("user1" in d["user_email"] for d in items)

    # Filter by event
    response = client.get(
        "/api/v1/admin/logs?event=info",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = data["items"]
    assert all("info" in d["event"].lower() for d in items)

def test_get_logs_sorting(client, admin_token, db, test_org):
    db.add(LogEntry(level="INFO", event="a_event", user_email="a@example.com", org_id=test_org.id))
    db.add(LogEntry(level="INFO", event="z_event", user_email="z@example.com", org_id=test_org.id))
    db.commit()

    # Sort by event ASC
    response = client.get(
        "/api/v1/admin/logs?sort_by=event&order=asc",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = [d for d in data["items"] if d["event"] in ["a_event", "z_event"]]
    assert items[0]["event"] == "a_event"
    assert items[1]["event"] == "z_event"

def test_list_users_as_admin(client, admin_token, regular_user):
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    emails = [u["email"] for u in data["items"]]
    assert regular_user.email in emails

def test_list_users_filtering_sorting(client, admin_token, regular_user, admin_user):
    # Filter by role
    response = client.get(
        "/api/v1/admin/users?role=admin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = data["items"]
    assert all(u["role"] == "admin" for u in items)

    # Filter by email
    response = client.get(
        "/api/v1/admin/users?email=regular",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = data["items"]
    assert all("regular" in u["email"] for u in items)

    # Sort by id DESC
    response = client.get(
        "/api/v1/admin/users?sort_by=id&order=desc",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    items = data["items"]
    assert items[0]["id"] > items[1]["id"]

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

def test_get_schema_as_admin(client, admin_user, db):
    # Schema endpoint requires super_admin
    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": "super_admin"})
    
    response = client.get(
        "/api/v1/admin/schema",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "mermaid" in data
    assert "erDiagram" in data["mermaid"]
    assert "users" in data["mermaid"]
    assert "surveys" in data["mermaid"]
    assert "log_entries" in data["mermaid"]

def test_schema_route_forbidden_for_regular_user(client, user_token):
    response = client.get(
        "/api/v1/admin/schema",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_update_user_as_admin(client, admin_token, regular_user, db):
    # System admin updates a user's role and status
    response = client.patch(
        f"/api/v1/admin/users/{regular_user.id}",
        json={
            "role": "admin",
            "membership_status": "active"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["role"] == "admin"
    assert data["membership_status"] == "active"
    
    db.refresh(regular_user)
    assert regular_user.role == "admin"
    assert regular_user.membership_status == "active"

def test_update_user_invalid_role(client, admin_token, regular_user):
    response = client.patch(
        f"/api/v1/admin/users/{regular_user.id}",
        json={"role": "super-god"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
