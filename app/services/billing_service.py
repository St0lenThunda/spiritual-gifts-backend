
import stripe
from ..config import settings
from .entitlements import get_plan_features

stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingService:
    @staticmethod
    def create_checkout_session(org_id: str, plan: str, success_url: str, cancel_url: str):
        """Create a Stripe checkout session for a subscription."""
        # Find price ID from settings
        price_id = settings.STRIPE_PRICE_IDS.get(plan)
        if not price_id:
            # Fallback to direct settings if dict is empty
            if plan == "starter": price_id = settings.STRIPE_PRICE_STARTER
            elif plan == "growth": price_id = settings.STRIPE_PRICE_GROWTH
            elif plan == "enterprise": price_id = settings.STRIPE_PRICE_ENTERPRISE
            
        if not price_id:
            raise ValueError(f"Invalid plan: {plan}")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "org_id": org_id,
                "plan": plan
            }
        )
        return session

    @staticmethod
    def create_portal_session(customer_id: str, return_url: str):
        """Create a Stripe customer portal session."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session

    @staticmethod
    def get_subscription_status(org):
        """Get summary of subscription status for an organization."""
        # This is a simplified version - in a real app you might query Stripe for real-time status
        return {
            "plan": org.plan,
            "status": "active" if org.stripe_customer_id else "incomplete",
            "limits": get_plan_features(org.plan)
        }
