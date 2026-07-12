"""Builds the evaluation corpus from the benchmark's own gold evidence passages.

Each question's real gold evidence (a passage from the real 10-K) becomes one
document; retrieval must then surface the correct passage among all of them (a
proper needle-in-haystack test on real filing text). doc_id == question id, so a
retrieval "hit" means we pulled the right source for that question.
"""

from __future__ import annotations

import logging

from src.config.settings import Settings
from src.evaluation.dataset import EvalQuestion
from src.ingestion.chunk import chunk_document
from src.ingestion.embed import Embedder
from src.ingestion.models import DocType, RawDocument, SourceMetadata
from src.ingestion.parse import parse_document
from src.retrieval.bm25 import BM25Index
from src.retrieval.reranker import Reranker
from src.retrieval.retriever import Retriever
from src.retrieval.store import LocalVectorStore

logger = logging.getLogger(__name__)


def build_eval_retriever(questions: list[EvalQuestion], settings: Settings) -> Retriever:
    """Ingest all gold evidence passages into a dedicated local store + BM25."""
    import os

    embedder = Embedder(settings)
    store = LocalVectorStore(
        embedder.dim, embedder.name, os.path.join(settings.data_dir, "eval_vectors.sqlite")
    )
    all_chunks = []
    for q in questions:
        md = SourceMetadata(
            ticker=q.ticker,
            doc_type=DocType.TEN_K,
            title=q.doc_name or f"{q.ticker} 10-K",
            source_url=f"benchmark://{q.benchmark}/{q.id}",
            filing_date=None,
            page=q.page,
        )
        doc = RawDocument(doc_id=q.id, metadata=md, content=q.evidence, content_type="text")
        chunks = chunk_document(doc, parse_document(doc))
        all_chunks.extend(chunks)

    # Idempotent: only embed chunks not already stored.
    existing = store.existing_ids([c.chunk_id for c in all_chunks])
    new = [c for c in all_chunks if c.chunk_id not in existing]
    batch = 32
    for i in range(0, len(new), batch):
        window = new[i : i + batch]
        vecs = embedder.embed([c.text for c in window])
        for c, v in zip(window, vecs, strict=True):
            c.embedding = v
        store.upsert(window)

    bm25 = BM25Index.build(store.iter_all(), os.path.join(settings.data_dir, "eval_bm25.json"))
    logger.info(
        "eval corpus: %d passages -> %d chunks (%d new)",
        len(questions),
        store.count(),
        len(new),
    )
    return Retriever(
        settings=settings,
        embedder=embedder,
        store=store,
        bm25=bm25,
        reranker=Reranker(settings),
    )
