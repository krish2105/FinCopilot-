"""Query expansion for financial retrieval (Phase 44) — deliberately conservative.

**HyDE is not used here, and that is a considered decision.** HyDE works by having the
model write a *hypothetical answer* and searching with that. On a financial benchmark
it actively hurt — Recall@5 0.544 vs 0.587 for plain retrieval — because the model
hallucinates plausible-but-wrong figures into the hypothetical document, which then
poisons the query (arXiv 2604.01733). For a product whose entire promise is "never
invent a number", injecting invented numbers into the *search itself* is the worst
possible failure mode. So we expand only in ways that cannot fabricate facts:

* **Vocabulary normalisation** — the language of filings differs from the language of
  questions. "AAPL" is written "Apple Inc."; "topline" is "revenue"; "FY24" is "fiscal
  year 2024". Purely lexical, zero risk, and it feeds the BM25/FTS leg directly — which
  matters because on financial corpora *lexical beats dense* (Recall@5 0.644 vs 0.587).
* **Step-back abstraction** (conceptual queries only) — ask the more general question
  alongside the specific one ("What drives gross margin in semiconductors?"). Retrieves
  the explanatory passages a narrow query misses.

Numeric questions get normalisation only: for those, precision is everything and
generative expansion is a liability.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# A question that turns on a figure. Generative expansion is disabled for these.
_NUMERIC_HINT = re.compile(
    r"\b(how much|how many|what was|what is|total|revenue|sales|income|profit|margin|"
    r"eps|earnings|cash|debt|assets|ratio|growth|percent|%|\$|number|amount|value)\b",
    re.IGNORECASE,
)

# Question-speak -> filing-speak. Filings never say "topline".
_SYNONYMS: dict[str, list[str]] = {
    "revenue": ["net sales", "total revenue", "revenues"],
    "topline": ["revenue", "net sales"],
    "profit": ["net income", "earnings"],
    "bottom line": ["net income"],
    "sales": ["net sales", "revenue"],
    "debt": ["long-term debt", "borrowings"],
    "cash": ["cash and cash equivalents"],
    "buyback": ["share repurchase", "repurchases of common stock"],
    "dividend": ["dividends declared", "dividends paid"],
    "headcount": ["employees", "full-time equivalent"],
    "guidance": ["outlook", "expectations"],
    "competitors": ["competition", "competitive"],
    "risks": ["risk factors"],
    "lawsuit": ["legal proceedings", "litigation"],
    "ceo": ["chief executive officer"],
    "cfo": ["chief financial officer"],
    "r&d": ["research and development"],
    "capex": ["capital expenditures", "payments for acquisition of property"],
    "fcf": ["free cash flow"],
    "margin": ["gross margin", "operating margin"],
}

_FY = re.compile(r"\bFY\s?(\d{2,4})\b", re.IGNORECASE)
_QTR = re.compile(r"\bQ([1-4])\s?(?:FY)?\s?(\d{2,4})\b", re.IGNORECASE)

_STEPBACK_SYSTEM = (
    "You turn a specific question into the broader question it depends on, so that "
    "explanatory background can be retrieved. Reply with ONE short question and "
    "nothing else. Never invent facts, figures or company names."
)


def is_numeric_query(query: str) -> bool:
    return bool(_NUMERIC_HINT.search(query))


def normalize_vocabulary(query: str) -> list[str]:
    """Filing-speak variants of the question's terms. Purely lexical — cannot fabricate."""
    low = query.lower()
    terms: list[str] = []

    for word, variants in _SYNONYMS.items():
        if word in low:
            terms.extend(variants)

    # FY24 -> "fiscal 2024" / "2024"; Q3 FY24 -> "third quarter" / "fiscal 2024"
    for m in _FY.finditer(query):
        year = m.group(1)
        year = f"20{year}" if len(year) == 2 else year
        terms += [f"fiscal {year}", year]
    for m in _QTR.finditer(query):
        q, year = m.group(1), m.group(2)
        year = f"20{year}" if len(year) == 2 else year
        ordinal = {"1": "first", "2": "second", "3": "third", "4": "fourth"}[q]
        terms += [f"{ordinal} quarter", f"fiscal {year}"]

    # de-dupe, drop anything already present
    out: list[str] = []
    for t in terms:
        if t.lower() not in low and t not in out:
            out.append(t)
    return out


def step_back(router, query: str) -> str | None:
    """The broader question behind a specific one. Conceptual queries only."""
    try:
        if getattr(router, "mode", "stub") == "stub":
            return None
        out = router.text(
            f"Question: {query}\n\nThe broader question it depends on:",
            system=_STEPBACK_SYSTEM,
            stub_text="",
        )
        out = (out or "").strip().strip('"')
        return out if 8 < len(out) < 200 else None
    except Exception as exc:  # noqa: BLE001
        logger.info("step-back expansion failed: %s", exc)
        return None


def expand(query: str, router=None) -> str:
    """The search string: the original query plus safe, non-fabricating expansions."""
    parts = [query]
    parts.extend(normalize_vocabulary(query))

    # Generative expansion only where a wrong figure can't be smuggled in.
    if router is not None and not is_numeric_query(query):
        sb = step_back(router, query)
        if sb:
            parts.append(sb)

    expanded = " ".join(parts)
    if expanded != query:
        logger.info("query expanded: %r -> %r", query, expanded[:160])
    return expanded
