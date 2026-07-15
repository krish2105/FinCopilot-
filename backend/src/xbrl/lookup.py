"""Exact numeric lookup over XBRL facts (Phase 45).

This is the piece that lets the product stop guessing at numbers. A figure returned
here is not "the model's best reading of a retrieved table" — it is the value the
company filed with the SEC, tied to the accession number it was filed under, so the
answer can cite the filing it came from and the faithfulness gate has a ground truth
to check the model against.

Concept fallback chains matter: companies re-tag the same idea over time (Apple's
revenue moved to `RevenueFromContractWithCustomerExcludingAssessedTax` under ASC 606),
so we try each concept in order and take the first with data.
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.database import Database
from src.xbrl.concepts import DERIVED, METRICS, match_metric

logger = logging.getLogger(__name__)

_EDGAR_FILING = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}"
_ACCN_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{accn}-index.htm"


def source_url(cik: int | None, accn: str) -> str:
    if not cik or not accn:
        return ""
    return _ACCN_URL.format(cik=cik, accn_nodash=accn.replace("-", ""), accn=accn)


def _annual_points(db: Database, ticker: str, concept: str) -> list[dict[str, Any]]:
    """Annual values of one concept, one per period, newest period first.

    Two traps here, both of which silently produce *confidently wrong numbers*:

    1. **`fy` is the fiscal year of the FILING, not of the fact.** Apple's FY2025 10-K
       restates FY2024 and FY2023, and every one of those rows carries `fy=2025`.
       Grouping on it mislabels history — a 5-year revenue chart came out shifted by
       two years. The real period is `period_end`, so that is what we key on.
    2. **A 10-K also contains quarterly facts.** For duration concepts (revenue,
       income) we keep only spans of roughly a year; instant concepts (cash, assets)
       have no start date and are kept as-is.

    Among restatements of the same period, the most recently *filed* value wins — that
    is the corrected one.
    """
    rows = db.query(
        "SELECT * FROM xbrl_facts WHERE ticker = ? AND concept = ? AND form = ?",
        (ticker.upper(), concept, "10-K"),
    )

    best: dict[str, dict] = {}  # period_end -> most recently filed row
    for r in rows:
        if r.get("val") is None or not r.get("period_end"):
            continue
        start, end = r.get("period_start"), r["period_end"]
        if start:  # duration fact — must span ~a year, else it's a quarter
            days = (_date(end) - _date(start)).days
            if not (300 <= days <= 400):
                continue
        prev = best.get(end)
        if prev is None or (r.get("filed") or "") > (prev.get("filed") or ""):
            best[end] = r

    points = [
        {
            "fiscal_year": int(end[:4]),  # from the PERIOD, never from the filing's `fy`
            "period_end": end,
            "value": float(r["val"]),
            "unit": r["unit"],
            "form": r.get("form"),
            "filed": r.get("filed"),
            "accn": r.get("accn"),
            "concept": concept,
        }
        for end, r in best.items()
    ]
    points.sort(key=lambda p: p["period_end"], reverse=True)
    return points


def _date(s: str):
    from datetime import date

    return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))


def _metric_points(db: Database, ticker: str, metric: str) -> list[dict[str, Any]]:
    """All annual points for a metric, merged across its whole concept chain.

    Taking the *first concept that has any data* is wrong: companies abandon tags. NVDA
    still has rows under an old revenue concept, so a first-match lookup happily
    returned FY2022 revenue as the latest figure — off by ~$100bn. Merging every
    concept in the chain by period, with earlier (preferred) concepts winning ties,
    keeps the tag preference *and* always finds the newest period anyone reported.
    """
    merged: dict[str, dict] = {}
    for concept in METRICS.get(metric, []):
        for p in _annual_points(db, ticker, concept):
            merged.setdefault(p["period_end"], p)  # first concept in the chain wins
    points = list(merged.values())
    points.sort(key=lambda p: p["period_end"], reverse=True)
    return points


def get_fact(
    db: Database,
    ticker: str,
    metric: str,
    fiscal_year: int | None = None,
    annual_only: bool = True,
) -> dict[str, Any] | None:
    """One metric for one company. `fiscal_year=None` -> the most recent annual figure."""
    points = _metric_points(db, ticker, metric)
    if fiscal_year is not None:
        points = [p for p in points if p["fiscal_year"] == fiscal_year]
    if not points:
        return None
    return {"ticker": ticker.upper(), "metric": metric, **points[0]}


def series(
    db: Database, ticker: str, metric: str, years: int = 5, annual_only: bool = True
) -> list[dict[str, Any]]:
    """A metric over time — one point per fiscal year, newest first."""
    return _metric_points(db, ticker, metric)[:years]


def derived(db: Database, ticker: str, metric: str, fiscal_year: int | None = None) -> dict | None:
    """Margins and free cash flow — computed from facts, never estimated by a model."""
    spec = DERIVED.get(metric)
    if not spec:
        return None
    a_key, b_key = spec
    a = get_fact(db, ticker, a_key, fiscal_year)
    b = get_fact(db, ticker, b_key, fiscal_year)
    if not a or not b or not b["value"]:
        return None

    if metric == "free_cash_flow":
        value, unit = a["value"] - b["value"], a["unit"]
    else:
        value, unit = a["value"] / b["value"] * 100.0, "percent"

    return {
        "ticker": ticker.upper(),
        "metric": metric,
        "value": round(value, 2),
        "unit": unit,
        "fiscal_year": a.get("fiscal_year"),
        "period_end": a["period_end"],
        "components": {a_key: a["value"], b_key: b["value"]},
        "accn": a.get("accn"),
    }


def answer_numeric(db: Database, query: str, tickers: list[str] | None) -> dict | None:
    """If a question is asking for a figure we hold, answer it exactly.

    Returns None when the question isn't a plain metric lookup, so the caller falls
    back to normal retrieval. Deliberately conservative: it would rather decline than
    answer the wrong question confidently.
    """
    # The UI often sends no ticker filter (the user just types "Apple's revenue"), so
    # resolve the company from the query text before giving up — otherwise every plain-
    # English numeric question skips the exact-figure path and the model refuses.
    if not tickers:
        resolved = _ticker_in_query(query)
        if not resolved:
            return None
        tickers = [resolved]
    metric = match_metric(query)
    if not metric:
        return None

    fy = _fiscal_year_in(query)
    ticker = tickers[0]

    # Derived metrics (margins, FCF) are computed from facts — check those first, or a
    # "margin" question gets answered with a dollar amount.
    fact = (
        derived(db, ticker, metric, fiscal_year=fy)
        if metric in DERIVED
        else get_fact(db, ticker, metric, fiscal_year=fy)
    )
    if not fact:
        return None
    logger.info("xbrl: answered %r from filed facts (%s)", query[:60], fact.get("accn"))
    return fact


# Plain-English company names -> ticker, so "Apple's revenue" resolves even with no
# ticker filter. Covers the ingested universe; extend as the corpus grows.
_NAME_TO_TICKER: dict[str, str] = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "johnson & johnson": "JNJ",
    "johnson and johnson": "JNJ",
    "j&j": "JNJ",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "j.p. morgan": "JPM",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "visa": "V",
}


def _ticker_in_query(query: str) -> str | None:
    """Resolve a ticker from the query: an explicit known symbol, else a company name."""
    import re

    from src.config.settings import get_settings

    known = {t.upper() for t in get_settings().tickers}
    for sym in re.findall(r"\b[A-Za-z]{1,5}\b", query):
        up = sym.upper()
        if up in known and up not in {"A", "I"}:  # avoid pronouns/articles as tickers
            return up
    q = query.lower()
    # Longest names first so "johnson & johnson" wins over a bare "johnson".
    for name in sorted(_NAME_TO_TICKER, key=len, reverse=True):
        if name in q and _NAME_TO_TICKER[name] in known:
            return _NAME_TO_TICKER[name]
    return None


def _fiscal_year_in(query: str) -> int | None:
    import re

    m = re.search(r"\b(?:FY\s?)?(20\d{2})\b", query, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\bFY\s?(\d{2})\b", query, re.IGNORECASE)
    return 2000 + int(m.group(1)) if m else None
