"""Analyst agent — extracts figures/ratios/trends from RETRIEVED evidence only.

Live: the provider router fills an AnalystOutput via structured JSON. Offline (or
if the whole provider chain fails): a deterministic builder regex-extracts numeric
mentions and cites the chunk they came from — so the graph always yields grounded,
cited findings and never fabricates figures not present in the evidence.
"""

from __future__ import annotations

import logging
import re

from src.agents.prompts import ANALYST_SYSTEM, format_evidence
from src.agents.schemas import AnalystOutput, Finding
from src.providers.router import ProviderRouter
from src.retrieval.types import RetrievalResult

logger = logging.getLogger(__name__)

# $391,035  |  391 billion  |  1.07  |  16.3%
_NUM_RE = re.compile(
    r"\$?\d[\d,]*(?:\.\d+)?\s?(?:billion|million|thousand|bn|mm|%)?",
    re.IGNORECASE,
)
_MAX_FINDINGS = 10


def analyze(
    router: ProviderRouter,
    query: str,
    retrieval: RetrievalResult | None,
    trace: list | None = None,
) -> AnalystOutput:
    if not retrieval or not retrieval.chunks:
        return AnalystOutput(notes="No evidence to analyze.")

    evidence = format_evidence(retrieval)
    prompt = (
        f"Question: {query}\n\nEvidence:\n{evidence}\n\n"
        "Extract the key figures, ratios, and trends relevant to the question. "
        "Cite each with the evidence marker it came from."
    )
    return router.structured(
        prompt,
        AnalystOutput,
        system=ANALYST_SYSTEM,
        stub=lambda: _stub_findings(retrieval),
        trace=trace,
    )


_SCALE_WORDS = ("billion", "million", "thousand", "bn", "mm")
_THOUSANDS_RE = re.compile(r"^\d{1,3}(,\d{3})+$")  # 391,035
_RATIO_RE = re.compile(r"^\d{1,3}\.\d+$")  # 1.07
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")  # exclude bare years


def _keep_token(token: str) -> tuple[bool, str]:
    """Decide whether a numeric token is a real figure/ratio worth reporting."""
    core = token.strip().strip(",.")
    low = token.lower()
    if "$" in token or any(w in low for w in _SCALE_WORDS):
        return True, "figure"
    if "%" in token:
        return True, "ratio"
    if _THOUSANDS_RE.match(core):  # large comma-grouped number
        return True, "figure"
    if _RATIO_RE.match(core) and not _YEAR_RE.match(core):
        return True, "ratio"
    return False, "figure"


def _stub_findings(retrieval: RetrievalResult) -> AnalystOutput:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for c in retrieval.chunks:
        text = " ".join(c.text.split())
        for m in _NUM_RE.finditer(text):
            token = m.group(0).strip().rstrip(",.")
            keep, kind = _keep_token(token)
            if not keep or (token, c.marker) in seen:
                continue
            seen.add((token, c.marker))
            label = _label_before(text, m.start(), c.metadata.section or c.metadata.ticker)
            findings.append(Finding(label=label, value=token, citation_marker=c.marker, kind=kind))
            if len(findings) >= _MAX_FINDINGS:
                return AnalystOutput(findings=findings, notes="Extracted offline (deterministic).")
    return AnalystOutput(findings=findings, notes="Extracted offline (deterministic).")


def _label_before(text: str, idx: int, fallback: str) -> str:
    prefix = text[:idx].rstrip()
    words = prefix.split()[-6:]
    label = " ".join(words).strip(" :–-")
    return label[-80:] if label else fallback
