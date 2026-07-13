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

    def _ensure_bm25(self) -> None:
        """Lazily (re)build the BM25 index from the vector store when it's absent.

        On Render the disk is ephemeral and the corpus is seeded from a laptop, so
        the BM25 file often isn't present. Since the vector store holds every chunk,
        we rebuild the lexical index on the first query and cache it in this
        process-wide singleton. Critical for the offline/hash embedding stack, where
        dense similarity is weak and BM25 does most of the retrieval work.
        """
        if self.bm25 is not None and len(self.bm25) > 0:
            return
        try:
            if self.store.count() <= 0:
                return
            chunks = self.store.iter_all()
            self.bm25 = BM25Index.build(chunks, bm25_path())
            logger.info("Lazily rebuilt BM25 from vector store: %d docs", len(self.bm25))
        except Exception:  # noqa: BLE001
            logger.exception("lazy BM25 rebuild failed")

    def retrieve(
        self,
        query: str,
        top_k: int = 6,
        candidate_k: int = 30,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> RetrievalResult:
        self._ensure_bm25()
        query_vec = self.embedder.embed([query])[0]
        fused = hybrid_search(
            query_vec,
            query,
            self.store,
            self.bm25,
            candidate_k=candidate_k,
            tickers=tickers,
            workspaces=workspaces,
            # Hash embeddings are non-semantic — lexical-only avoids RRF dilution.
            use_dense=self.embedder.backend != "hash",
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
