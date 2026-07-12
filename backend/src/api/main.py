"""FastAPI entrypoint.

Phase 0: a booting app with health + metadata endpoints. Query/agent routes are
added from Phase 3 onward.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.account_routes import router as account_router
from src.api.agent_routes import router as agent_router
from src.api.billing_routes import router as billing_router
from src.api.retrieval_routes import router as retrieval_router
from src.api.workspace_routes import router as workspace_router
from src.auth.principal import Principal, get_principal
from src.config.settings import get_settings
from src.db.database import get_db
from src.ops.observability import init_sentry

settings = get_settings()
init_sentry(settings)

app = FastAPI(
    title="FinCopilot API",
    description="Multi-agent, adaptive-RAG financial research copilot.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # set FRONTEND_ORIGIN in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(retrieval_router)
app.include_router(agent_router)
app.include_router(workspace_router)
app.include_router(billing_router)
app.include_router(account_router)


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return resp


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe (also used by Render's health check)."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    """Readiness probe: the metadata DB is reachable."""
    try:
        get_db().query_one("SELECT 1 AS ok")
        return {"ready": True}
    except Exception as exc:  # noqa: BLE001
        return {"ready": False, "error": str(exc)}


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": "FinCopilot API",
        "version": app.version,
        "phase": "13 — security + compliance",
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


@app.get("/graph/stats")
def graph_stats() -> dict[str, object]:
    """Entity-graph summary that backs the GraphRAG relationship route (Phase 4)."""
    from src.retrieval.graph import EntityGraph, graph_path

    graph = EntityGraph.load(graph_path())
    if graph is None:
        return {"built": False, "message": "No entity graph yet — run ingestion."}
    return {"built": True, **graph.stats()}


@app.get("/eval")
def eval_results() -> dict[str, object]:
    """Latest RAGAS/eval results for the evaluation dashboard (Phase 7)."""
    import json
    import os

    from src.evaluation.harness import latest_results_path

    path = latest_results_path()
    if not os.path.exists(path):
        return {"available": False, "message": "No evaluation run yet."}
    with open(path) as f:
        return {"available": True, **json.load(f)}


@app.get("/audit")
def audit(limit: int = 100, principal: Principal = Depends(get_principal)) -> dict[str, object]:
    """Tenant-scoped audit trail: query · routes · sources · providers · verdict."""
    from src.tenancy import repo

    db = get_db()
    records = repo.recent_audit(db, principal.org_id, limit=limit)
    return {"count": repo.audit_count(db, principal.org_id), "records": records}
