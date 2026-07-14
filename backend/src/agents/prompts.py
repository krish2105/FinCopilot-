"""System prompts and evidence formatting shared by the agents."""

from __future__ import annotations

from src.retrieval.types import RetrievalResult

ANALYST_SYSTEM = (
    "You are a meticulous financial analyst. Extract only figures, ratios, and "
    "trends that are explicitly present in the provided evidence. For every "
    "finding you MUST set citation_marker to the bracketed marker (e.g. [2]) of "
    "the evidence chunk it came from. Never invent numbers. If a figure is not in "
    "the evidence, do not include it."
)

SYNTHESIS_SYSTEM = (
    "You are FinCopilot, a financial research assistant. Answer the user's "
    "question using ONLY the provided evidence. Cite every factual claim with the "
    "bracketed marker(s) (e.g. [1], [3]) of the supporting evidence. If the "
    "evidence is insufficient to answer, say so plainly and state what is missing. "
    "Do not give investment advice. Be concise and precise with numbers."
)


def order_for_context(chunks: list) -> list:
    """Strongest evidence at the START and END of the prompt.

    Attention is U-shaped: models reliably use the beginning and the end of a context
    window and skim the middle ("lost in the middle"), with accuracy dropping 30-50%
    for facts buried mid-context. Chunks arrive best-first, so we deal them
    alternately to the front and the back — rank 1 leads, rank 2 closes, and the
    weakest evidence ends up in the middle where it does the least harm.

    Citation markers are already assigned, so re-ordering the presentation costs
    nothing and changes no output contract.
    """
    if len(chunks) <= 2:
        return chunks
    head, tail = [], []
    for i, c in enumerate(chunks):
        (head if i % 2 == 0 else tail).append(c)
    return head + tail[::-1]


def format_evidence(retrieval: RetrievalResult | None, max_chars: int = 900) -> str:
    if not retrieval or not retrieval.chunks:
        return "(no evidence retrieved)"
    lines = []
    for c in order_for_context(list(retrieval.chunks)):
        m = c.metadata
        loc = f"{m.ticker} {m.doc_type}"
        if m.page is not None:
            loc += f" p.{m.page}"
        if m.section:
            loc += f" · {m.section}"
        text = " ".join(c.text.split())[:max_chars]
        lines.append(f"{c.marker} ({loc}) {text}")
    return "\n\n".join(lines)


def format_findings(findings) -> str:
    if not findings:
        return "(no findings)"
    return "\n".join(f"- {f.label}: {f.value} {f.citation_marker}".rstrip() for f in findings)
