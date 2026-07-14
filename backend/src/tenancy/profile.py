"""User personalization profile (Phase 49) — derived, not stored.

Memory in a financial product is dangerous if you cache *facts*: a company's numbers
change every quarter, so a remembered figure is a latent wrong answer. So we remember
only the user's *context* — which companies they research and what they ask — and we
derive even that from the audit trail we already keep, rather than maintaining a second
store that could drift out of sync.

The result powers "welcome back, you've been researching AAPL and MSFT" and one-tap
resume of recent questions: a tool that remembers you, without ever remembering a
financial fact.
"""

from __future__ import annotations

from collections import Counter

from src.db.database import Database
from src.tenancy import repo


def build_profile(db: Database, org_id: str, limit: int = 200) -> dict:
    audit = repo.recent_audit(db, org_id, limit=limit)

    ticker_counts: Counter[str] = Counter()
    recent_questions: list[dict] = []
    seen_q: set[str] = set()

    for row in audit:
        for t in row.get("tickers") or []:
            if t:
                ticker_counts[t.upper()] += 1
        q = (row.get("query") or "").strip()
        if q and q.lower() not in seen_q and len(recent_questions) < 8:
            seen_q.add(q.lower())
            recent_questions.append(
                {"query": q, "route": row.get("route"), "verdict": row.get("verdict")}
            )

    top_tickers = [t for t, _ in ticker_counts.most_common(6)]
    return {
        "total_queries": repo.audit_count(db, org_id),
        "top_tickers": top_tickers,
        "recent_questions": recent_questions,
        "returning": len(audit) > 0,
    }
