"""Turn an exact XBRL fact into a citable piece of evidence (Phase 45).

Rather than bolting a second answer path onto the orchestrator, a matched fact is
injected as the *top-ranked chunk* of the normal retrieval result. Everything
downstream then works unchanged — the Analyst reads it, the Compliance agent sees it,
citations are assigned to it, and, crucially, the faithfulness gate's numeric
guardrail finds the figure present in the evidence and stops treating it as
ungrounded.

The effect is that the model no longer has to *recover* a number from a table it half
understands. The number is handed to it, typed, period-aligned, and carrying the
accession number of the filing it was reported in.
"""

from __future__ import annotations

import logging

from src.db.database import get_db
from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.types import RetrievedChunk
from src.xbrl import lookup
from src.xbrl.client import cik_for

logger = logging.getLogger(__name__)

_LABELS = {
    "revenue": "Revenue",
    "net_income": "Net income",
    "gross_profit": "Gross profit",
    "operating_income": "Operating income",
    "gross_margin_pct": "Gross margin",
    "operating_margin_pct": "Operating margin",
    "net_margin_pct": "Net margin",
    "free_cash_flow": "Free cash flow",
    "rnd_expense": "Research and development expense",
    "capex": "Capital expenditures",
    "operating_cash_flow": "Net cash provided by operating activities",
    "eps_diluted": "Diluted earnings per share",
    "cash": "Cash and cash equivalents",
    "assets": "Total assets",
    "liabilities": "Total liabilities",
    "equity": "Stockholders' equity",
    "long_term_debt": "Long-term debt",
}


def _format(value: float, unit: str) -> str:
    if unit == "percent":
        return f"{value:.2f}%"
    if unit == "USD/shares":
        return f"${value:,.2f} per share"
    if unit == "shares":
        return f"{value:,.0f} shares"
    return f"${value:,.0f}"


def fact_chunk(query: str, tickers: list[str] | None) -> RetrievedChunk | None:
    """A top-ranked evidence chunk carrying the exact filed figure, or None."""
    try:
        fact = lookup.answer_numeric(get_db(), query, tickers)
    except Exception as exc:  # noqa: BLE001
        logger.info("xbrl lookup skipped: %s", exc)
        return None
    if not fact:
        return None

    ticker = fact["ticker"]
    label = _LABELS.get(fact["metric"], fact["metric"].replace("_", " "))
    value = _format(fact["value"], fact["unit"])
    fy = fact.get("fiscal_year")
    accn = fact.get("accn") or ""

    text = (
        f"{ticker} — {label} for fiscal year {fy} (period ended {fact['period_end']}) "
        f"was {value}, as reported in the company's {fact.get('form') or '10-K'} "
        f"filed with the SEC (accession {accn})."
    )
    if fact.get("components"):
        parts = ", ".join(f"{k} = ${v:,.0f}" for k, v in fact["components"].items())
        text += f" Computed from filed values: {parts}."

    md = SourceMetadata(
        ticker=ticker,
        doc_type=DocType.TEN_K,
        title=f"{ticker} {fact.get('form') or '10-K'} — XBRL (SEC)",
        source_url=lookup.source_url(cik_for(ticker), accn),
        filing_date=fact.get("filed"),
        section=f"XBRL · {fact.get('concept', label)}",
    )
    return RetrievedChunk(
        chunk_id=f"xbrl:{ticker}:{fact['metric']}:{fact['period_end']}",
        text=text,
        metadata=md,
        rrf_score=1.0,
        # Outrank anything the reranker can produce: this is the filed number itself,
        # not a passage that might mention it.
        rerank_score=99.0,
    )
