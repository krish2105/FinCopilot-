"""Typed data models shared across the ingestion pipeline.

A document flows: RawDocument -> (parse) -> ParsedBlock[] -> (chunk) -> Chunk[]
-> (embed) -> Chunk with .embedding -> (store) -> vector store + BM25 index.

Every Chunk carries SourceMetadata so answers can cite ticker / filing / page.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, Field


class DocType(StrEnum):
    TEN_K = "10-K"
    TEN_Q = "10-Q"
    EIGHT_K = "8-K"
    MARKET = "market"  # yfinance fundamentals rendered as text
    NEWS = "news"  # GDELT headline/article
    UPLOAD = "upload"  # user-uploaded document (data room)
    SUBSIDIARIES = "subsidiaries"  # 10-K Exhibit 21 — list of subsidiaries


class SourceMetadata(BaseModel):
    """Everything needed to render a citation back to the original source."""

    ticker: str
    doc_type: DocType
    title: str = ""
    source_url: str = ""
    filing_date: str | None = None  # ISO date string
    # Pseudo-page (see parse.py) and section heading for in-document citation.
    page: int | None = None
    section: str | None = None
    # Tenancy: which workspace/data-room this chunk belongs to. The shared public
    # corpus uses "public"; uploaded documents use their private workspace id.
    workspace_id: str = "public"


class RawDocument(BaseModel):
    """A fetched, not-yet-parsed source document."""

    doc_id: str
    metadata: SourceMetadata
    # Raw payload; `content_type` disambiguates how parse.py should handle it.
    content: str
    content_type: str = "html"  # "html" | "text"

    @staticmethod
    def make_doc_id(ticker: str, doc_type: DocType, key: str) -> str:
        raw = f"{ticker}:{doc_type.value}:{key}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class ParsedBlock(BaseModel):
    """A contiguous text block from a parsed document, with location info."""

    text: str
    page: int
    section: str
    is_table: bool = False


class Chunk(BaseModel):
    """The unit that gets embedded, stored, and retrieved."""

    chunk_id: str  # deterministic content hash -> idempotency key
    doc_id: str
    text: str
    metadata: SourceMetadata
    token_estimate: int = 0
    embedding: list[float] | None = Field(default=None, repr=False)

    @staticmethod
    def make_chunk_id(doc_id: str, text: str) -> str:
        """Content-addressed id: identical text in the same doc -> same id.

        This is the idempotency key — re-ingesting an unchanged filing produces
        the same chunk ids, so the store skips already-embedded chunks.
        """
        digest = hashlib.sha256(f"{doc_id}:{text}".encode()).hexdigest()
        return digest[:24]
