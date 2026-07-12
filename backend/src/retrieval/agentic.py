"""Agentic multi-hop retrieval (Phase 4).

For hard/compound questions, decompose the query into sub-queries and retrieve
iteratively, accumulating unique evidence. Capped at 3 iterations and every round
is logged. Live: the provider router proposes sub-queries (structured). Offline:
a deterministic splitter on conjunctions/comparison markers.

This keeps the ReAct-style loop cheap and bounded — complexity is a cost, not a
virtue: only queries the classifier flags as multi-hop pay for it.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from src.providers.router import ProviderRouter
from src.retrieval.citations import assign_citations, build_extractive_answer
from src.retrieval.retriever import Retriever
from src.retrieval.types import RetrievalResult, RetrievedChunk

logger = logging.getLogger(__name__)

MAX_ITERS = 3
_SPLIT_RE = re.compile(r"\s+(?:and|versus|vs\.?|compared to|as well as)\s+", re.IGNORECASE)


class SubQueries(BaseModel):
    sub_queries: list[str] = Field(default_factory=list)


def _stub_decompose(query: str) -> SubQueries:
    parts = [p.strip(" ?.") for p in _SPLIT_RE.split(query) if p.strip(" ?.")]
    subs = [query] + [p for p in parts if p and p.lower() != query.lower()]
    # Unique, preserve order, cap.
    seen, out = set(), []
    for s in subs:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return SubQueries(sub_queries=out[:MAX_ITERS])


def agentic_retrieve(
    retriever: Retriever,
    router: ProviderRouter,
    query: str,
    tickers: list[str] | None = None,
    top_k: int = 6,
    trace: list | None = None,
    workspaces: list[str] | None = None,
) -> RetrievalResult:
    plan = router.structured(
        f"Decompose this financial question into up to {MAX_ITERS} focused "
        f"sub-queries for retrieval:\n{query}",
        SubQueries,
        stub=lambda: _stub_decompose(query),
        trace=trace,
    )
    sub_queries = plan.sub_queries[:MAX_ITERS] or [query]

    by_id: dict[str, RetrievedChunk] = {}
    for i, sq in enumerate(sub_queries, start=1):
        res = retriever.retrieve(sq, top_k=top_k, tickers=tickers, workspaces=workspaces)
        logger.info(
            "agentic iter %d/%d | %r -> %d chunks", i, len(sub_queries), sq, len(res.chunks)
        )
        for c in res.chunks:
            # Keep the best (highest rrf) copy of each chunk seen across iterations.
            prev = by_id.get(c.chunk_id)
            if prev is None or c.rrf_score > prev.rrf_score:
                by_id[c.chunk_id] = c

    merged = sorted(by_id.values(), key=lambda c: c.rrf_score, reverse=True)[:top_k]
    # Re-rank the merged set against the ORIGINAL query for final ordering.
    merged = retriever.reranker.rerank(query, merged, top_k=top_k)
    citations = assign_citations(merged)
    answer = build_extractive_answer(query, merged)

    return RetrievalResult(
        query=query,
        route="agentic",
        chunks=merged,
        citations=citations,
        answer=answer,
        reranker=retriever.reranker.name,
        embed_backend=f"{retriever.embedder.backend}:{retriever.embedder.name}",
    )
