import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Organization, Survey
from app.services import AuthService

client = TestClient(app)

def test_pending_member_cannot_access_analytics(db, client):
    # 1. Setup Data
    org = Organization(name="Lifecycle Org", slug="lifecycle-org", plan="free")
    db.add(org)
    db.commit()
    
    # Create Pending User
    user = User(
        email="pending@example.com", 
        role="user", 
        org_id=org.id, 
        membership_status="pending"
    )
    db.add(user)
    db.commit()
    
    db.commit()
    
    # Mock Auth Context
    from app.neon_auth import get_user_context, UserContext
    # We need to return a UserContext object
    # And we need to ensure mapped relationships (user.organization) work or strictly passed
    # User object from DB has organization loaded via lazy loading/eager loading? 
    # Test session might need refresh.

    def mock_get_context():
        # Refresh to ensure relationships are accessible in this session
        u = db.query(User).get(user.id) # user is from outer scope?
        # Actually user is 'user' variable above.
        # But 'db' fixture is function scoped.
        
        # Need to capture correct user from scope.
        # Let's verify 'user' variable is the one we want.
        db.refresh(user)
        return UserContext(
            user=user,
            organization=user.organization,
            role=user.role
        )

    app.dependency_overrides[get_user_context] = mock_get_context
    
    # 2. Call Analytics Endpoint
    # Correct path per organizations.py: /api/v1/organizations/me/analytics
    response = client.get("/api/v1/organizations/me/analytics")
    
    # 3. Verify Access Denied
    # Pending users should be denied by require_org which checks membership_status
    # require_org Line 205: if context.user.membership_status != "active": raise 403
    assert response.status_code == 403
    assert "pending approval" in response.json()["detail"]

def test_approve_role_activation(db, client):
    # 1. Setup
    org = Organization(name="Approve Org", slug="approve-org")
    db.add(org)
    
    # Create Admin
    admin = User(email="admin@example.com", role="admin", membership_status="active")
    db.add(admin)
    
    # Associate Admin with Org (via id, but also need to commit org first)
    db.flush()
    admin.org_id = org.id
    
    # Create Pending User
    pending = User(email="tobeapproved@example.com", role="user", org_id=org.id, membership_status="pending")
    db.add(pending)
    db.commit()
    
    # Mock Auth Context
    from app.neon_auth import get_user_context, UserContext
    def mock_admin_context():
        db.refresh(admin)
        return UserContext(
            user=admin,
            organization=admin.organization,
            role=admin.role
        )
    app.dependency_overrides[get_user_context] = mock_admin_context
    
    # 2. Call Approve Endpoint
    # Path: /api/v1/organizations/members/{user_id}/approve
    response = client.post(f"/api/v1/organizations/members/{pending.id}/approve")
    
    # 3. Verify
    assert response.status_code == 200, response.json()
    db.expire_all()
    updated_user = db.query(User).get(pending.id)
    assert updated_user.membership_status == "active"

def test_reject_data_leakage(db, client):
    # 1. Setup
    org = Organization(name="Reject Org", slug="reject-org")
    db.add(org)
    
    # Create Admin
    admin = User(email="admin2@example.com", role="admin", membership_status="active")
    db.add(admin)
    db.flush()
    admin.org_id = org.id
    
    # Create Pending User
    pending = User(email="reject@example.com", role="user", org_id=org.id, membership_status="pending")
    db.add(pending)
    
    db.commit()
    
    # Mock Auth Context
    from app.neon_auth import get_user_context, UserContext
    def mock_admin_context():
        db.refresh(admin)
        return UserContext(
            user=admin,
            organization=admin.organization,
            role=admin.role
        )
    app.dependency_overrides[get_user_context] = mock_admin_context

    # 2. Call Reject Endpoint
    # Path: /api/v1/organizations/members/{user_id}/reject (POST)
    response = client.post(f"/api/v1/organizations/members/{pending.id}/reject")
    
    assert response.status_code == 200
    
    # 3. Verify
    db.expire_all()
    rejected_user = db.query(User).get(pending.id)
    # Reject implementation sets org_id=None, status="active" (reset)
    assert rejected_user.org_id is None
    assert rejected_user.membership_status == "active"

def test_member_assessment_history_ordering(db, client):
    from datetime import datetime, timedelta
    from app.models import Survey
    
    # 1. Setup
    org = Organization(name="History Org", slug="history-org")
    db.add(org)
    
    admin = User(email="admin3@example.com", role="admin", membership_status="active")
    db.add(admin)
    db.flush()
    admin.org_id = org.id
    
    member = User(email="member_hist@example.com", role="user", org_id=org.id, membership_status="active")
    db.add(member)
    db.flush() # get member.id
    
    # Create 2 Assessments
    s1 = Survey(user_id=member.id, org_id=org.id, created_at=datetime.utcnow() - timedelta(days=2), answers={}, scores={"Administration": 10})
    s2 = Survey(user_id=member.id, org_id=org.id, created_at=datetime.utcnow() - timedelta(days=1), answers={}, scores={"Faith": 10})
    db.add_all([s1, s2])
    db.commit()
    
    # Mock Auth as Admin
    from app.neon_auth import get_user_context, UserContext
    def mock_admin_context():
        db.refresh(admin)
        return UserContext(
            user=admin,
            organization=admin.organization,
            role=admin.role
        )
    app.dependency_overrides[get_user_context] = mock_admin_context
    
    # 2. Call Endpoint
    # Path: /api/v1/organizations/me/members/{member_id}/assessments
    response = client.get(f"/api/v1/organizations/me/members/{member.id}/assessments")
    
    assert response.status_code == 200
    data = response.json()
    assessments = data["assessments"]
    
    # 3. Verify
    assert len(assessments) == 2
    # Verify Descending Order (Newest First)
    # s2 is newer (1 day ago) than s1 (2 days ago).
    assert assessments[0]["id"] == s2.id
    assert assessments[1]["id"] == s1.id
