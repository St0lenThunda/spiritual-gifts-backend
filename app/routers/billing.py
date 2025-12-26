"""
Billing router for Stripe webhook handling with idempotency.
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
import stripe
import logging

from ..config import settings
from ..database import get_db
from ..models import Organization
from ..services.event_store import is_event_processed, mark_event_processed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events with idempotency.
    
    Uses Redis to track processed event IDs and prevent duplicate processing.
    Events are stored for 24 hours before TTL expiration.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_id = event["id"]
    event_type = event["type"]
    
    # Idempotency check - skip if already processed
    if is_event_processed(event_id):
        logger.info(f"Skipping duplicate event: {event_id} ({event_type})")
        return {"status": "already_processed", "event_id": event_id}
    
    logger.info(f"Processing Stripe event: {event_id} ({event_type})")
    
    # Handle event types
    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event, db)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event, db)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event, db)
        elif event_type == "invoice.payment_succeeded":
            await handle_invoice_paid(event, db)
        elif event_type == "invoice.payment_failed":
            await handle_invoice_failed(event, db)
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        # Mark event as processed after successful handling
        mark_event_processed(event_id)
        
        return {"status": "success", "event_id": event_id}
    
    except Exception as e:
        logger.exception(f"Error processing event {event_id}: {e}")
        # Don't mark as processed on error - allow retry
        raise HTTPException(status_code=500, detail="Event processing failed")


async def handle_checkout_completed(event: dict, db: Session):
    """Handle successful checkout - activate subscription."""
    session = event["data"]["object"]
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})
    org_id = metadata.get("org_id")
    plan = metadata.get("plan", "starter")
    
    if not org_id:
        logger.warning("Checkout completed without org_id in metadata")
        return
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org:
        org.stripe_customer_id = customer_id
        org.plan = plan
        db.commit()
        logger.info(f"Activated {plan} plan for org {org_id}")


async def handle_subscription_updated(event: dict, db: Session):
    """Handle subscription changes (upgrades/downgrades)."""
    subscription = event["data"]["object"]
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    org = db.query(Organization).filter(
        Organization.stripe_customer_id == customer_id
    ).first()
    
    if org and status == "active":
        # Get plan from subscription items
        items = subscription.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id", "")
            # Map price IDs to plan names (configure in settings)
            plan = map_price_to_plan(price_id)
            if plan:
                org.plan = plan
                db.commit()
                logger.info(f"Updated plan for org {org.id} to {plan}")


async def handle_subscription_deleted(event: dict, db: Session):
    """Handle subscription cancellation."""
    subscription = event["data"]["object"]
    customer_id = subscription.get("customer")
    
    org = db.query(Organization).filter(
        Organization.stripe_customer_id == customer_id
    ).first()
    
    if org:
        org.plan = "free"
        db.commit()
        logger.info(f"Downgraded org {org.id} to free plan")


async def handle_invoice_paid(event: dict, db: Session):
    """Log successful payment (subscription renewal)."""
    invoice = event["data"]["object"]
    customer_id = invoice.get("customer")
    amount_paid = invoice.get("amount_paid", 0) / 100
    
    logger.info(f"Invoice paid for customer {customer_id}: ${amount_paid}")


async def handle_invoice_failed(event: dict, db: Session):
    """Handle failed payment - could trigger email notification."""
    invoice = event["data"]["object"]
    customer_id = invoice.get("customer")
    
    logger.warning(f"Invoice payment failed for customer {customer_id}")
    # TODO: Send notification email to org admin


def map_price_to_plan(price_id: str) -> str | None:
    """Map Stripe price ID to plan name."""
    # Configure these in settings or database
    price_map = {
        settings.STRIPE_PRICE_STARTER: "starter",
        settings.STRIPE_PRICE_GROWTH: "growth",
        settings.STRIPE_PRICE_ENTERPRISE: "enterprise",
    }
    return price_map.get(price_id)
