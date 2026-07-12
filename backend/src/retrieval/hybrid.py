"""Hybrid search: dense (pgvector) + lexical (BM25) fused with Reciprocal Rank
Fusion (RRF).

RRF is score-scale agnostic — it combines *ranks*, not raw scores, so we never
have to normalize cosine similarities against BM25 magnitudes. Each source
contributes 1 / (rrf_k + rank) per document; ties break toward documents that
appear in both lists.
"""

from __future__ import annotations

from src.retrieval.bm25 import BM25Index
from src.retrieval.store import SearchHit, VectorStore
from src.retrieval.types import RetrievedChunk

RRF_K = 60


def _rank_map(hits: list[SearchHit]) -> dict[str, int]:
    return {h.chunk_id: rank for rank, h in enumerate(hits, start=1)}


def hybrid_search(
    query_vec: list[float],
    query_text: str,
    store: VectorStore,
    bm25: BM25Index | None,
    candidate_k: int = 30,
    tickers: list[str] | None = None,
    workspaces: list[str] | None = None,
) -> list[RetrievedChunk]:
    dense_hits = store.search(query_vec, k=candidate_k, tickers=tickers, workspaces=workspaces)
    bm25_hits = (
        bm25.query(query_text, k=candidate_k, tickers=tickers, workspaces=workspaces)
        if bm25
        else []
    )

    dense_ranks = _rank_map(dense_hits)
    bm25_ranks = _rank_map(bm25_hits)

    # Union of both candidate sets, keyed by chunk_id with best-available payload.
    payload: dict[str, SearchHit] = {}
    for h in dense_hits + bm25_hits:
        payload.setdefault(h.chunk_id, h)

    fused: list[RetrievedChunk] = []
    for cid, hit in payload.items():
        dr = dense_ranks.get(cid)
        br = bm25_ranks.get(cid)
        score = 0.0
        if dr is not None:
            score += 1.0 / (RRF_K + dr)
        if br is not None:
            score += 1.0 / (RRF_K + br)
        fused.append(
            RetrievedChunk(
                chunk_id=cid,
                text=hit.text,
                metadata=hit.metadata,
                dense_rank=dr,
                bm25_rank=br,
                rrf_score=score,
            )
        )

    fused.sort(key=lambda c: c.rrf_score, reverse=True)
    return fused
