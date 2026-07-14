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


@router.get("/income-flow/{ticker}")
def income_flow(ticker: str) -> dict:
    """Income-statement flows for a Sankey diagram: revenue → costs → profit.

    The most legible financial visual there is — the whole income statement in one
    picture, every value a filed figure.
    """
    db = get_db()

    def val(metric: str) -> float | None:
        f = lookup.get_fact(db, ticker, metric)
        return f["value"] if f else None

    revenue = val("revenue")
    if not revenue:
        raise HTTPException(status_code=404, detail=f"No revenue filed for {ticker.upper()}.")

    cogs = val("cost_of_revenue")
    gross = val("gross_profit")
    if gross is None and cogs is not None:
        gross = revenue - cogs
    op_income = val("operating_income")
    net_income = val("net_income")
    rnd = val("rnd_expense")
    sga = val("sga_expense")

    # Build only the links we can actually ground in filed numbers.
    links: list[dict] = []
    if cogs is not None and gross is not None:
        links.append({"source": "Revenue", "target": "Cost of revenue", "value": round(cogs)})
        links.append({"source": "Revenue", "target": "Gross profit", "value": round(gross)})
    if gross is not None and op_income is not None:
        opex = gross - op_income
        if rnd:
            links.append({"source": "Gross profit", "target": "R&D", "value": round(rnd)})
        if sga:
            links.append({"source": "Gross profit", "target": "SG&A", "value": round(sga)})
        other_opex = opex - (rnd or 0) - (sga or 0)
        if other_opex > 0:
            links.append({"source": "Gross profit", "target": "Other opex", "value": round(other_opex)})
        links.append({"source": "Gross profit", "target": "Operating income", "value": round(op_income)})
    if op_income is not None and net_income is not None:
        below = op_income - net_income
        if below > 0:
            links.append({"source": "Operating income", "target": "Tax & other", "value": round(below)})
        links.append({"source": "Operating income", "target": "Net income", "value": round(net_income)})

    if not links:
        raise HTTPException(status_code=404, detail=f"Not enough filed detail to chart {ticker.upper()}.")

    return {
        "ticker": ticker.upper(),
        "revenue": revenue,
        "net_income": net_income,
        "links": links,
    }
