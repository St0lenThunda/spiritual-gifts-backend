import pytest
from fastapi import status
from app.models import User, Organization
from app.neon_auth import create_access_token
import uuid

@pytest.fixture
def org_admin(db):
    org = Organization(name="Test Church", slug="test-church")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    user = User(email="admin@testchurch.com", role="admin", org_id=org.id, membership_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, org

@pytest.fixture
def regular_user(db):
    user = User(email="user@example.com", role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_token(org_admin):
    user, _ = org_admin
    return create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})

@pytest.fixture
def user_token(regular_user):
    return create_access_token(data={"sub": str(regular_user.id), "email": regular_user.email, "role": regular_user.role})

def test_search_organizations(client, org_admin):
    _, org = org_admin
    
    # Search by name (GET request with query param 'q')
    response = client.get("/api/v1/organizations/search?q=Test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(o["name"] == "Test Church" for o in data)
    
    # Search by slug
    response = client.get("/api/v1/organizations/search?q=test-church")
    assert response.status_code == 200
    data = response.json()
    assert any(o["slug"] == "test-church" for o in data)

def test_join_request_flow(client, user_token, regular_user, org_admin, db):
    admin_user, org = org_admin
    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role})
    
    # User requests to join (POST /organizations/join/{slug})
    response = client.post(
        f"/api/v1/organizations/join/{org.slug}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 202
    
    db.refresh(regular_user)
    assert regular_user.org_id == org.id
    assert regular_user.membership_status == "pending"
    
    # Admin approves (POST /organizations/members/{user_id}/approve)
    response = client.post(
        f"/api/v1/organizations/members/{regular_user.id}/approve",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    db.refresh(regular_user)
    assert regular_user.membership_status == "active"

def test_join_request_rejection(client, user_token, regular_user, org_admin, db):
    admin_user, org = org_admin
    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role})
    
    # User requests to join
    client.post(
        f"/api/v1/organizations/join/{org.slug}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    # Admin rejects (POST /organizations/members/{user_id}/reject)
    response = client.post(
        f"/api/v1/organizations/members/{regular_user.id}/reject",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    db.refresh(regular_user)
    assert regular_user.org_id is None

def test_update_member_role(client, user_token, regular_user, org_admin, db):
    admin_user, org = org_admin
    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role})
    
    # Manually add user to org
    regular_user.org_id = org.id
    regular_user.membership_status = "active"
    db.commit()
    
    # Admin updates role
    # OrganizationMemberInvite requires email and role
    response = client.patch(
        f"/api/v1/organizations/members/{regular_user.id}",
        json={"email": regular_user.email, "role": "admin"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    db.refresh(regular_user)
    assert regular_user.role == "admin"

def test_org_admin_cannot_update_non_member(client, org_admin, db):
    admin_user, org = org_admin
    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role})
    
    other_user = User(email="other@example.com", role="user")
    db.add(other_user)
    db.commit()
    
    # Admin tries to update user not in their org
    response = client.patch(
        f"/api/v1/organizations/members/{other_user.id}",
        json={"email": other_user.email, "role": "admin"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
