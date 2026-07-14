"""Postgres full-text lexical search (Phase 32) — the production BM25 replacement.

The in-memory `rank_bm25` index served us well locally, but it's the wrong tool in
production:

* **It isn't there.** The corpus is seeded from a laptop and Render's disk is
  ephemeral, so the index file never exists on the server — it had to be rebuilt
  from the vector store on every cold start.
* **It doesn't fit.** Holding tens of thousands of tokenized documents in RAM is a
  real problem on a 512 MB free instance (we saw OOM-induced 502s at ~3.5k chunks).
* **Postgres already does this.** A GIN-indexed `tsvector` scales, persists, needs
  zero warm-up, and costs no application memory.

The indexed expression mirrors **Contextual Retrieval**: we search over
`ticker + title + section + text`, so lexical matching still benefits from the
situating context even though the context blurb isn't a stored column. The index
expression and the query expression must be byte-identical for Postgres to use the
GIN index — hence the single `_FTS_EXPR` constant.

Exposes the same interface as `BM25Index` (`query`, `__len__`) so it drops straight
into `hybrid_search`.
"""

from __future__ import annotations

import logging

from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.store import SearchHit

logger = logging.getLogger(__name__)

# Must match between the index definition and the query for the GIN index to be used.
_FTS_EXPR = (
    "to_tsvector('english', coalesce(ticker,'') || ' ' || coalesce(title,'') || ' ' "
    "|| coalesce(section,'') || ' ' || coalesce(text,''))"
)


class PgFtsIndex:
    """Lexical search backed by Postgres full-text search."""

    name = "postgres-fts"

    def __init__(self, conn) -> None:
        self.conn = conn
        self._ensure_index()

    def _ensure_index(self) -> None:
        try:
            self.conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_chunks_fts ON chunks USING GIN ({_FTS_EXPR})"
            )
            logger.info("Postgres FTS index ready")
        except Exception:  # noqa: BLE001
            # A missing index only costs speed (sequential scan), never correctness.
            logger.exception("could not create FTS index; lexical search will be slower")

    def query(
        self,
        text: str,
        k: int = 8,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> list[SearchHit]:
        if not text.strip():
            return []
        ticker_filter = [t.upper() for t in tickers] if tickers else None
        ws_filter = list(workspaces) if workspaces else None

        sql = f"""
            SELECT chunk_id, text, ticker, doc_type, title, source_url, filing_date,
                   page, section, ts_rank_cd({_FTS_EXPR}, q) AS rank
            FROM chunks, plainto_tsquery('english', %s) AS q
            WHERE {_FTS_EXPR} @@ q
              AND (%s::text[] IS NULL OR ticker = ANY(%s))
              AND (%s::text[] IS NULL OR workspace_id = ANY(%s))
            ORDER BY rank DESC
            LIMIT %s
        """
        try:
            rows = self.conn.execute(
                sql,
                (text, ticker_filter, ticker_filter, ws_filter, ws_filter, k),
            ).fetchall()
        except Exception:  # noqa: BLE001
            logger.exception("Postgres FTS query failed")
            return []

        hits: list[SearchHit] = []
        for r in rows:
            cid, body, ticker, doc_type, title, url, filing_date, page, section, rank = r
            md = SourceMetadata(
                ticker=ticker,
                doc_type=DocType(doc_type),
                title=title or "",
                source_url=url or "",
                filing_date=filing_date,
                page=page,
                section=section,
            )
            hits.append(SearchHit(cid, float(rank or 0.0), body, md))
        return hits

    def __len__(self) -> int:
        try:
            return int(self.conn.execute("SELECT count(*) FROM chunks").fetchone()[0])
        except Exception:  # noqa: BLE001
            return 0
