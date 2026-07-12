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
        "phase": "0 — scaffold",
        "tickers": settings.tickers,
        "disclaimer": "Informational research only. Not investment advice.",
    }
