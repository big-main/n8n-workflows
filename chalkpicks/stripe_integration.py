import logging
import os
from typing import Optional, Tuple

import stripe

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

TIER_PRICE_IDS = {
    "pro":   os.getenv("STRIPE_PRO_PRICE_ID",   ""),
    "sharp": os.getenv("STRIPE_SHARP_PRICE_ID", ""),
}

PLAN_DETAILS = {
    "free":  {"name": "Chalk Free",  "monthly_cents": 0,    "picks_per_day": 3,  "features": ["3 picks/day", "Basic ChalkScore", "Public stats"]},
    "pro":   {"name": "Chalk Pro",   "monthly_cents": 1999, "picks_per_day": -1, "features": ["Unlimited picks", "Full analysis", "Line movement charts", "Sharp money tracker", "Email alerts"]},
    "sharp": {"name": "Chalk Sharp", "monthly_cents": 4999, "picks_per_day": -1, "features": ["Everything in Pro", "Elite AI picks", "ROI dashboard", "Early-line access", "Parlay builder", "Priority support"]},
}


async def create_checkout_session(
    user_id: int,
    email: str,
    tier: str,
    success_url: str,
    cancel_url: str,
) -> Optional[str]:
    if not stripe.api_key or not TIER_PRICE_IDS.get(tier):
        logger.warning("Stripe not configured — returning None for checkout URL")
        return None

    try:
        session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[{"price": TIER_PRICE_IDS[tier], "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": str(user_id), "tier": tier},
            subscription_data={"metadata": {"user_id": str(user_id), "tier": tier}},
            allow_promotion_codes=True,
        )
        return session.url
    except stripe.error.StripeError as exc:
        logger.error(f"Stripe checkout error: {exc}")
        return None


async def create_billing_portal(customer_id: str, return_url: str) -> Optional[str]:
    if not stripe.api_key:
        return None
    try:
        session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
        return session.url
    except stripe.error.StripeError as exc:
        logger.error(f"Stripe portal error: {exc}")
        return None


def verify_webhook(payload: bytes, sig_header: str) -> Optional[dict]:
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        return None
    try:
        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except (stripe.error.SignatureVerificationError, ValueError) as exc:
        logger.error(f"Webhook verification failed: {exc}")
        return None


def extract_event_metadata(event: dict) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Return (user_id, tier, customer_id, subscription_id) from a Stripe event."""
    obj = event.get("data", {}).get("object", {})
    meta = obj.get("metadata", {})
    return (
        meta.get("user_id"),
        meta.get("tier"),
        obj.get("customer"),
        obj.get("id") if event["type"].startswith("customer.subscription") else obj.get("subscription"),
    )
