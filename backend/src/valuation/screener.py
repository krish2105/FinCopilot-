"""Stock screener over filed XBRL facts (Phase 48).

A screener is where a natural-language product could reach for text-to-SQL, but letting
a model write SQL against your database is a security decision, not a feature. Instead we
expose a fixed, typed set of filterable metrics and evaluate them deterministically over
the facts we already hold — same expressive power for "profitable companies with net
margin over 20%", none of the injection surface.

Every value is a filed figure (Phase 45), so the screen is auditable: each row can be
traced back to the filing it came from.
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.database import Database
from src.xbrl import lookup, store

logger = logging.getLogger(__name__)

# The columns a user can screen on. Each maps to a filed metric or a derived one.
FIELDS: dict[str, str] = {
    "revenue": "revenue",
    "net_income": "net_income",
    "net_margin": "net_margin_pct",
    "gross_margin": "gross_margin_pct",
    "operating_margin": "operating_margin_pct",
    "free_cash_flow": "free_cash_flow",
    "rnd_expense": "rnd_expense",
    "assets": "assets",
    "cash": "cash",
    "eps": "eps_diluted",
}


def _metric(db: Database, ticker: str, metric: str) -> float | None:
    from src.xbrl.concepts import DERIVED

    f = lookup.derived(db, ticker, metric) if metric in DERIVED else lookup.get_fact(db, ticker, metric)
    return f["value"] if f else None


def row_for(db: Database, ticker: str) -> dict[str, Any]:
    """Latest filed value of every screenable field for one company."""
    row: dict[str, Any] = {"ticker": ticker.upper()}
    for field, metric in FIELDS.items():
        row[field] = _metric(db, ticker, metric)
    return row


def screen(db: Database, filters: list[dict], universe: list[str] | None = None) -> dict:
    """Return companies passing every filter.

    A filter is ``{"field": "net_margin", "op": ">", "value": 20}``. Rows missing a
    filtered field are excluded (you cannot pass a threshold on data that wasn't filed).
    """
    universe = [t.upper() for t in (universe or store.tickers(db))]
    ops = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
    }

    results: list[dict] = []
    for ticker in universe:
        row = row_for(db, ticker)
        ok = True
        for f in filters:
            field, op, value = f.get("field"), f.get("op"), f.get("value")
            if field not in FIELDS or op not in ops:
                continue
            cell = row.get(field)
            if cell is None or not ops[op](cell, value):
                ok = False
                break
        if ok:
            results.append(row)

    # Sort by the first numeric filter's field, descending, so the "best" lead.
    sort_field = next((f["field"] for f in filters if f.get("field") in FIELDS), "revenue")
    results.sort(key=lambda r: (r.get(sort_field) is None, -(r.get(sort_field) or 0)))
    return {"count": len(results), "fields": list(FIELDS), "results": results}
