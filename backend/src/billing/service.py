"""Stripe integration (Phase 11) — guarded.

Activates only when STRIPE_SECRET_KEY is set; otherwise endpoints report that
billing isn't configured (so the app runs free/offline). Subscription state is
mirrored onto the org row so quota enforcement reads a single source of truth.
"""

from __future__ import annotations

import logging
import os

from fastapi import HTTPException

from src.billing.plans import get_plan
from src.config.settings import Settings
from src.db.database import Database

logger = logging.getLogger(__name__)


def is_configured(settings: Settings) -> bool:
    return bool(settings.stripe_secret_key)


def _client(settings: Settings):
    if not is_configured(settings):
        raise HTTPException(status_code=501, detail="Billing is not configured.")
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


def create_checkout_session(
    settings: Settings, org_id: str, plan_id: str, success_url: str, cancel_url: str
) -> str:
    stripe = _client(settings)
    plan = get_plan(plan_id)
    price_id = os.getenv(plan.stripe_price_env or "", "")
    if not price_id:
        raise HTTPException(status_code=400, detail=f"No Stripe price configured for {plan.name}.")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=org_id,
        metadata={"org_id": org_id, "plan_id": plan_id},
    )
    return session.url


def create_portal_session(settings: Settings, db: Database, org_id: str, return_url: str) -> str:
    stripe = _client(settings)
    row = db.query_one("SELECT stripe_customer_id FROM orgs WHERE id = ?", (org_id,))
    if not row or not row["stripe_customer_id"]:
        raise HTTPException(status_code=400, detail="No billing account yet.")
    session = stripe.billing_portal.Session.create(
        customer=row["stripe_customer_id"], return_url=return_url
    )
    return session.url


def handle_webhook(
    settings: Settings, db: Database, payload: bytes, sig_header: str | None
) -> dict:
    stripe = _client(settings)
    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid webhook signature: {exc}"
            ) from exc
    else:
        import json

        event = json.loads(payload)

    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    org_id = (obj.get("metadata") or {}).get("org_id") or obj.get("client_reference_id")

    if etype == "checkout.session.completed" and org_id:
        plan_id = (obj.get("metadata") or {}).get("plan_id", "pro")
        db.execute(
            "UPDATE orgs SET plan = ?, stripe_customer_id = ?, stripe_subscription_id = ? WHERE id = ?",
            (plan_id, obj.get("customer"), obj.get("subscription"), org_id),
        )
    elif etype == "customer.subscription.deleted" and obj.get("customer"):
        db.execute(
            "UPDATE orgs SET plan = 'free' WHERE stripe_customer_id = ?", (obj.get("customer"),)
        )
    return {"received": True, "type": etype}
