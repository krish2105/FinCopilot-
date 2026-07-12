"""Typed retrieval results shared across retrieval and (later) the agents/API.

A retrieval produces ranked RetrievedChunks, each tied to a Citation so every
downstream claim can point back to a real filing page/section.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.ingestion.models import SourceMetadata


class Citation(BaseModel):
    """A numbered, renderable pointer back to a source location."""

    marker: str  # "[1]", "[2]", ...
    ticker: str
    doc_type: str
    title: str = ""
    page: int | None = None
    section: str | None = None
    source_url: str = ""
    excerpt: str = ""

    def label(self) -> str:
        """Human-readable citation label, e.g. 'AAPL 10-K p.54 · Item 8'."""
        parts = [self.ticker, self.doc_type]
        if self.page is not None:
            parts.append(f"p.{self.page}")
        line = " ".join(parts)
        if self.section:
            line += f" · {self.section}"
        return line


class RetrievedChunk(BaseModel):
    """A candidate chunk with its provenance and per-stage scores."""

    chunk_id: str
    text: str
    metadata: SourceMetadata
    marker: str = ""  # citation marker assigned after ranking
    dense_rank: int | None = None
    bm25_rank: int | None = None
    rrf_score: float = 0.0
    rerank_score: float | None = None


class RetrievalResult(BaseModel):
    """Everything the API/agents need: ranked evidence + citations + an
    extractive, fully-cited answer (LLM synthesis is layered on in Phase 3)."""

    query: str
    route: str = "hybrid"
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    answer: str = ""
    reranker: str = ""
    embed_backend: str = ""
