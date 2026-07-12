"""Contextual Retrieval (Phase 26) — Anthropic's technique.

Isolated chunks from a 10-K lose *which company / period / section* they belong
to, which cripples both dense and lexical retrieval. We fix that by prepending a
short, self-describing context string to each chunk **before embedding and BM25
indexing** (the user-facing citation excerpt stays the original text).

Two ways to build the context blurb:

- ``template_context`` — deterministic, keyless, offline. Derived purely from the
  chunk's own metadata (ticker, doc type, title, section, date). Runs everywhere,
  including CI and the free-tier path. This is the default.
- ``llm_context`` — an LLM-written 1-sentence situating blurb (the full Anthropic
  method). Higher quality but needs an API key. Provided as a drop-in helper to
  wire into ingestion once a key is set; falls back to the template on any error.

Reference: https://www.anthropic.com/engineering/contextual-retrieval
"""

from __future__ import annotations

import logging

from src.ingestion.models import SourceMetadata

logger = logging.getLogger(__name__)

_DOCTYPE_LABEL: dict[str, str] = {
    "10-K": "annual report (10-K)",
    "10-Q": "quarterly report (10-Q)",
    "8-K": "current report (8-K)",
    "market": "market fundamentals summary",
    "news": "news article",
    "upload": "uploaded document",
    "subsidiaries": "list of subsidiaries (Exhibit 21)",
}


def template_context(md: SourceMetadata) -> str:
    """A deterministic one-sentence situating blurb from chunk metadata."""
    label = _DOCTYPE_LABEL.get(str(md.doc_type), str(md.doc_type))
    seg = f"This excerpt is from {md.ticker}'s {label}"
    if md.title:
        seg += f' titled "{md.title}"'
    if md.section:
        seg += f', section "{md.section}"'
    if md.filing_date:
        seg += f", filed {md.filing_date}"
    return seg + "."


def contextual_text(text: str, context: str) -> str:
    """The text that actually gets embedded / lexically indexed."""
    context = (context or "").strip()
    return f"{context}\n\n{text}" if context else text


def context_for(md: SourceMetadata, existing: str = "") -> str:
    """Context to index a chunk under — persisted value if present, else recomputed.

    Deterministic recomputation from metadata means the BM25 index and the dense
    embedding agree even when the store doesn't round-trip the ``context`` field.
    """
    return existing.strip() if existing and existing.strip() else template_context(md)


# --- optional LLM-written context (needs an API key; off by default) -----------
_LLM_SYSTEM = (
    "You situate a document chunk for retrieval. Given the whole document's summary "
    "and a chunk, write ONE short sentence (<=25 words) stating what company, period, "
    "and topic the chunk concerns. Output only that sentence."
)


def llm_context(router, ticker: str, doc_title: str, chunk_text: str) -> str | None:
    """Best-effort LLM-generated context; returns None to signal template fallback."""
    try:
        if getattr(router, "mode", "stub") == "stub":
            return None
        prompt = (
            f"Document: {ticker} — {doc_title}\n\nChunk:\n{chunk_text[:1500]}\n\n"
            "One-sentence context:"
        )
        out = router.complete(prompt, system=_LLM_SYSTEM, max_tokens=60)
        out = (out or "").strip()
        return out or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_context failed, using template: %s", exc)
        return None
