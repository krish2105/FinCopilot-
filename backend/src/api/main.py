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
from src.api.notify_routes import router as notify_router
from src.api.retrieval_routes import router as retrieval_router
from src.api.valuation_routes import router as valuation_router
from src.api.xbrl_routes import router as xbrl_router
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
app.include_router(xbrl_router)
app.include_router(valuation_router)
app.include_router(notify_router)
app.include_router(agent_router)
app.include_router(workspace_router)
app.include_router(billing_router)
app.include_router(account_router)
app.include_router(saas_router)
app.include_router(team_router)


def _rebuild_indexes() -> None:
    """Rebuild the BM25 index + entity graph from the shared vector store.

    We seed the vector store (Supabase) from a laptop because the Render free tier
    has no shell, and Render's disk is ephemeral — so the file-based BM25 index and
    entity graph aren't present on the server. Since the vector store already holds
    every chunk's text, we can regenerate both from it, making hybrid search and
    GraphRAG work in production. Runs only when the file is missing.
    """
    import logging
    import os

    log = logging.getLogger(__name__)
    try:
        from src.ingestion.embed import Embedder
        from src.retrieval.bm25 import BM25Index, bm25_path
        from src.retrieval.graph import EntityGraph, graph_path
        from src.retrieval.pg_store import PgVectorStore
        from src.retrieval.store import get_vector_store

        # Bare store — do NOT build the retriever here (it loads the 184 MB cross-encoder,
        # which we don't need to warm indexes and which would spike startup memory).
        embedder = Embedder(settings)
        store = get_vector_store(embedder.dim, embedder.name, settings)
        if store.count() <= 0:
            log.info("warm_indexes: vector store empty, nothing to rebuild")
            return

        # Postgres corpora get lexical search straight from the DB (GIN index) —
        # no in-memory index to build, so only the entity graph needs warming.
        pg = isinstance(store, PgVectorStore)
        if not pg and not os.path.exists(bm25_path()):
            BM25Index.build(store.iter_lite(), bm25_path())
            log.info("warm_indexes: rebuilt in-memory BM25")
        # Rebuild the graph if it's missing OR stale — "stale" meaning it covers fewer
        # companies than the corpus actually holds. That auto-heals a graph left behind
        # by a test run (which writes a tiny fixture graph to the same data dir) or by a
        # corpus that grew since the last build.
        corpus_tickers = len(store.counts_by_ticker())
        existing = EntityGraph.load(graph_path())
        graph_companies = len(existing.companies()) if existing else 0
        if existing is None or graph_companies < corpus_tickers:
            EntityGraph.build(store, graph_path())  # uses iter_lite internally
            log.info(
                "warm_indexes: (re)built entity graph (had %d companies, corpus has %d)",
                graph_companies,
                corpus_tickers,
            )
    except Exception:  # noqa: BLE001
        log.exception("warm_indexes: rebuild failed (hybrid may be degraded)")

    # Prewarm the screener's per-company fundamentals cache — the first /valuation/screener
    # otherwise does ~100 sequential remote lookups (tens of seconds) inside the request.
    try:
        from src.valuation import screener

        n = screener.prewarm(get_db())
        log.info("warm_indexes: prewarmed screener fundamentals for %d tickers", n)
    except Exception:  # noqa: BLE001
        log.exception("warm_indexes: screener prewarm failed (first screen will be slow)")


@app.on_event("startup")
def _warm_indexes() -> None:
    """Kick the index rebuild onto a background thread so it never blocks boot.

    Building the entity graph pulls all ~16k chunk texts from Supabase over the
    network — tens of seconds. If that runs inside the startup event, uvicorn won't
    open its port until it finishes, so Render's health check times out during the
    deploy window and the deploy is marked dead (x-render-routing: no-deploy). Running
    it in a daemon thread lets /health answer instantly (Render marks the deploy live)
    while the graph builds in the background; /graph/* endpoints degrade gracefully
    (return empty) until it's ready, then populate on the next request.
    """
    import threading

    threading.Thread(target=_rebuild_indexes, name="warm-indexes", daemon=True).start()


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
    """How much real data is ingested and searchable (proves Phase 1).

    Aggregates in SQL and never touches the retriever — loading every chunk (with its
    embedding) or the 184 MB cross-encoder just to render a stat card OOM-killed the
    512 MB instance and 502'd the whole dashboard.
    """
    from src.ingestion.embed import Embedder
    from src.retrieval.pg_fts import PgFtsIndex
    from src.retrieval.pg_store import PgVectorStore
    from src.retrieval.store import get_vector_store

    embedder = Embedder(settings)
    store = get_vector_store(embedder.dim, embedder.name, settings)
    total = store.count()
    by_ticker = store.counts_by_ticker() if total else {}

    lexical = "postgres-fts" if isinstance(store, PgVectorStore) else "bm25"
    bm25_docs = total  # FTS indexes every chunk
    if not isinstance(store, PgVectorStore):
        bm25_docs = 0
    else:
        PgFtsIndex(store.conn)  # ensure the GIN index exists (cheap)

    return {
        "embed_backend": f"{embedder.backend}:{embedder.name}",
        "embed_dim": embedder.dim,
        "vector_chunks": total,
        "lexical_backend": lexical,
        "bm25_docs": bm25_docs,
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


@app.get("/graph/heatmap")
def graph_heatmap() -> dict[str, object]:
    """Companies × risk-topics exposure matrix (Phase 47 risk heatmap)."""
    from src.retrieval.graph import EntityGraph, graph_path

    graph = EntityGraph.load(graph_path())
    if graph is None:
        return {"companies": [], "topics": [], "matrix": []}
    return graph.risk_matrix()


@app.get("/graph/network")
def graph_network() -> dict[str, object]:
    """Company↔risk network (Phase 47 entity-graph visualization)."""
    from src.retrieval.graph import EntityGraph, graph_path

    graph = EntityGraph.load(graph_path())
    if graph is None:
        return {"nodes": [], "links": []}
    return graph.network()


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
