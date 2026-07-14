"""Typed contracts for the insight layer (Phase 40)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskChange(BaseModel):
    """One year-over-year movement in a company's disclosed risks."""

    change: str = "new"  # "new" | "removed" | "escalated"
    topic: str = ""
    detail: str = ""
    citation_marker: str = ""


class RiskDiff(BaseModel):
    ticker: str = ""
    year_from: str = ""
    year_to: str = ""
    summary: str = ""
    changes: list[RiskChange] = Field(default_factory=list)
    available: bool = True
    message: str = ""


class RedFlag(BaseModel):
    category: str  # going_concern | restatement | litigation | material_weakness | ...
    detail: str
    severity: str = "medium"  # high | medium | low
    source_url: str = ""
    title: str = ""


class RedFlagReport(BaseModel):
    ticker: str
    flags: list[RedFlag] = Field(default_factory=list)
    scanned_sources: int = 0
    clean: bool = True


class SharedRisk(BaseModel):
    topic: str
    companies: list[str] = Field(default_factory=list)
    concentration: float = 0.0  # share of the portfolio exposed to this risk


class PortfolioOverlap(BaseModel):
    tickers: list[str] = Field(default_factory=list)
    shared_risks: list[SharedRisk] = Field(default_factory=list)
    summary: str = ""


class FundamentalPoint(BaseModel):
    period: str
    revenue: float | None = None
    net_income: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    eps: float | None = None


class Fundamentals(BaseModel):
    ticker: str
    points: list[FundamentalPoint] = Field(default_factory=list)
    source: str = ""


class PeerRow(BaseModel):
    ticker: str
    name: str = ""
    price: float | None = None
    change_pct: float | None = None
    market_cap: float | None = None
    pe: float | None = None
    revenue: float | None = None
    net_margin: float | None = None


class PeerTable(BaseModel):
    rows: list[PeerRow] = Field(default_factory=list)
