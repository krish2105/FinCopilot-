"""Compliance agent — flags risk language and validates the Analyst's claims.

Deliberately rule-based (not LLM): compliance flags must be reliable and
non-hallucinated, so we pattern-match well-known risk/going-concern/restatement
language over the retrieved evidence and check that every analyst finding cites a
real marker. The agent can veto to the refusal path by setting
verdict="insufficient_evidence".
"""

from __future__ import annotations

import logging
import re

from src.agents.schemas import AnalystOutput, ComplianceFlag, ComplianceOutput
from src.retrieval.types import RetrievalResult

logger = logging.getLogger(__name__)

# category -> regex of trigger phrases
_PATTERNS: dict[str, re.Pattern] = {
    "going_concern": re.compile(r"going concern", re.IGNORECASE),
    "restatement": re.compile(r"restate(?:d|ment)?", re.IGNORECASE),
    "material_weakness": re.compile(r"material weakness", re.IGNORECASE),
    "litigation": re.compile(r"litigation|lawsuit|legal proceeding", re.IGNORECASE),
    "impairment": re.compile(r"impairment", re.IGNORECASE),
    "risk_factors": re.compile(r"risk factors", re.IGNORECASE),
}


def check(retrieval: RetrievalResult | None, analyst: AnalystOutput | None) -> ComplianceOutput:
    if not retrieval or not retrieval.chunks:
        return ComplianceOutput(
            verdict="insufficient_evidence",
            reason="No supporting evidence was retrieved for this query.",
        )

    flags: list[ComplianceFlag] = []
    for c in retrieval.chunks:
        text = " ".join(c.text.split())
        for category, pat in _PATTERNS.items():
            m = pat.search(text)
            if m:
                snippet = _around(text, m.start(), m.end())
                flags.append(
                    ComplianceFlag(category=category, detail=snippet, citation_marker=c.marker)
                )

    # Validate that analyst findings reference real citation markers.
    valid_markers = {c.marker for c in retrieval.chunks}
    uncited = []
    if analyst:
        for f in analyst.findings:
            if f.citation_marker not in valid_markers:
                uncited.append(f.label)

    reason = ""
    if uncited:
        reason = f"{len(uncited)} finding(s) lacked a valid citation and were flagged."

    return ComplianceOutput(
        verdict="ok",
        flags=_dedupe(flags),
        reason=reason,
        uncited_findings=uncited,
    )


def _around(text: str, start: int, end: int, window: int = 90) -> str:
    a = max(0, start - window)
    b = min(len(text), end + window)
    return ("…" if a > 0 else "") + text[a:b] + ("…" if b < len(text) else "")


def _dedupe(flags: list[ComplianceFlag]) -> list[ComplianceFlag]:
    seen: set[tuple[str, str]] = set()
    out: list[ComplianceFlag] = []
    for f in flags:
        key = (f.category, f.citation_marker)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out
