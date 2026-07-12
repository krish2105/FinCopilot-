"""Retrieval API (Phase 2): hybrid + rerank + cited answer for a query."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.retrieval.retriever import get_retriever
from src.retrieval.types import RetrievalResult

router = APIRouter(tags=["retrieval"])


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(6, ge=1, le=20)
    tickers: list[str] | None = None


@router.post("/retrieve", response_model=RetrievalResult)
def retrieve(req: RetrieveRequest) -> RetrievalResult:
    """Return ranked, cited evidence + an extractive cited answer.

    Unauthenticated debug endpoint — scoped to the shared public corpus only so it
    can never surface a tenant's private uploads.
    """
    return get_retriever().retrieve(
        req.query, top_k=req.top_k, tickers=req.tickers, workspaces=["public"]
    )
