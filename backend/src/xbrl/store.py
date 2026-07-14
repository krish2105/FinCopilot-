"""Persistence for XBRL facts (Phase 45).

Facts land in Postgres alongside the corpus, so a numeric lookup is a single indexed
query rather than a retrieval + LLM extraction round-trip.

One subtlety worth stating: **the same period gets filed more than once.** Apple's
FY2025 10-K restates FY2024 revenue, so `(concept, period_end)` alone is not unique —
you get the original filing and every later restatement. We keep them all (the
accession number is part of the key, so an audit trail survives) and let the lookup
prefer the most recently *filed* value, which is the restated, most-correct one.
"""

from __future__ import annotations

import logging

from src.db.database import Database

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS xbrl_facts (
    ticker        TEXT NOT NULL,
    concept       TEXT NOT NULL,
    unit          TEXT NOT NULL,
    period_end    TEXT NOT NULL,
    period_start  TEXT,
    fiscal_year   INTEGER,
    fiscal_period TEXT,
    form          TEXT,
    val           DOUBLE PRECISION,
    accn          TEXT NOT NULL,
    filed         TEXT,
    PRIMARY KEY (ticker, concept, unit, period_end, accn)
)
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_xbrl_lookup ON xbrl_facts (ticker, concept, period_end DESC)",
    "CREATE INDEX IF NOT EXISTS idx_xbrl_fy ON xbrl_facts (ticker, concept, fiscal_year DESC)",
]


def init_schema(db: Database) -> None:
    db.execute(SCHEMA)
    for stmt in _INDEXES:
        try:
            db.execute(stmt)
        except Exception:  # noqa: BLE001
            logger.exception("could not create xbrl index")


_COLS = (
    "ticker, concept, unit, period_end, period_start, fiscal_year, "
    "fiscal_period, form, val, accn, filed"
)
_BATCH = 500


def upsert_facts(db: Database, rows: list[dict]) -> int:
    """Insert facts, ignoring ones we already have (ingestion is idempotent).

    Batched into multi-row INSERTs. A company files tens of thousands of facts, and one
    round-trip per row to a database on another continent simply times out — the first
    version of this did exactly that.
    """
    if not rows:
        return 0

    n = 0
    for i in range(0, len(rows), _BATCH):
        window = rows[i : i + _BATCH]
        placeholders = ", ".join(["(" + ", ".join(["?"] * 11) + ")"] * len(window))
        sql = f"INSERT INTO xbrl_facts ({_COLS}) VALUES {placeholders} ON CONFLICT DO NOTHING"

        params: list = []
        for r in window:
            params += [
                r["ticker"], r["concept"], r["unit"], r["period_end"], r.get("period_start"),
                r.get("fiscal_year"), r.get("fiscal_period"), r.get("form"), r.get("val"),
                r["accn"], r.get("filed"),
            ]
        db.execute(sql, tuple(params))
        n += len(window)
    return n


def count(db: Database, ticker: str | None = None) -> int:
    if ticker:
        row = db.query_one(
            "SELECT count(*) AS n FROM xbrl_facts WHERE ticker = ?", (ticker.upper(),)
        )
    else:
        row = db.query_one("SELECT count(*) AS n FROM xbrl_facts")
    return int(row["n"]) if row else 0


def tickers(db: Database) -> list[str]:
    rows = db.query("SELECT DISTINCT ticker FROM xbrl_facts ORDER BY ticker")
    return [r["ticker"] for r in rows]
