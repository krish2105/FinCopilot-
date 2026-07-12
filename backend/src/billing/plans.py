"""Subscription plans and quota limits (Phase 11)."""

from __future__ import annotations

from pydantic import BaseModel


class Plan(BaseModel):
    id: str
    name: str
    price_usd_month: int
    queries_per_month: int
    max_documents: int
    max_seats: int
    features: list[str]
    stripe_price_env: str | None = None  # env var holding the Stripe price id


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_usd_month=0,
        queries_per_month=25,
        max_documents=3,
        max_seats=1,
        features=["Public filings corpus", "Cited answers", "1 data room"],
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_usd_month=49,
        queries_per_month=1000,
        max_documents=100,
        max_seats=1,
        features=["Everything in Free", "Document upload", "GraphRAG", "Audit + export"],
        stripe_price_env="STRIPE_PRICE_PRO",
    ),
    "team": Plan(
        id="team",
        name="Team",
        price_usd_month=199,
        queries_per_month=5000,
        max_documents=2000,
        max_seats=10,
        features=["Everything in Pro", "10 seats", "Shared data rooms", "Priority support"],
        stripe_price_env="STRIPE_PRICE_TEAM",
    ),
}


def get_plan(plan_id: str | None) -> Plan:
    return PLANS.get(plan_id or "free", PLANS["free"])
