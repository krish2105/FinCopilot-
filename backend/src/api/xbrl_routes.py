"""XBRL API (Phase 45) — exact filed figures, free of any vendor quota.

Everything here comes from SEC XBRL: no API key, no daily cap, and each value is
citable back to the accession number it was filed under. This is what replaces a
250-calls-a-day vendor tier for fundamentals.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.db.database import get_db
from src.xbrl import lookup, store
from src.xbrl.concepts import ALIASES, DERIVED, METRICS

router = APIRouter(prefix="/xbrl", tags=["xbrl"])


@router.get("/metrics")
def metrics() -> dict:
    """Everything we can answer exactly."""
    return {
        "metrics": sorted(set(METRICS) | set(DERIVED)),
        "aliases": sorted(ALIASES),
    }


@router.get("/stats")
def stats() -> dict:
    db = get_db()
    return {"facts": store.count(db), "tickers": store.tickers(db)}


@router.get("/fact/{ticker}/{metric}")
def fact(ticker: str, metric: str, fiscal_year: int | None = None) -> dict:
    db = get_db()
    f = (
        lookup.derived(db, ticker, metric, fiscal_year)
        if metric in DERIVED
        else lookup.get_fact(db, ticker, metric, fiscal_year)
    )
    if not f:
        raise HTTPException(
            status_code=404,
            detail=f"No filed value for {metric} / {ticker.upper()}"
            + (f" FY{fiscal_year}" if fiscal_year else ""),
        )
    return f


@router.get("/series/{ticker}/{metric}")
def series(ticker: str, metric: str, years: int = Query(5, ge=1, le=15)) -> dict:
    points = lookup.series(get_db(), ticker, metric, years=years)
    if not points:
        raise HTTPException(status_code=404, detail=f"No series for {metric} / {ticker.upper()}")
    return {"ticker": ticker.upper(), "metric": metric, "points": points}
