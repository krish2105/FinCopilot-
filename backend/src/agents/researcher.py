"""Researcher agent — turns the query into retrieved, ranked, cited evidence.

Retrieval is the researcher's core competency, so this delegates to the Phase 2
advanced-RAG Retriever (hybrid + rerank + citations). Sub-query expansion and the
agentic ReAct loop for hard queries arrive in Phase 4.
"""

from __future__ import annotations

import logging

from src.retrieval.retriever import Retriever
from src.retrieval.types import RetrievalResult

logger = logging.getLogger(__name__)


def research(
    retriever: Retriever,
    query: str,
    tickers: list[str] | None = None,
    top_k: int = 6,
) -> RetrievalResult:
    result = retriever.retrieve(query, top_k=top_k, tickers=tickers)
    logger.info("researcher: %d evidence chunks for %r", len(result.chunks), query)
    return result
