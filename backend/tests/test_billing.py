import uuid
from datetime import UTC, datetime

import pytest

from src.billing import service
from src.billing.plans import PLANS, get_plan
from src.billing.quota import (
    QuotaExceeded,
    enforce_query_quota,
    month_query_count,
    usage_summary,
)
from src.config.settings import Settings
from src.db.database import Database


@pytest.fixture
def db(settings) -> Database:
    return Database(None, settings.data_dir)


def _add_query(db, org_id):
    db.execute(
        "INSERT INTO usage_events (id, org_id, user_id, ts, kind, tokens, providers) "
        "VALUES (?, ?, 'u', ?, 'query', 0, 'stub')",
        (f"use_{uuid.uuid4().hex[:12]}", org_id, datetime.now(UTC).isoformat()),
    )


def test_get_plan():
    assert get_plan(None).id == "free"
    assert get_plan("pro").queries_per_month == 1000
    assert get_plan("nonsense").id == "free"


def test_month_query_count_and_summary(db):
    for _ in range(3):
        _add_query(db, "org1")
    assert month_query_count(db, "org1") == 3
    s = usage_summary(db, "org1", "free")
    assert s["queries_used"] == 3
    assert s["queries_remaining"] == PLANS["free"].queries_per_month - 3


def test_enforce_query_quota(db):
    enforce_query_quota(db, "org1", "free")  # 0 used -> ok
    for _ in range(PLANS["free"].queries_per_month):
        _add_query(db, "org1")
    with pytest.raises(QuotaExceeded):
        enforce_query_quota(db, "org1", "free")


def test_stripe_guarded_when_unconfigured(db):
    settings = Settings()  # no stripe key
    assert service.is_configured(settings) is False
    with pytest.raises(Exception) as exc:
        service.create_checkout_session(settings, "org1", "pro", "s", "c")
    assert "not configured" in str(exc.value).lower()


def test_cost_estimation():
    from src.agents.schemas import ProviderCall
    from src.billing.pricing import estimate_cost, price_per_m

    assert price_per_m("stub-llm-v1") == 0.0
    assert price_per_m("gemini-2.5-flash") == 0.30
    trace = [ProviderCall(provider="gemini", model="gemini-2.5-flash", tokens=1_000_000)]
    assert estimate_cost(trace) == 0.30
    # cached calls don't cost
    trace.append(
        ProviderCall(provider="gemini", model="gemini-2.5-flash", tokens=1_000_000, cached=True)
    )
    assert estimate_cost(trace) == 0.30


def test_usage_summary_includes_cost(db):
    for _ in range(2):
        _add_query(db, "org1")
    s = usage_summary(db, "org1", "free")
    assert "tokens_used" in s and "est_cost_usd" in s


def test_billing_api_wiring():
    from fastapi.testclient import TestClient

    from src.api.main import app

    client = TestClient(app)
    plans = client.get("/billing/plans")
    assert plans.status_code == 200
    assert len(plans.json()["plans"]) == 3

    usage = client.get("/usage")  # demo tenant
    assert usage.status_code == 200
    assert usage.json()["queries_used"] == 0
    assert usage.json()["plan"]["id"] == "free"
