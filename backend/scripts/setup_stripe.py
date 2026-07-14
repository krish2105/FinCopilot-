#!/usr/bin/env python
"""One-shot Stripe setup (Phase 35).

Checkout needs a Stripe **Price id** per paid plan, and those only exist once the
products are created in your Stripe account. This script creates them idempotently
(it reuses a product/price if one already matches) and prints the two env vars to
paste into Render.

Usage:
    cd backend
    STRIPE_SECRET_KEY=sk_test_... python scripts/setup_stripe.py

Safe to re-run. Uses whatever mode the key implies — a `sk_test_` key creates
test-mode products, a live key creates live ones.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.billing.plans import PLANS  # noqa: E402


def main() -> int:
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key:
        print("ERROR: set STRIPE_SECRET_KEY (sk_test_... for test mode).")
        return 1

    try:
        import stripe
    except ImportError:
        print("ERROR: pip install stripe")
        return 1

    stripe.api_key = key
    mode = "TEST" if key.startswith("sk_test_") else "LIVE"
    print(f"Stripe mode: {mode}\n")

    env_lines: list[str] = []
    for plan in PLANS.values():
        if not plan.stripe_price_env or plan.price_usd_month <= 0:
            continue  # free plan needs no price

        lookup = f"fincopilot_{plan.id}_monthly"

        # Reuse an existing price with our lookup key if one is already there.
        existing = stripe.Price.search(query=f'lookup_key:"{lookup}" AND active:"true"')
        if existing.data:
            price = existing.data[0]
            print(f"✓ {plan.name}: reusing existing price {price.id}")
        else:
            product = stripe.Product.create(
                name=f"FinCopilot {plan.name}",
                description=" · ".join(plan.features),
                metadata={"plan_id": plan.id},
            )
            price = stripe.Price.create(
                product=product.id,
                unit_amount=plan.price_usd_month * 100,  # cents
                currency="usd",
                recurring={"interval": "month"},
                lookup_key=lookup,
                metadata={"plan_id": plan.id},
            )
            print(f"✓ {plan.name}: created price {price.id} (${plan.price_usd_month}/mo)")

        env_lines.append(f"{plan.stripe_price_env}={price.id}")

    print("\n" + "=" * 62)
    print("Add these to Render → fincopilot-api → Environment:\n")
    for line in env_lines:
        print("  " + line)
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
