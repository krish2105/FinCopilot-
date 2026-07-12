"""Live market-data API (Phase 25): quotes, price history, earnings.

yfinance-backed, free, no key. These endpoints are **database-independent** so the
retail dashboard renders live prices and charts even before the RAG corpus is
seeded. Public market data only — unauthenticated by design.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.market import quotes

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote/{ticker}")
def quote(ticker: str) -> dict:
    q = quotes.get_quote(ticker)
    if q is None:
        raise HTTPException(status_code=404, detail=f"No live quote available for {ticker}")
    return q


@router.get("/history/{ticker}")
def history(ticker: str, range: str = Query("1Y")) -> dict:
    if range.upper() not in quotes.RANGE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"range must be one of {sorted(quotes.RANGE_MAP)}",
        )
    h = quotes.get_history(ticker, range)
    if h is None:
        raise HTTPException(status_code=404, detail=f"No price history available for {ticker}")
    return h


@router.get("/earnings/{ticker}")
def earnings(ticker: str) -> dict:
    e = quotes.get_earnings(ticker)
    if e is None:
        raise HTTPException(status_code=404, detail=f"No earnings data available for {ticker}")
    return e
