"""FastAPI entrypoint.

Phase 0: a booting app with health + metadata endpoints. Query/agent routes are
added from Phase 3 onward.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="FinCopilot API",
    description="Multi-agent, adaptive-RAG financial research copilot.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened to the deployed frontend origin in Phase 8
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe (also used by Render's health check)."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": "FinCopilot API",
        "version": app.version,
        "phase": "1 — ingestion",
        "tickers": settings.tickers,
        "disclaimer": "Informational research only. Not investment advice.",
    }


@app.get("/corpus/stats")
def corpus_stats() -> dict[str, object]:
    """How much real data is ingested and searchable (proves Phase 1)."""
    from src.ingestion.embed import Embedder
    from src.retrieval.bm25 import BM25Index, bm25_path
    from src.retrieval.store import get_vector_store

    embedder = Embedder(settings)
    store = get_vector_store(embedder.dim, embedder.name, settings)
    bm25 = BM25Index.load(bm25_path())

    by_ticker: dict[str, int] = {}
    for chunk in store.iter_all():
        by_ticker[chunk.metadata.ticker] = by_ticker.get(chunk.metadata.ticker, 0) + 1

    return {
        "embed_backend": f"{embedder.backend}:{embedder.name}",
        "embed_dim": embedder.dim,
        "vector_chunks": store.count(),
        "bm25_docs": len(bm25) if bm25 else 0,
        "chunks_by_ticker": by_ticker,
    }
