import pytest
from unittest.mock import MagicMock, patch
from app.services.billing_service import BillingService
from app.config import settings

def test_create_checkout_session_valid_plan():
    """Test creating a checkout session with a valid plan name from settings dict."""
    with patch("app.services.billing_service.stripe", autospec=True) as mock_stripe:
        mock_session = MagicMock()
        mock_stripe.checkout.Session.create.return_value = mock_session
        
        # Override settings for this test
        with patch.dict(settings.STRIPE_PRICE_IDS, {"pro": "price_123"}):
            session = BillingService.create_checkout_session(
                org_id="org_1",
                plan="pro",
                success_url="http://success",
                cancel_url="http://cancel"
            )
            
            assert session == mock_session
            mock_stripe.checkout.Session.create.assert_called_once()
            call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
            assert call_kwargs["metadata"]["org_id"] == "org_1"
            assert call_kwargs["line_items"][0]["price"] == "price_123"

def test_create_checkout_session_fallback_logic():
    """Test creating a checkout session using fallback logic (legacy settings)."""
    with patch("app.services.billing_service.stripe", autospec=True) as mock_stripe:
        mock_stripe.checkout.Session.create.return_value = MagicMock()
        
        # Ensure dict is empty to trigger fallback
        with patch.dict(settings.STRIPE_PRICE_IDS, {}, clear=True):
            # Test starter fallback
            with patch.object(settings, "STRIPE_PRICE_STARTER", "price_starter_999"):
                BillingService.create_checkout_session(
                    org_id="org_2",
                    plan="starter",
                    success_url="s", 
                    cancel_url="c"
                )
                args = mock_stripe.checkout.Session.create.call_args[1]
                assert args["line_items"][0]["price"] == "price_starter_999"

            # Test growth fallback
            with patch.object(settings, "STRIPE_PRICE_GROWTH", "price_growth_888"):
                BillingService.create_checkout_session(
                    org_id="org_2",
                    plan="growth",
                    success_url="s", 
                    cancel_url="c"
                )
                args = mock_stripe.checkout.Session.create.call_args[1]
                assert args["line_items"][0]["price"] == "price_growth_888"

            # Test enterprise fallback
            with patch.object(settings, "STRIPE_PRICE_ENTERPRISE", "price_ent_777"):
                BillingService.create_checkout_session(
                    org_id="org_2",
                    plan="enterprise",
                    success_url="s", 
                    cancel_url="c"
                )
                args = mock_stripe.checkout.Session.create.call_args[1]
                assert args["line_items"][0]["price"] == "price_ent_777"

def test_create_checkout_session_invalid_plan():
    """Test that invalid plans raise ValueError."""
    # Ensure no prices match
    with patch.dict(settings.STRIPE_PRICE_IDS, {}, clear=True):
        with pytest.raises(ValueError, match="Invalid plan: unknown_plan"):
            BillingService.create_checkout_session(
                org_id="org_1",
                plan="unknown_plan",
                success_url="s",
                cancel_url="c"
            )

def test_create_portal_session():
    """Test creating a billing portal session."""
    with patch("app.services.billing_service.stripe", autospec=True) as mock_stripe:
        mock_session = MagicMock()
        mock_stripe.billing_portal.Session.create.return_value = mock_session
        
        session = BillingService.create_portal_session(customer_id="cus_123", return_url="http://return")
        
        assert session == mock_session
        mock_stripe.billing_portal.Session.create.assert_called_once_with(
            customer="cus_123",
            return_url="http://return"
        )

def test_get_subscription_status():
    """Test getting simplified subscription status from org object."""
    mock_org = MagicMock()
    mock_org.plan = "individual"
    mock_org.stripe_customer_id = None
    
    status = BillingService.get_subscription_status(mock_org)
    assert status["plan"] == "individual"
    assert status["status"] == "incomplete"
    assert "limits" in status
    
    mock_org.plan = "starter"
    mock_org.stripe_customer_id = "cus_999"
    
    status = BillingService.get_subscription_status(mock_org)
    assert status["plan"] == "starter"
    assert status["status"] == "active"
