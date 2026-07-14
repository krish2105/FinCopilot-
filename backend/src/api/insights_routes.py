"""Insight API (Phase 40) — proactive findings, not answers to questions.

`/ask` tells you what you asked. These tell you what you should have asked:
  * risk-diff   — what changed in a company's risk disclosures year over year
  * red-flags   — going concern / restatement / material weakness / litigation
  * fundamentals— revenue, margins and EPS trend
  * peers       — side-by-side metrics across companies
  * portfolio   — which risks your holdings share (concentration is the real danger)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.insights import service
from src.insights.schemas import (
    Fundamentals,
    PeerTable,
    PortfolioOverlap,
    RedFlagReport,
    RiskDiff,
)
from src.providers.router import ProviderRouter
from src.retrieval.graph import EntityGraph, graph_path
from src.retrieval.retriever import get_retriever

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/risk-diff/{ticker}", response_model=RiskDiff)
def risk_diff(ticker: str) -> RiskDiff:
    """What changed in this company's risk factors since the previous annual report."""
    return service.risk_diff(get_retriever(), ProviderRouter(get_settings()), ticker)


@router.get("/red-flags/{ticker}", response_model=RedFlagReport)
def red_flags(ticker: str) -> RedFlagReport:
    return service.red_flags(get_retriever(), ticker)


@router.get("/fundamentals/{ticker}", response_model=Fundamentals)
def fundamentals(ticker: str) -> Fundamentals:
    f = service.fundamentals(ticker)
    if not f.points:
        raise HTTPException(
            status_code=404,
            detail=f"No fundamentals available for {ticker.upper()} (needs FMP_API_KEY).",
        )
    return f


@router.get("/peers", response_model=PeerTable)
def peers(tickers: str = Query(..., description="Comma-separated, e.g. AAPL,MSFT,NVDA")) -> PeerTable:
    syms = [t.strip().upper() for t in tickers.split(",") if t.strip()][:8]
    if not syms:
        raise HTTPException(status_code=400, detail="Provide at least one ticker.")
    return service.peer_table(syms)


class PortfolioRequest(BaseModel):
    tickers: list[str] = Field(default_factory=list, max_length=20)


@router.post("/portfolio", response_model=PortfolioOverlap)
def portfolio(body: PortfolioRequest) -> PortfolioOverlap:
    """Shared-risk concentration across holdings — the danger a price chart can't show."""
    graph = EntityGraph.load(graph_path())
    return service.portfolio_overlap(graph, body.tickers)
