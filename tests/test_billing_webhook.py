"""
Tests for billing webhook and event store idempotency.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import json


class TestEventStore:
    """Tests for the Redis-based event store service."""

    def test_is_event_processed_returns_false_when_redis_disabled(self):
        """When Redis is disabled, should return False (fail-open)."""
        with patch('app.services.event_store.settings') as mock_settings:
            mock_settings.REDIS_ENABLED = False
            
            from app.services.event_store import is_event_processed
            result = is_event_processed("evt_test123")
            
            assert result is False

    def test_is_event_processed_returns_false_when_redis_unavailable(self):
        """When Redis connection fails, should return False (fail-open)."""
        with patch('app.services.event_store.settings') as mock_settings:
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = "redis://nonexistent:6379"
            
            from app.services.event_store import is_event_processed
            result = is_event_processed("evt_test456")
            
            assert result is False

    def test_mark_event_processed_returns_false_when_redis_disabled(self):
        """When Redis is disabled, should return False."""
        with patch('app.services.event_store.settings') as mock_settings:
            mock_settings.REDIS_ENABLED = False
            
            from app.services.event_store import mark_event_processed
            result = mark_event_processed("evt_test789")
            
            assert result is False

    def test_event_store_uses_correct_key_prefix(self):
        """Event keys should use 'stripe_event:' prefix."""
        from app.services.event_store import KEY_PREFIX
        assert KEY_PREFIX == "stripe_event:"

    def test_event_ttl_is_24_hours(self):
        """Event TTL should be 24 hours (86400 seconds)."""
        from app.services.event_store import EVENT_TTL_SECONDS
        assert EVENT_TTL_SECONDS == 24 * 60 * 60


class TestBillingWebhook:
    """Tests for the billing webhook endpoint."""

    def test_webhook_missing_signature_returns_400(self, client):
        """Webhook without signature should return 400."""
        response = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps({"type": "test"}),
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert "Missing Stripe signature" in response.json()["detail"]

    def test_webhook_invalid_signature_returns_400(self, client):
        """Webhook with invalid signature should return 400."""
        response = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps({"type": "test"}),
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "invalid_sig"
            }
        )
        assert response.status_code == 400

    @patch('app.routers.billing.stripe.Webhook.construct_event')
    @patch('app.routers.billing.is_event_processed')
    @patch('app.routers.billing.mark_event_processed')
    def test_duplicate_event_returns_already_processed(
        self, mock_mark, mock_is_processed, mock_construct, client
    ):
        """Already processed events should return success without reprocessing."""
        mock_construct.return_value = {
            "id": "evt_duplicate",
            "type": "checkout.session.completed",
            "data": {"object": {}}
        }
        mock_is_processed.return_value = True  # Already processed
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps({"type": "test"}),
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "valid_sig"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "already_processed"
        mock_mark.assert_not_called()  # Should not mark again

    @patch('app.routers.billing.stripe.Webhook.construct_event')
    @patch('app.routers.billing.is_event_processed')
    @patch('app.routers.billing.mark_event_processed')
    def test_new_event_is_processed_and_marked(
        self, mock_mark, mock_is_processed, mock_construct, client
    ):
        """New events should be processed and marked in Redis."""
        mock_construct.return_value = {
            "id": "evt_new123",
            "type": "invoice.payment_succeeded",
            "data": {"object": {"customer": "cus_xyz", "amount_paid": 1000}}
        }
        mock_is_processed.return_value = False  # Not yet processed
        mock_mark.return_value = True
        
        response = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps({"type": "test"}),
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "valid_sig"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_mark.assert_called_once_with("evt_new123")

    @patch('app.routers.billing.stripe.Webhook.construct_event')
    @patch('app.routers.billing.is_event_processed')
    def test_unhandled_event_type_succeeds(
        self, mock_is_processed, mock_construct, client
    ):
        """Unhandled event types should still succeed without error."""
        mock_construct.return_value = {
            "id": "evt_unhandled",
            "type": "some.unknown.event",
            "data": {"object": {}}
        }
        mock_is_processed.return_value = False
        
        with patch('app.routers.billing.mark_event_processed'):
            response = client.post(
                "/api/v1/billing/webhook",
                content=json.dumps({"type": "test"}),
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": "valid_sig"
                }
            )
        
        assert response.status_code == 200


class TestPriceToPlanMapping:
    """Tests for the price ID to plan name mapping."""

    def test_map_price_to_plan_returns_correct_plan(self):
        """Valid price IDs should map to correct plan names."""
        with patch('app.routers.billing.settings') as mock_settings:
            mock_settings.STRIPE_PRICE_STARTER = "price_starter_123"
            mock_settings.STRIPE_PRICE_GROWTH = "price_growth_456"
            mock_settings.STRIPE_PRICE_ENTERPRISE = "price_enterprise_789"
            
            from app.routers.billing import map_price_to_plan
            
            assert map_price_to_plan("price_starter_123") == "starter"
            assert map_price_to_plan("price_growth_456") == "growth"
            assert map_price_to_plan("price_enterprise_789") == "enterprise"

    def test_map_price_to_plan_returns_none_for_unknown(self):
        """Unknown price IDs should return None."""
        with patch('app.routers.billing.settings') as mock_settings:
            mock_settings.STRIPE_PRICE_STARTER = "price_starter_123"
            mock_settings.STRIPE_PRICE_GROWTH = "price_growth_456"
            mock_settings.STRIPE_PRICE_ENTERPRISE = "price_enterprise_789"
            
            from app.routers.billing import map_price_to_plan
            
            assert map_price_to_plan("price_unknown") is None


class TestBillingEventHandlers:
    """Tests for individual webhook event handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_checkout_completed_activates_plan(self, db):
        """Checkout completed should activate subscription for org."""
        from app.routers.billing import handle_checkout_completed
        from app.models import Organization
        import uuid
        
        # Create test org
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Test Org", slug="test-checkout-" + str(org_id)[:8], plan="free")
        db.add(org)
        db.commit()
        
        event = {
            "data": {
                "object": {
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "metadata": {"org_id": str(org_id), "plan": "growth"}
                }
            }
        }
        
        await handle_checkout_completed(event, db)
        
        db.refresh(org)
        assert org.plan == "growth"
        assert org.stripe_customer_id == "cus_test123"

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_without_org_id(self, db):
        """Checkout without org_id in metadata should not crash."""
        from app.routers.billing import handle_checkout_completed
        
        event = {
            "data": {
                "object": {
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "metadata": {}  # No org_id
                }
            }
        }
        
        # Should not raise
        await handle_checkout_completed(event, db)

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_downgrades_to_free(self, db):
        """Subscription deletion should downgrade org to free plan."""
        from app.routers.billing import handle_subscription_deleted
        from app.models import Organization
        import uuid
        
        # Create test org with active subscription
        org_id = uuid.uuid4()
        org = Organization(
            id=org_id, 
            name="Test Org", 
            slug="test-cancel-" + str(org_id)[:8], 
            plan="growth",
            stripe_customer_id="cus_delete_test"
        )
        db.add(org)
        db.commit()
        
        event = {
            "data": {
                "object": {
                    "customer": "cus_delete_test"
                }
            }
        }
        
        await handle_subscription_deleted(event, db)
        
        db.refresh(org)
        assert org.plan == "free"

    @pytest.mark.asyncio
    async def test_handle_invoice_paid_logs_successfully(self, db):
        """Invoice paid should log without error."""
        from app.routers.billing import handle_invoice_paid
        
        event = {
            "data": {
                "object": {
                    "customer": "cus_invoice",
                    "amount_paid": 2999
                }
            }
        }
        
        # Should not raise
        await handle_invoice_paid(event, db)

    @pytest.mark.asyncio
    async def test_handle_invoice_failed_logs_warning(self, db):
        """Invoice failed should log warning without error."""
        from app.routers.billing import handle_invoice_failed
        
        event = {
            "data": {
                "object": {
                    "customer": "cus_failed"
                }
            }
        }
        
        # Should not raise
        await handle_invoice_failed(event, db)


class TestEventStoreRedisOperations:
    """Tests for event store with mocked Redis client."""
    
    def test_is_event_processed_with_existing_key(self):
        """Should return True when event key exists in Redis."""
        with patch('app.services.event_store.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.exists.return_value = 1
            mock_get_client.return_value = mock_client
            
            from app.services.event_store import is_event_processed
            result = is_event_processed("evt_exists")
            
            assert result is True
            mock_client.exists.assert_called_once_with("stripe_event:evt_exists")
    
    def test_is_event_processed_with_missing_key(self):
        """Should return False when event key does not exist."""
        with patch('app.services.event_store.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.exists.return_value = 0
            mock_get_client.return_value = mock_client
            
            from app.services.event_store import is_event_processed
            result = is_event_processed("evt_missing")
            
            assert result is False
    
    def test_mark_event_processed_success(self):
        """Should set key with TTL and return True."""
        with patch('app.services.event_store.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            from app.services.event_store import mark_event_processed, EVENT_TTL_SECONDS
            result = mark_event_processed("evt_new")
            
            assert result is True
            mock_client.setex.assert_called_once_with(
                "stripe_event:evt_new", 
                EVENT_TTL_SECONDS, 
                "1"
            )
    
    def test_is_event_processed_handles_exception(self):
        """Should return False on Redis exception."""
        with patch('app.services.event_store.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.exists.side_effect = Exception("Redis error")
            mock_get_client.return_value = mock_client
            
            from app.services.event_store import is_event_processed
            result = is_event_processed("evt_error")
            
            assert result is False
    
    def test_mark_event_processed_handles_exception(self):
        """Should return False on Redis exception."""
        with patch('app.services.event_store.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.setex.side_effect = Exception("Redis error")
            mock_get_client.return_value = mock_client
            
            from app.services.event_store import mark_event_processed
            result = mark_event_processed("evt_error")
            
            assert result is False

