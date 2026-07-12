"""Ingestion orchestration: fetch -> parse -> chunk -> embed -> store -> BM25.

Idempotent by construction: chunk ids are content hashes, and chunks already in
the store are skipped before embedding, so re-running an unchanged corpus embeds
and writes nothing new. The BM25 index is rebuilt from the full store afterward.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config.settings import Settings, get_settings
from src.ingestion.chunk import chunk_document
from src.ingestion.embed import Embedder
from src.ingestion.fetchers import edgar, market, news
from src.ingestion.models import Chunk, RawDocument
from src.ingestion.parse import parse_document
from src.retrieval.bm25 import BM25Index, bm25_path
from src.retrieval.store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)

DEFAULT_SOURCES = ("edgar", "market", "news")


@dataclass
class IngestStats:
    tickers: list[str] = field(default_factory=list)
    docs_fetched: int = 0
    chunks_total: int = 0
    chunks_new: int = 0
    chunks_skipped: int = 0
    embed_backend: str = ""
    store_count: int = 0
    bm25_docs: int = 0

    def as_dict(self) -> dict:
        return self.__dict__


def _fetch_documents(ticker: str, sources: tuple[str, ...]) -> list[RawDocument]:
    docs: list[RawDocument] = []
    if "edgar" in sources:
        docs += edgar.fetch_filings(ticker)
    if "market" in sources:
        docs += market.fetch_market(ticker)
    if "news" in sources:
        docs += news.fetch_news(ticker)
    return docs


def _chunk_documents(docs: list[RawDocument]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        blocks = parse_document(doc)
        chunks.extend(chunk_document(doc, blocks))
    # Global de-dupe across docs (identical boilerplate appears across filings).
    seen: set[str] = set()
    out: list[Chunk] = []
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        out.append(c)
    return out


def _embed_and_store(
    chunks: list[Chunk], embedder: Embedder, store: VectorStore, stats: IngestStats
) -> None:
    ids = [c.chunk_id for c in chunks]
    existing = store.existing_ids(ids)
    new_chunks = [c for c in chunks if c.chunk_id not in existing]
    stats.chunks_total += len(chunks)
    stats.chunks_skipped += len(chunks) - len(new_chunks)

    batch = 32
    for i in range(0, len(new_chunks), batch):
        window = new_chunks[i : i + batch]
        vectors = embedder.embed([c.text for c in window])
        for c, v in zip(window, vectors, strict=True):
            c.embedding = v
        store.upsert(window)
        stats.chunks_new += len(window)
        logger.info("Embedded+stored %d/%d new chunks", stats.chunks_new, len(new_chunks))


def ingest(
    tickers: list[str] | None = None,
    sources: tuple[str, ...] = DEFAULT_SOURCES,
    settings: Settings | None = None,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
) -> IngestStats:
    settings = settings or get_settings()
    tickers = tickers or settings.tickers
    embedder = embedder or Embedder(settings)
    store = store or get_vector_store(embedder.dim, embedder.name, settings)

    stats = IngestStats(tickers=tickers, embed_backend=f"{embedder.backend}:{embedder.name}")
    logger.info("Ingest start | tickers=%s | embedder=%s", tickers, stats.embed_backend)

    for ticker in tickers:
        docs = _fetch_documents(ticker, sources)
        stats.docs_fetched += len(docs)
        chunks = _chunk_documents(docs)
        _embed_and_store(chunks, embedder, store, stats)

    # Rebuild BM25 over the full corpus (cheap, keeps it in sync with the store).
    all_chunks = store.iter_all()
    bm25 = BM25Index.build(all_chunks, bm25_path())
    stats.store_count = store.count()
    stats.bm25_docs = len(bm25)

    logger.info("Ingest done | %s", stats.as_dict())
    return stats
