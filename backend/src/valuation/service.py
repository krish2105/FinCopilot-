"""Assemble a DCF from filed data (Phase 48).

Anchors every default assumption to the company's own history: base free cash flow is
the latest filed FCF, the default stage-1 growth is its trailing FCF CAGR (clamped to a
sane band), and net cash is filed cash minus filed debt. The user can override any of
them — the point is that the starting point is real, not invented.
"""

from __future__ import annotations

import logging

from src.db.database import Database
from src.market import quotes
from src.valuation.dcf import DcfAssumptions, run_dcf, sensitivity
from src.xbrl import lookup

logger = logging.getLogger(__name__)

_MIN_GROWTH, _MAX_GROWTH = -0.05, 0.30  # keep an auto-derived CAGR believable


def _cagr(series: list[dict]) -> float | None:
    """Trailing CAGR of an XBRL series (points are newest-first)."""
    vals = [p["value"] for p in series if p.get("value")]
    if len(vals) < 2:
        return None
    end, start = vals[0], vals[-1]
    n = len(vals) - 1
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / n) - 1


def build_assumptions(db: Database, ticker: str, overrides: dict | None = None) -> DcfAssumptions | None:
    fcf_series = lookup.series(db, ticker, "operating_cash_flow", years=6)
    capex_series = {p["fiscal_year"]: p["value"] for p in lookup.series(db, ticker, "capex", years=6)}
    if not fcf_series:
        return None

    # Free cash flow = operating cash flow - capex, per year.
    fcf_points = []
    for p in fcf_series:
        capex = capex_series.get(p["fiscal_year"], 0.0)
        fcf_points.append({"fiscal_year": p["fiscal_year"], "value": p["value"] - capex})
    base_fcf = fcf_points[0]["value"]

    growth = _cagr(fcf_points)
    if growth is None:
        growth = 0.08
    growth = max(_MIN_GROWTH, min(_MAX_GROWTH, growth))

    cash = lookup.get_fact(db, ticker, "cash")
    debt = lookup.get_fact(db, ticker, "long_term_debt")
    net_cash = (cash["value"] if cash else 0.0) - (debt["value"] if debt else 0.0)

    shares = lookup.get_fact(db, ticker, "shares_diluted")
    shares_out = shares["value"] if shares else None

    a = DcfAssumptions(
        base_fcf=base_fcf,
        growth_rate=round(growth, 4),
        net_cash=net_cash,
        shares=shares_out,
    )
    for k, v in (overrides or {}).items():
        if v is not None and hasattr(a, k):
            setattr(a, k, v)
    return a


def valuation(db: Database, ticker: str, overrides: dict | None = None) -> dict | None:
    a = build_assumptions(db, ticker, overrides)
    if a is None:
        return None
    result = run_dcf(a)
    grid = sensitivity(a)

    # Compare fair value to the live market price, if we can get one.
    price = None
    upside = None
    q = quotes.get_quote(ticker)
    if q:
        price = q.get("price")
    if price and result.fair_value_per_share:
        upside = round((result.fair_value_per_share - price) / price * 100, 1)

    return {
        "ticker": ticker.upper(),
        "fair_value_per_share": result.fair_value_per_share,
        "market_price": price,
        "upside_pct": upside,
        "enterprise_value": result.enterprise_value,
        "equity_value": result.equity_value,
        "terminal_value": result.terminal_value,
        "projected_fcf": result.projected_fcf,
        "assumptions": {
            "base_fcf": a.base_fcf,
            "growth_rate": a.growth_rate,
            "terminal_growth": a.terminal_growth,
            "discount_rate": a.discount_rate,
            "years": a.years,
            "net_cash": a.net_cash,
            "shares": a.shares,
        },
        "sensitivity": grid,
        "disclaimer": "A transparent DCF calculator, not investment advice. Output depends entirely on the editable assumptions above.",
    }
