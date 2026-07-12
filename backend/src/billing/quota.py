"""Usage metering + quota enforcement (Phase 11).

Counts usage from the audit-adjacent usage_events table and blocks requests that
would exceed the org's plan. Query and document quotas are enforced before the
expensive work runs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from src.billing.plans import Plan, get_plan
from src.db.database import Database


class QuotaExceeded(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=402, detail=detail)


def _month_start_iso() -> str:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def month_query_count(db: Database, org_id: str) -> int:
    row = db.query_one(
        "SELECT COUNT(*) AS n FROM usage_events WHERE org_id = ? AND kind = 'query' AND ts >= ?",
        (org_id, _month_start_iso()),
    )
    return int(row["n"]) if row else 0


def document_count(db: Database, org_id: str) -> int:
    row = db.query_one("SELECT COUNT(*) AS n FROM documents WHERE org_id = ?", (org_id,))
    return int(row["n"]) if row else 0


def usage_summary(db: Database, org_id: str, plan_id: str) -> dict:
    plan = get_plan(plan_id)
    q = month_query_count(db, org_id)
    d = document_count(db, org_id)
    return {
        "plan": plan.model_dump(),
        "queries_used": q,
        "queries_limit": plan.queries_per_month,
        "queries_remaining": max(0, plan.queries_per_month - q),
        "documents_used": d,
        "documents_limit": plan.max_documents,
    }


def enforce_query_quota(db: Database, org_id: str, plan_id: str) -> None:
    plan: Plan = get_plan(plan_id)
    if month_query_count(db, org_id) >= plan.queries_per_month:
        raise QuotaExceeded(
            f"Monthly query limit reached ({plan.queries_per_month} on the {plan.name} plan). "
            "Upgrade to continue."
        )


def enforce_document_quota(db: Database, org_id: str, plan_id: str) -> None:
    plan = get_plan(plan_id)
    if document_count(db, org_id) >= plan.max_documents:
        raise QuotaExceeded(
            f"Document limit reached ({plan.max_documents} on the {plan.name} plan). Upgrade to add more."
        )
