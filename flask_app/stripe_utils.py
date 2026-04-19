import os
import stripe
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICING = {
    "small": {
        "name": "Small MUN",
        "price": 199,
        "max_delegates": 100,
    },
    "medium": {
        "name": "Medium MUN",
        "price": 399,
        "max_delegates": 200,
    },
    "large": {
        "name": "Large MUN",
        "price": 499,
        "max_delegates": 250,
        "per_delegate": 2,
    },
}


def get_or_create_product(plan_key: str, plan_info: dict) -> str:
    """Get or create a Stripe product dynamically."""
    try:
        # Search for existing product by name
        products = stripe.Product.list(active=True, limit=100)
        for p in products.data:
            if p.name == f"MUN SaaS - {plan_info['name']}":
                # Find the active price
                prices = stripe.Price.list(product=p.id, active=True, limit=10)
                for price in prices.data:
                    if price.unit_amount == plan_info["price"] * 100:
                        return price.id
                # Create new price if product exists but no matching price
                new_price = stripe.Price.create(
                    product=p.id,
                    unit_amount=plan_info["price"] * 100,
                    currency="aed",
                )
                return new_price.id

        # Create new product if not found
        product = stripe.Product.create(
            name=f"MUN SaaS - {plan_info['name']}",
            description=f"{plan_info['name']} - Up to {plan_info['max_delegates']} delegates",
        )
        price = stripe.Price.create(
            product=product.id,
            unit_amount=plan_info["price"] * 100,
            currency="aed",
        )
        return price.id
    except Exception as e:
        print(f"Stripe product error: {e}")
        return None


# Cache price IDs
_cached_prices = {}


def get_price_id(plan_key: str) -> str:
    """Get the Stripe price ID for a plan, creating if needed."""
    if plan_key in _cached_prices:
        return _cached_prices[plan_key]

    if plan_key not in PRICING:
        return None

    # Try to get/create the product
    price_id = get_or_create_product(plan_key, PRICING[plan_key])
    if price_id:
        _cached_prices[plan_key] = price_id
    return price_id


def calculate_price(plan: str, delegate_count: int = 0) -> int:
    """Calculate the price based on plan and delegate count."""
    if plan == "small":
        return 199
    elif plan == "medium":
        return 399
    elif plan == "large":
        base = 500
        if delegate_count > 250:
            return base + (delegate_count - 250) * 2
        return base
    return 0


def calculate_upgrade_price(
    from_plan: str, to_plan: str, delegate_count: int = 0
) -> int:
    """Calculate upgrade price (difference only)."""
    from_price = calculate_price(from_plan, delegate_count)
    to_price = calculate_price(to_plan, delegate_count)
    return max(0, to_price - from_price)


def create_checkout_session(
    user_email: str,
    user_name: str,
    event_id: str,
    event_name: str,
    plan: str,
    success_url: str,
    cancel_url: str,
    is_upgrade: bool = False,
    current_plan: str = None,
    delegate_count: int = 0,
) -> str:
    """Create a Stripe checkout session and return the URL."""

    price = calculate_price(plan, delegate_count)

    if is_upgrade and current_plan:
        price = calculate_upgrade_price(current_plan, plan, delegate_count)
        if price <= 0:
            return None

    # Get price ID dynamically
    price_id = get_price_id(plan)

    if not price_id:
        # Fallback: create checkout without price_id (use amount)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "aed",
                        "product_data": {
                            "name": f"MUN SaaS - {PRICING[plan]['name']}",
                            "description": f"Event: {event_name}"
                            + (f" (Upgrade)" if is_upgrade else ""),
                        },
                        "unit_amount": int(price * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user_email,
            metadata={
                "event_id": event_id,
                "plan": plan,
                "is_upgrade": str(is_upgrade).lower(),
                "from_plan": current_plan or "",
            },
        )
    else:
        # Use price ID
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user_email,
            metadata={
                "event_id": event_id,
                "plan": plan,
                "is_upgrade": str(is_upgrade).lower(),
                "from_plan": current_plan or "",
            },
        )

    return session.url


def verify_payment(session_id: str) -> dict:
    """Verify payment was successful."""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            return {
                "paid": True,
                "amount": session.amount_total,
                "customer_email": session.customer_email,
            }
    except Exception as e:
        print(f"Stripe verify error: {e}")
    return {"paid": False}


def construct_webhook_event(payload: bytes, signature: str) -> dict:
    """Construct and verify webhook event."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        return None
    try:
        return stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except ValueError:
        return None
    except stripe.error.SignatureVerificationError:
        return None
