"""
Test suite for user preferences API endpoints.
Fixed to properly handle SQLAlchemy sessions.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database import Base, get_db
from app.main import app
from app.models import User, Organization
from app.services.entitlements import THEMES_INDIVIDUAL, THEMES_MINISTRY
import uuid

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_preferences.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Global session for tests
_test_session = None

def get_test_db():
    """Override for get_db that returns our test session."""
    global _test_session
    try:
        yield _test_session
    finally:
        pass  # Don't close, we'll manage it in fixtures

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    global _test_session
    
    Base.metadata.create_all(bind=engine)
    _test_session = TestingSessionLocal()
    
    # Override the dependency
    app.dependency_overrides[get_db] = get_test_db
    
    yield _test_session
    
    _test_session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def free_tier_org(db_session):
    """Create a free tier organization."""
    org = Organization(
        id=uuid.uuid4(),
        name="Free Org",
        slug="free-org",
        plan="free",
        is_active=True
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def ministry_tier_org(db_session):
    """Create a ministry tier organization."""
    org = Organization(
        id=uuid.uuid4(),
        name="Ministry Org",
        slug="ministry-org",
        plan="ministry",
        is_active=True
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session, free_tier_org):
    """Create a test user."""
    user = User(
        email="test@example.com",
        role="user",
        org_id=free_tier_org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, ministry_tier_org):
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        role="admin",
        org_id=ministry_tier_org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def override_auth(user):
    """Create an auth override that returns user from DB session."""
    def _get_user():
        # Return the user - it's already in the same session
        return user
    return _get_user


class TestPreferencesGet:
    """Test GET /user/preferences endpoint."""
    
    def test_get_default_preferences(self, db_session, test_user):
        """User with no preferences gets defaults."""
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.get("/api/v1/user/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data.get("locale") == "en"
        assert data.get("sync_across_orgs") == True
    
    def test_get_preferences_with_global_prefs(self, db_session, test_user):
        """User with global preferences gets them back."""
        test_user.global_preferences = {"theme": "dark", "locale": "es"}
        db_session.commit()
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.get("/api/v1/user/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data.get("theme") == "dark"
        assert data.get("locale") == "es"
    
    def test_get_preferences_org_specific(self, db_session, test_user, free_tier_org):
        """Organization-specific preferences override global."""
        test_user.global_preferences = {"theme": "light"}
        test_user.org_preferences = {
            str(free_tier_org.id): {"theme": "dark"}
        }
        db_session.commit()
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        # Get org-specific
        response = client.get(f"/api/v1/user/preferences?org_id={free_tier_org.id}")
        assert response.status_code == 200
        assert response.json().get("theme") == "dark"
        
        # Get global
        response = client.get("/api/v1/user/preferences")
        assert response.status_code == 200
        assert response.json().get("theme") == "light"


class TestPreferencesUpdate:
    """Test PATCH /user/preferences endpoint."""
    
    def test_update_global_preferences(self, db_session, test_user):
        """User can update global preferences."""
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.patch("/api/v1/user/preferences", json={
            "theme": "dark",
            "locale": "fr"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("theme") == "dark"
        assert data.get("locale") == "fr"
        
        # Verify in database
        db_session.refresh(test_user)
        assert test_user.global_preferences.get("theme") == "dark"
        assert test_user.global_preferences.get("locale") == "fr"
    
    def test_update_validates_theme_tier(self, db_session, test_user):
        """Theme selection is validated against tier."""
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        # Free tier user tries premium theme
        response = client.patch("/api/v1/user/preferences", json={
            "theme": "glacier"  # Ministry+ only
        })
        assert response.status_code == 403
        assert "not available" in response.json()["detail"].lower()
        
        # Free tier user can select allowed theme
        response = client.patch("/api/v1/user/preferences", json={
            "theme": "synthwave"  # Allowed in free tier
        })
        assert response.status_code == 200
    
    def test_update_org_specific_when_sync_disabled(self, db_session, test_user, free_tier_org):
        """Org-specific preferences when sync is disabled."""
        test_user.global_preferences = {"sync_across_orgs": False}
        db_session.commit()
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.patch(
            f"/api/v1/user/preferences?org_id={free_tier_org.id}",
            json={"theme": "dark"}
        )
        assert response.status_code == 200
        
        # Verify org-specific preference stored
        db_session.refresh(test_user)
        assert str(free_tier_org.id) in test_user.org_preferences
        assert test_user.org_preferences[str(free_tier_org.id)]["theme"] == "dark"


class TestPreferencesReset:
    """Test POST /user/preferences/reset endpoint."""
    
    def test_reset_all_preferences(self, db_session, test_user):
        """Reset clears all preferences."""
        test_user.global_preferences = {"theme": "dark", "locale": "es"}
        test_user.org_preferences = {"uuid": {"theme": "light"}}
        db_session.commit()
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.post("/api/v1/user/preferences/reset")
        assert response.status_code == 200
        
        # Verify cleared
        db_session.refresh(test_user)
        assert test_user.global_preferences == {}
        assert test_user.org_preferences == {}
    
    def test_reset_org_specific_only(self, db_session, test_user, free_tier_org):
        """Reset can clear just org-specific preferences."""
        test_user.global_preferences = {"theme": "dark"}
        test_user.org_preferences = {
            str(free_tier_org.id): {"theme": "light"}
        }
        db_session.commit()
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.post(f"/api/v1/user/preferences/reset?org_id={free_tier_org.id}")
        assert response.status_code == 200
        
        # Global still there, org-specific cleared
        db_session.refresh(test_user)
        assert test_user.global_preferences.get("theme") == "dark"
        assert str(free_tier_org.id) not in test_user.org_preferences


class TestThemeAnalytics:
    """Test GET /admin/analytics/themes endpoint."""
    
    def test_requires_admin_role(self, db_session, test_user):
        """Analytics requires admin role."""
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(test_user)
        
        response = client.get("/api/v1/admin/analytics/themes")
        assert response.status_code == 403
        assert "admin access" in response.json()["detail"].lower()
    
    def test_requires_ministry_tier(self, db_session, free_tier_org):
        """Analytics requires Ministry or Church tier."""
        admin = User(
            email="admin@free.com",
            role="admin",
            org_id=free_tier_org.id
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(admin)
        
        response = client.get("/api/v1/admin/analytics/themes")
        assert response.status_code == 403
        assert "not available" in response.json()["detail"].lower()
        assert "ministry or church" in response.json()["detail"].lower()
    
    def test_returns_distribution(self, db_session, admin_user, ministry_tier_org):
        """Analytics returns theme distribution."""
        # Create users with different themes
        user1 = User(
            email="user1@ministry.com",
            role="user",
            org_id=ministry_tier_org.id,
            global_preferences={"theme": "dark"}
        )
        user2 = User(
            email="user2@ministry.com",
            role="user",
            org_id=ministry_tier_org.id,
            global_preferences={"theme": "dark"}
        )
        user3 = User(
            email="user3@ministry.com",
            role="user",
            org_id=ministry_tier_org.id,
            global_preferences={"theme": "light"}
        )
        db_session.add_all([user1, user2, user3])
        db_session.commit()
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(admin_user)
        
        response = client.get("/api/v1/admin/analytics/themes")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_users"] == 4  # 3 users + admin
        assert len(data["theme_distribution"]) > 0
        
        # Find dark theme entry
        dark_entry = next((e for e in data["theme_distribution"] if e["theme"] == "dark"), None)
        assert dark_entry is not None
        assert dark_entry["count"] == 2
        assert dark_entry["percentage"] == 50.0  # 2 out of 4


class TestTierEntitlements:
    """Test theme entitlement enforcement across tiers."""
    
    def test_free_tier_themes(self, db_session, free_tier_org):
        """Free tier has access to 3 themes."""
        user = User(email="free@test.com", role="user", org_id=free_tier_org.id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(user)
        
        # Can select free tier themes
        for theme in THEMES_INDIVIDUAL:
            response = client.patch("/api/v1/user/preferences", json={"theme": theme})
            assert response.status_code == 200, f"Failed for theme {theme}: {response.json()}"
        
        # Cannot select premium themes
        response = client.patch("/api/v1/user/preferences", json={"theme": "ocean"})
        assert response.status_code == 403
    
    def test_ministry_tier_themes(self, db_session, ministry_tier_org):
        """Ministry tier has access to 10 themes."""
        user = User(email="ministry@test.com", role="user", org_id=ministry_tier_org.id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        from app.neon_auth import get_current_user
        app.dependency_overrides[get_current_user] = override_auth(user)
        
        # Can select ministry tier themes
        for theme in THEMES_MINISTRY:
            response = client.patch("/api/v1/user/preferences", json={"theme": theme})
            assert response.status_code == 200, f"Failed for theme {theme}: {response.json()}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
