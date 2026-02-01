
import stripe
from ..config import settings
from .entitlements import get_plan_features

stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingService:
    # Price amounts in cents for each plan
    PLAN_PRICES = {
        "fellowship": 2900,  # $29/month
        "starter": 2900,
        "ministry": 4900,    # $49/month 
        "growth": 4900,
        "church": 9900,      # $99/month
        "enterprise": 9900,
    }
    
    @staticmethod
    def create_checkout_session(
        org_id: str, 
        plan: str, 
        success_url: str, 
        cancel_url: str,
        locale: str = None,
        product_name: str = None,
        product_description: str = None,
        submit_message: str = None,
        after_submit_message: str = None,
    ):
        """Create a Stripe checkout session for a subscription with optional i18n."""
        # Determine if we should use price_data (dynamic) or price (existing product)
        use_price_data = product_name is not None or product_description is not None
        
        if use_price_data:
            # Use price_data for dynamic product info with translations
            unit_amount = BillingService.PLAN_PRICES.get(plan, 2900)
            
            product_data = {
                "name": product_name or f"{plan.title()} Plan",
            }
            if product_description:
                product_data["description"] = product_description[:500]  # Stripe limit
            
            line_item = {
                "price_data": {
                    "currency": "usd",
                    "product_data": product_data,
                    "unit_amount": unit_amount,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }
        else:
            # Fall back to existing price ID
            price_id = settings.STRIPE_PRICE_IDS.get(plan)
            if not price_id:
                # Fallback to direct settings if dict is empty
                if plan == "starter": price_id = settings.STRIPE_PRICE_STARTER
                elif plan == "growth": price_id = settings.STRIPE_PRICE_GROWTH
                elif plan == "enterprise": price_id = settings.STRIPE_PRICE_ENTERPRISE
                elif plan == "fellowship": price_id = settings.STRIPE_PRICE_STARTER
                elif plan == "ministry": price_id = settings.STRIPE_PRICE_GROWTH
                elif plan == "church": price_id = settings.STRIPE_PRICE_ENTERPRISE
                
            if not price_id:
                raise ValueError(f"Invalid plan: {plan}")
            
            line_item = {
                "price": price_id,
                "quantity": 1,
            }

        # Build session kwargs
        session_kwargs = {
            "payment_method_types": ["card"],
            "line_items": [line_item],
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "org_id": org_id,
                "plan": plan
            }
        }
        
        # Add locale if provided (Stripe uses 2-letter locale codes)
        if locale:
            # Map common locales to Stripe's supported format
            locale_map = {
                "en": "en",
                "es": "es", 
                "fr": "fr",
                "ru": "ru",
            }
            stripe_locale = locale_map.get(locale[:2], "auto")
            session_kwargs["locale"] = stripe_locale
        
        # Add custom_text for submit button if provided
        if submit_message or after_submit_message:
            custom_text = {}
            if submit_message:
                custom_text["submit"] = {"message": submit_message[:1200]}  # Stripe limit
            if after_submit_message:
                custom_text["after_submit"] = {"message": after_submit_message[:1200]}
            session_kwargs["custom_text"] = custom_text

        session = stripe.checkout.Session.create(**session_kwargs)
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
