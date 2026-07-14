"""Insight generation (Phase 40).

Each function turns the corpus we already have into something the user never thought
to ask for. All of them degrade gracefully: if the evidence isn't there, they say so
rather than inventing a finding — the same contract as the rest of the product.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from src.agents.compliance import check as compliance_check
from src.insights.schemas import (
    FundamentalPoint,
    Fundamentals,
    PeerRow,
    PeerTable,
    PortfolioOverlap,
    RedFlag,
    RedFlagReport,
    RiskDiff,
    SharedRisk,
)
from src.market import quotes
from src.providers.router import ProviderRouter
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

_RISK_SECTION_HINT = "risk factor"

# Severity by how directly the flag threatens the business.
_SEVERITY = {
    "going_concern": "high",
    "material_weakness": "high",
    "restatement": "high",
    "litigation": "medium",
}

_DIFF_SYSTEM = (
    "You compare a company's risk-factor disclosures between two annual reports. "
    "Report only genuine movements: risks that are NEW in the later filing, risks "
    "that were DROPPED, and risks whose language ESCALATED (more specific, more "
    "severe, or newly quantified). Ignore boilerplate rewording. Ground every item "
    "in the supplied text; if nothing meaningfully changed, say so."
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _risk_chunks_by_year(retriever: Retriever, ticker: str) -> dict[str, list]:
    """Risk-factor chunks for a ticker, grouped by filing year (newest first)."""
    by_year: dict[str, list] = defaultdict(list)
    for chunk in retriever.store.iter_all():
        md = chunk.metadata
        if md.ticker.upper() != ticker.upper():
            continue
        if _RISK_SECTION_HINT not in (md.section or "").lower():
            continue
        year = (md.filing_date or "")[:4]
        if year:
            by_year[year].append(chunk)
    return dict(sorted(by_year.items(), reverse=True))


def _joined(chunks: list, limit: int = 12) -> str:
    return "\n\n".join(" ".join(c.text.split())[:900] for c in chunks[:limit])


# --------------------------------------------------------------------------- #
# 40a — Risk Diff (year over year)
# --------------------------------------------------------------------------- #
def risk_diff(retriever: Retriever, router: ProviderRouter, ticker: str) -> RiskDiff:
    """What changed in this company's disclosed risks since the previous annual report."""
    by_year = _risk_chunks_by_year(retriever, ticker)
    years = list(by_year)
    if len(years) < 2:
        return RiskDiff(
            ticker=ticker.upper(),
            available=False,
            message=(
                "Need risk factors from two annual reports to diff. "
                f"Found {len(years)} year(s) for {ticker.upper()}."
            ),
        )

    newer, older = years[0], years[1]
    prompt = (
        f"Company: {ticker.upper()}\n\n"
        f"=== RISK FACTORS — {older} ===\n{_joined(by_year[older])}\n\n"
        f"=== RISK FACTORS — {newer} ===\n{_joined(by_year[newer])}\n\n"
        f"What changed between {older} and {newer}?"
    )
    out = router.structured(
        prompt,
        RiskDiff,
        system=_DIFF_SYSTEM,
        stub=lambda: RiskDiff(
            ticker=ticker.upper(),
            year_from=older,
            year_to=newer,
            summary="Offline mode: a live LLM is required to compare disclosures.",
        ),
    )
    out.ticker = ticker.upper()
    out.year_from, out.year_to = older, newer
    out.available = True
    return out


# --------------------------------------------------------------------------- #
# 40b — Red-flag scanner
# --------------------------------------------------------------------------- #
def red_flags(retriever: Retriever, ticker: str) -> RedFlagReport:
    """Surface going-concern / restatement / material-weakness / litigation language.

    The Compliance agent already detects these on every query — this simply asks it
    the question proactively instead of waiting for the user to.
    """
    probe = (
        "going concern substantial doubt restatement material weakness in internal "
        "control litigation legal proceedings investigation"
    )
    retrieval = retriever.retrieve(probe, top_k=10, candidate_k=40, tickers=[ticker.upper()])
    result = compliance_check(retrieval, None)

    by_marker = {c.marker: c for c in retrieval.citations}
    flags: list[RedFlag] = []
    for f in result.flags:
        cite = by_marker.get(f.citation_marker)
        flags.append(
            RedFlag(
                category=f.category,
                detail=f.detail,
                severity=_SEVERITY.get(f.category, "medium"),
                source_url=cite.source_url if cite else "",
                title=cite.title if cite else "",
            )
        )
    return RedFlagReport(
        ticker=ticker.upper(),
        flags=flags,
        scanned_sources=len(retrieval.chunks),
        clean=not flags,
    )


# --------------------------------------------------------------------------- #
# 40d — Portfolio risk overlap
# --------------------------------------------------------------------------- #
def portfolio_overlap(graph, tickers: list[str]) -> PortfolioOverlap:
    """Which risks do these holdings share? Concentration is the real portfolio danger."""
    tickers = [t.upper() for t in tickers if t.strip()]
    if not graph or len(tickers) < 2:
        return PortfolioOverlap(
            tickers=tickers,
            summary="Add at least two holdings to see shared-risk concentration.",
        )

    exposure: dict[str, list[str]] = defaultdict(list)
    for t in tickers:
        for topic in graph.risks_for_company(t):
            exposure[topic].append(t)

    shared = [
        SharedRisk(topic=topic, companies=sorted(cos), concentration=len(cos) / len(tickers))
        for topic, cos in exposure.items()
        if len(cos) >= 2
    ]
    shared.sort(key=lambda s: (-s.concentration, s.topic))

    if shared:
        top = shared[0]
        summary = (
            f"{len(top.companies)} of your {len(tickers)} holdings "
            f"({', '.join(top.companies)}) disclose {top.topic} risk — "
            f"{top.concentration:.0%} of the portfolio is exposed to it."
        )
    else:
        summary = "No risk topic is shared across these holdings in the ingested filings."
    return PortfolioOverlap(tickers=tickers, shared_risks=shared, summary=summary)


# --------------------------------------------------------------------------- #
# 40c — Fundamentals + peer benchmarking
# --------------------------------------------------------------------------- #
def fundamentals(ticker: str) -> Fundamentals:
    """Revenue / margins / EPS by year — from SEC XBRL first.

    XBRL is free, keyless and uncapped, so fundamentals no longer burn a 250-calls-a-day
    vendor allowance, and the figures are the ones the company actually filed rather
    than a vendor's normalisation of them. FMP stays as a fallback for anything the SEC
    doesn't cover (e.g. non-US filers).
    """
    from src.db.database import get_db
    from src.xbrl import lookup as xl

    db = get_db()
    try:
        revenue = {p["fiscal_year"]: p for p in xl.series(db, ticker, "revenue", years=6)}
    except Exception as exc:  # noqa: BLE001 — no xbrl_facts table yet, or DB unavailable
        logger.info("xbrl fundamentals unavailable (%s); falling back to the vendor feed", exc)
        revenue = {}
    if revenue:
        net = {p["fiscal_year"]: p["value"] for p in xl.series(db, ticker, "net_income", years=6)}
        gross = {p["fiscal_year"]: p["value"] for p in xl.series(db, ticker, "gross_profit", years=6)}
        eps = {p["fiscal_year"]: p["value"] for p in xl.series(db, ticker, "eps_diluted", years=6)}

        points = []
        for fy in sorted(revenue, reverse=True):
            rev = revenue[fy]["value"]
            ni, gp = net.get(fy), gross.get(fy)
            points.append(
                FundamentalPoint(
                    period=str(fy),
                    revenue=rev,
                    net_income=ni,
                    gross_margin=round(gp / rev * 100, 2) if rev and gp is not None else None,
                    net_margin=round(ni / rev * 100, 2) if rev and ni is not None else None,
                    eps=eps.get(fy),
                )
            )
        return Fundamentals(ticker=ticker.upper(), points=points, source="sec-xbrl")

    f = quotes.get_fundamentals(ticker)  # fallback: non-US filers, etc.
    if not f:
        return Fundamentals(ticker=ticker.upper(), points=[], source="")
    return Fundamentals(**f)


def peer_table(tickers: list[str]) -> PeerTable:
    rows: list[PeerRow] = []
    for t in tickers:
        q = quotes.get_quote(t) or {}
        f = quotes.get_fundamentals(t) or {}
        latest = (f.get("points") or [{}])[0] if f.get("points") else {}
        rows.append(
            PeerRow(
                ticker=t.upper(),
                name=q.get("name", t.upper()),
                price=q.get("price"),
                change_pct=q.get("change_pct"),
                market_cap=q.get("market_cap"),
                pe=q.get("pe"),
                revenue=latest.get("revenue"),
                net_margin=latest.get("net_margin"),
            )
        )
    return PeerTable(rows=rows)
