import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import Organization, User
from app.database import get_db
from app.neon_auth import get_current_user, require_org
from app.services.billing_service import BillingService
from fastapi_csrf_protect import CsrfProtect
import stripe

client = TestClient(app)

# --- Fixtures ---

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_org():
    org = MagicMock(spec=Organization)
    org.id = "uuid-billing-123"
    org.stripe_customer_id = "cus_123"
    return org

@pytest.fixture
def mock_user_admin(mock_org):
    user = MagicMock(spec=User)
    user.role = "admin"
    user.org_id = mock_org.id
    user.organization = mock_org
    return user

# --- Tests ---

def test_create_checkout_session(mock_db, mock_org, mock_user_admin):
    """Test creating a checkout session."""
    
    with patch("app.routers.billing.BillingService.create_checkout_session") as mock_create, \
         patch("app.routers.billing.CsrfProtect.validate_csrf", new_callable=AsyncMock) as mock_csrf:
        
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_create.return_value = mock_session
        
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user_admin
        # Mock require_org to return our mock_org
        app.dependency_overrides[require_org] = lambda: mock_org

        # CSRF headers usually handled by frontend, mocking validate_csrf accepts anything
        response = client.post(
            "/api/v1/billing/create-checkout-session?plan=ministry",
            headers={"X-CSRF-Token": "secret"}
        )
        
        assert response.status_code == 200
        assert response.json()["url"] == "https://checkout.stripe.com/test"
        
        app.dependency_overrides = {}

def test_create_checkout_session_error(mock_db, mock_org, mock_user_admin):
    """Test error handling in checkout session."""
    
    with patch("app.routers.billing.BillingService.create_checkout_session") as mock_create, \
         patch("app.routers.billing.CsrfProtect.validate_csrf", new_callable=AsyncMock):
        
        mock_create.side_effect = ValueError("Invalid Plan")
        
        app.dependency_overrides[require_org] = lambda: mock_org
        
        response = client.post(
            "/api/v1/billing/create-checkout-session?plan=bad_plan",
            headers={"X-CSRF-Token": "secret"}
        )
        
        assert response.status_code == 400
        assert "Invalid Plan" in response.json()["detail"]
        
        app.dependency_overrides = {}

def test_create_portal_session(mock_db, mock_org, mock_user_admin):
    """Test creating a portal session."""
    
    with patch("app.routers.billing.BillingService.create_portal_session") as mock_create, \
         patch("app.routers.billing.CsrfProtect.validate_csrf", new_callable=AsyncMock):
        
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/test"
        mock_create.return_value = mock_session
        
        app.dependency_overrides[require_org] = lambda: mock_org
        
        response = client.post(
            "/api/v1/billing/create-portal-session",
            headers={"X-CSRF-Token": "secret"}
        )
        
        assert response.status_code == 200
        assert response.json()["url"] == "https://billing.stripe.com/test"
        
        app.dependency_overrides = {}

def test_stripe_webhook_success(mock_db):
    """Test handling a valid webhook."""
    
    payload = b'{"id": "evt_123", "type": "checkout.session.completed"}'
    sig = "valid_signature"
    
    with patch("stripe.Webhook.construct_event") as mock_construct, \
         patch("app.routers.billing.is_event_processed", return_value=False), \
         patch("app.routers.billing.mark_event_processed") as mock_mark, \
         patch("app.routers.billing.handle_checkout_completed", new_callable=AsyncMock) as mock_handle:
        
        mock_construct.return_value = {
            "id": "evt_123",
            "type": "checkout.session.completed",
            "data": {"object": {}}
        }
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=payload,
            headers={"stripe-signature": sig}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_handle.assert_called_once()
        mock_mark.assert_called_once_with("evt_123")
        
        app.dependency_overrides = {}

def test_stripe_webhook_duplicate(mock_db):
    """Test idempotent handling of duplicate webhook."""
    
    with patch("stripe.Webhook.construct_event") as mock_construct, \
         patch("app.routers.billing.is_event_processed", return_value=True): # Already processed
        
        mock_construct.return_value = {
            "id": "evt_123",
            "type": "checkout.session.completed"
        }
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "already_processed"

def test_stripe_webhook_invalid_signature():
    """Test invalid signature handling."""
    with patch("stripe.Webhook.construct_event", side_effect=stripe.error.SignatureVerificationError("Bad sig", "sig")):
        response = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "bad_sig"}
        )
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

def test_stripe_webhook_subscription_updated(mock_db, mock_org):
    """Test subscription updated event."""
    
    # Setup mock org to be returned by query
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value.first.return_value = mock_org
    
    with patch("stripe.Webhook.construct_event") as mock_construct, \
         patch("app.routers.billing.is_event_processed", return_value=False), \
         patch("app.routers.billing.mark_event_processed"), \
         patch("app.routers.billing.map_price_to_plan", return_value="ministry"):
        
        mock_construct.return_value = {
            "id": "evt_sub",
            "type": "customer.subscription.updated",
            "data": {"object": {
                "customer": "cus_123",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_123"}}]}
            }}
        }
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig"}
        )
        assert response.status_code == 200
        # Check that org plan was updated
        assert mock_org.plan == "ministry"
        mock_db.commit.assert_called()
        
        app.dependency_overrides = {}

def test_stripe_webhook_invoice_paid(mock_db):
    """Test invoice paid event."""
    with patch("stripe.Webhook.construct_event") as mock_construct, \
         patch("app.routers.billing.is_event_processed", return_value=False), \
         patch("app.routers.billing.mark_event_processed"):
        
        mock_construct.return_value = {
            "id": "evt_inv",
            "type": "invoice.payment_succeeded",
            "data": {"object": {
                "customer": "cus_123",
                "amount_paid": 5000
            }}
        }
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig"}
        )
        assert response.status_code == 200
        # Invoice paid just logs info, safe to assume success if 200 returned
        
        app.dependency_overrides = {}

def test_stripe_webhook_invoice_failed(mock_db):
    """Test invoice failed event."""
    with patch("stripe.Webhook.construct_event") as mock_construct, \
         patch("app.routers.billing.is_event_processed", return_value=False), \
         patch("app.routers.billing.mark_event_processed"):
        
        mock_construct.return_value = {
            "id": "evt_fail",
            "type": "invoice.payment_failed",
            "data": {"object": {
                "customer": "cus_123"
            }}
        }
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig"}
        )
        assert response.status_code == 200
        # Invoice failed warning log check not strictly necessary for coverage logic path
        
        app.dependency_overrides = {}

