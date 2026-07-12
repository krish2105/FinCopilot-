"""Citation assignment and extractive cited-answer formatting.

Phase 2 produces an *extractive* cited answer: the top reranked evidence stitched
together, each snippet followed by its citation marker. This proves the
retrieval → citation contract end-to-end. Phase 3 swaps the extractive step for
LLM synthesis over these same cited chunks (the citations stay identical).
"""

from __future__ import annotations

import re

from src.retrieval.types import Citation, RetrievedChunk

_EXCERPT_CHARS = 240
_ANSWER_SNIPPETS = 3
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _excerpt(text: str, limit: int = _EXCERPT_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def assign_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Number chunks in rank order and build their Citation records in place."""
    citations: list[Citation] = []
    for i, c in enumerate(chunks, start=1):
        marker = f"[{i}]"
        c.marker = marker
        m = c.metadata
        citations.append(
            Citation(
                marker=marker,
                ticker=m.ticker,
                doc_type=str(m.doc_type),
                title=m.title,
                page=m.page,
                section=m.section,
                source_url=m.source_url,
                excerpt=_excerpt(c.text),
            )
        )
    return citations


def build_extractive_answer(query: str, chunks: list[RetrievedChunk]) -> str:
    """Stitch the most relevant sentences from the top chunks, each cited.

    No LLM: we pick the highest-overlap sentence from each of the top chunks so
    the 'answer' is grounded verbatim in the sources and traceably cited.
    """
    if not chunks:
        return (
            "Insufficient evidence: no relevant sources were retrieved for this "
            "query. (Extractive answer; LLM synthesis arrives in Phase 3.)"
        )
    q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    lines: list[str] = []
    for c in chunks[:_ANSWER_SNIPPETS]:
        sentence = _best_sentence(q_tokens, c.text)
        lines.append(f"{sentence} {c.marker}")
    return " ".join(lines)


def _best_sentence(q_tokens: set[str], text: str) -> str:
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return _excerpt(text)
    if not q_tokens:
        return _excerpt(sentences[0])

    def overlap(s: str) -> int:
        toks = set(re.findall(r"[a-z0-9]+", s.lower()))
        return len(toks & q_tokens)

    best = max(sentences, key=overlap)
    return _excerpt(best)
