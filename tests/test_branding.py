import pytest
import uuid
from app.models import Organization, User


@pytest.mark.asyncio
async def test_branding_configuration_persistence(client, db):
    """
    Verify that an organization admin can update the branding configuration
    and that it is correctly persisted and retrieved.
    """
    from app.neon_auth import get_current_user, require_org
    from app.main import app
    
    # 1. Setup Test Data
    # Create Organization
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id, 
        name="Branding Test Org", 
        slug="brand-test", 
        plan="ministry",
        branding={}
    )
    db.add(org)
    
    # Create Admin User linked to Org
    user = User(
        email="admin@brandtest.com",
        role="admin",
        org_id=org_id
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    
    # 2. Override Dependencies to simulate logged-in Admin
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_org] = lambda: org
    
    try:
        # 3. Update Organization Branding via PATCH /api/v1/organizations/me
        branding_payload = {
            "branding": {
                "primary_color": "#ff0080",
                "theme_preset": "synthwave",
                "logo_url": "https://example.com/logo.png"
            }
        }
        
        response = client.patch("/api/v1/organizations/me", json=branding_payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["branding"]["primary_color"] == "#ff0080"
        assert data["branding"]["theme_preset"] == "synthwave"
        
        # 4. Verify persistence by verifying DB state directly (or via GET)
        db.refresh(org)
        assert org.branding["primary_color"] == "#ff0080"
        
    finally:
        # Cleanup overrides
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[require_org]

