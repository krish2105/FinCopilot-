"""Load SEC XBRL facts into the store (Phase 45).

Only the concepts we actually answer from — a companyfacts payload carries ~500
concepts and most are noise. Idempotent: re-running inserts nothing new, so this is
safe on a schedule.

Run:  python -m src.xbrl.ingest --tickers AAPL MSFT NVDA
"""

from __future__ import annotations

import argparse
import logging

from src.db.database import get_db
from src.xbrl import store
from src.xbrl.client import company_facts
from src.xbrl.concepts import METRICS

logger = logging.getLogger(__name__)

# Flatten every concept in every fallback chain — that's what we keep.
_WANTED: set[str] = {c for chain in METRICS.values() for c in chain}


def facts_for(ticker: str) -> list[dict]:
    payload = company_facts(ticker)
    if not payload:
        return []

    rows: list[dict] = []
    for taxonomy in ("us-gaap", "ifrs-full"):
        concepts = payload.get("facts", {}).get(taxonomy, {})
        for concept, body in concepts.items():
            if concept not in _WANTED:
                continue
            for unit, entries in body.get("units", {}).items():
                for e in entries:
                    if e.get("val") is None or not e.get("end") or not e.get("accn"):
                        continue
                    rows.append(
                        {
                            "ticker": ticker.upper(),
                            "concept": concept,
                            "unit": unit,
                            "period_end": e["end"],
                            "period_start": e.get("start"),
                            "fiscal_year": e.get("fy"),
                            "fiscal_period": e.get("fp"),
                            "form": e.get("form"),
                            "val": float(e["val"]),
                            "accn": e["accn"],
                            "filed": e.get("filed"),
                        }
                    )
    return rows


def ingest(tickers: list[str]) -> dict:
    db = get_db()
    store.init_schema(db)

    stats: dict[str, int] = {}
    for t in tickers:
        rows = facts_for(t)
        store.upsert_facts(db, rows)
        stats[t.upper()] = len(rows)
        logger.info("xbrl: %s -> %d facts", t.upper(), len(rows))

    total = store.count(db)
    return {"per_ticker": stats, "total_facts_in_store": total}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Ingest SEC XBRL facts.")
    ap.add_argument("--tickers", nargs="+", required=True)
    args = ap.parse_args()

    import json

    print(json.dumps(ingest(args.tickers), indent=2))


if __name__ == "__main__":
    main()
