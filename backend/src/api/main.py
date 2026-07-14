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
from src.api.insights_routes import router as insights_router
from src.api.market_routes import router as market_router
from src.api.retrieval_routes import router as retrieval_router
from src.api.saas_routes import router as saas_router
from src.api.team_routes import router as team_router
from src.api.workspace_routes import router as workspace_router
from src.auth.principal import Principal, get_principal
from src.config.settings import get_settings
from src.db.database import get_db
from src.ops.observability import init_sentry, init_tracing

settings = get_settings()
init_sentry(settings)
init_tracing(settings)

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
app.include_router(market_router)
app.include_router(insights_router)
app.include_router(agent_router)
app.include_router(workspace_router)
app.include_router(billing_router)
app.include_router(account_router)
app.include_router(saas_router)
app.include_router(team_router)


@app.on_event("startup")
def _warm_indexes() -> None:
    """Rebuild the BM25 index + entity graph from the shared vector store on boot.

    We seed the vector store (Supabase) from a laptop because the Render free tier
    has no shell, and Render's disk is ephemeral — so the file-based BM25 index and
    entity graph aren't present on the server. Since the vector store already holds
    every chunk's text, we can regenerate both from it, making hybrid search and
    GraphRAG work in production. Runs only when the BM25 file is missing (once per
    cold start) and never blocks startup on failure.
    """
    import logging
    import os

    log = logging.getLogger(__name__)
    try:
        from src.retrieval.bm25 import BM25Index, bm25_path
        from src.retrieval.graph import EntityGraph, graph_path
        from src.retrieval.pg_fts import PgFtsIndex
        from src.retrieval.retriever import get_retriever

        r = get_retriever()
        store = r.store
        if store.count() <= 0:
            log.info("warm_indexes: vector store empty, nothing to rebuild")
            return

        # Postgres corpora get lexical search straight from the DB (GIN index) —
        # no in-memory index to build, so only the entity graph needs warming.
        pg = isinstance(r.bm25, PgFtsIndex)
        if not pg and not os.path.exists(bm25_path()):
            BM25Index.build(store.iter_all(), bm25_path())
            log.info("warm_indexes: rebuilt in-memory BM25")
        if not os.path.exists(graph_path()):
            EntityGraph.build(store, graph_path())
            log.info("warm_indexes: rebuilt entity graph")
    except Exception:  # noqa: BLE001
        log.exception("warm_indexes: rebuild failed (hybrid may be degraded)")


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
        "phase": "20 — teams + RBAC",
        "tickers": settings.tickers,
        "disclaimer": "Informational research only. Not investment advice.",
    }


@app.get("/corpus/stats")
def corpus_stats() -> dict[str, object]:
    """How much real data is ingested and searchable (proves Phase 1)."""
    from src.retrieval.retriever import get_retriever

    r = get_retriever()
    by_ticker: dict[str, int] = {}
    for chunk in r.store.iter_all():
        by_ticker[chunk.metadata.ticker] = by_ticker.get(chunk.metadata.ticker, 0) + 1

    lexical = r.bm25
    return {
        "embed_backend": f"{r.embedder.backend}:{r.embedder.name}",
        "embed_dim": r.embedder.dim,
        "vector_chunks": r.store.count(),
        "lexical_backend": getattr(lexical, "name", "bm25") if lexical else "none",
        "bm25_docs": len(lexical) if lexical else 0,
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
