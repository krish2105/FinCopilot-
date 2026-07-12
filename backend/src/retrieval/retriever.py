"""Advanced-RAG retriever: embed → hybrid (dense+BM25, RRF) → rerank → cite.

This is the default retrieval foundation for the whole product. The Orchestrator
(Phase 3) calls `Retriever.retrieve(...)`; the adaptive router (Phase 4) will
pick this route for simple factual queries.
"""

from __future__ import annotations

import logging

from src.config.settings import Settings, get_settings
from src.ingestion.embed import Embedder
from src.retrieval.bm25 import BM25Index, bm25_path
from src.retrieval.citations import assign_citations, build_extractive_answer
from src.retrieval.hybrid import hybrid_search
from src.retrieval.reranker import Reranker
from src.retrieval.store import VectorStore, get_vector_store
from src.retrieval.types import RetrievalResult

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        settings: Settings | None = None,
        embedder: Embedder | None = None,
        store: VectorStore | None = None,
        bm25: BM25Index | None = None,
        reranker: Reranker | None = None,
    ):
        self.settings = settings or get_settings()
        self.embedder = embedder or Embedder(self.settings)
        self.store = store or get_vector_store(self.embedder.dim, self.embedder.name, self.settings)
        # bm25 may legitimately be None before the first ingestion.
        self.bm25 = bm25 if bm25 is not None else BM25Index.load(bm25_path())
        self.reranker = reranker or Reranker(self.settings)

    def retrieve(
        self,
        query: str,
        top_k: int = 6,
        candidate_k: int = 30,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> RetrievalResult:
        query_vec = self.embedder.embed([query])[0]
        fused = hybrid_search(
            query_vec,
            query,
            self.store,
            self.bm25,
            candidate_k=candidate_k,
            tickers=tickers,
            workspaces=workspaces,
        )
        reranked = self.reranker.rerank(query, fused, top_k=top_k)
        citations = assign_citations(reranked)
        answer = build_extractive_answer(query, reranked)

        logger.info(
            "retrieve | q=%r | candidates=%d | returned=%d | reranker=%s",
            query,
            len(fused),
            len(reranked),
            self.reranker.name,
        )
        return RetrievalResult(
            query=query,
            route="hybrid",
            chunks=reranked,
            citations=citations,
            answer=answer,
            reranker=self.reranker.name,
            embed_backend=f"{self.embedder.backend}:{self.embedder.name}",
        )


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """Process-wide singleton so the API reuses the loaded index/models."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def reset_retriever() -> None:
    global _retriever
    _retriever = None
