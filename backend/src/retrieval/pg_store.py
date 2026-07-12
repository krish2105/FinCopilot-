"""Supabase Postgres + pgvector implementation of VectorStore.

Imported lazily by get_vector_store() only when DATABASE_URL is set, so the
offline path never needs psycopg/pgvector installed.
"""

from __future__ import annotations

import logging

from src.ingestion.models import Chunk, DocType, SourceMetadata
from src.retrieval.store import SearchHit, VectorStore

logger = logging.getLogger(__name__)

_COLS = (
    "chunk_id, doc_id, ticker, doc_type, title, source_url, filing_date, page, "
    "section, text, token_estimate, embedding, workspace_id"
)


class PgVectorStore(VectorStore):
    def __init__(self, dim: int, embed_model: str, database_url: str):
        import psycopg
        from pgvector.psycopg import register_vector

        self.dim = dim
        self.embed_model = embed_model
        self.conn = psycopg.connect(database_url, autocommit=True)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.conn)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                title TEXT,
                source_url TEXT,
                filing_date TEXT,
                page INTEGER,
                section TEXT,
                text TEXT NOT NULL,
                token_estimate INTEGER,
                embedding vector({self.dim}),
                embed_model TEXT,
                dim INTEGER,
                workspace_id TEXT DEFAULT 'public'
            )
            """
        )
        self.conn.execute(
            "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS workspace_id TEXT DEFAULT 'public'"
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON chunks(ticker)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_ws ON chunks(workspace_id)")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )

    def upsert(self, chunks: list[Chunk]) -> int:
        with self.conn.cursor() as cur:
            for c in chunks:
                if c.embedding is not None and len(c.embedding) != self.dim:
                    raise ValueError(f"Chunk {c.chunk_id} dim {len(c.embedding)} != {self.dim}")
                m = c.metadata
                cur.execute(
                    """
                    INSERT INTO chunks (
                        chunk_id, doc_id, ticker, doc_type, title, source_url,
                        filing_date, page, section, text, token_estimate,
                        embedding, embed_model, dim, workspace_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (chunk_id) DO NOTHING
                    """,
                    (
                        c.chunk_id,
                        c.doc_id,
                        m.ticker,
                        m.doc_type.value,
                        m.title,
                        m.source_url,
                        m.filing_date,
                        m.page,
                        m.section,
                        c.text,
                        c.token_estimate,
                        c.embedding,
                        self.embed_model,
                        self.dim,
                        m.workspace_id,
                    ),
                )
        return len(chunks)

    def existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        rows = self.conn.execute(
            "SELECT chunk_id FROM chunks WHERE chunk_id = ANY(%s)", (ids,)
        ).fetchall()
        return {r[0] for r in rows}

    def get_by_ids(self, ids: list[str]) -> list[Chunk]:
        if not ids:
            return []
        rows = self.conn.execute(
            f"SELECT {_COLS} FROM chunks WHERE chunk_id = ANY(%s)", (ids,)
        ).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def iter_all(self) -> list[Chunk]:
        rows = self.conn.execute(f"SELECT {_COLS} FROM chunks").fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def search(
        self,
        query_vec: list[float],
        k: int = 8,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> list[SearchHit]:
        self.assert_query_compatible(len(query_vec), self.embed_model)
        where = "WHERE embedding IS NOT NULL"
        params: list = [query_vec]
        if tickers:
            where += " AND ticker = ANY(%s)"
            params.append([t.upper() for t in tickers])
        if workspaces:
            where += " AND workspace_id = ANY(%s)"
            params.append(list(workspaces))
        params += [query_vec, k]
        rows = self.conn.execute(
            "SELECT chunk_id, text, ticker, doc_type, title, source_url, "
            "filing_date, page, section, workspace_id, "
            "1 - (embedding <=> %s::vector) AS score "
            f"FROM chunks {where} "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            tuple(params),
        ).fetchall()
        hits = []
        for r in rows:
            md = SourceMetadata(
                ticker=r[2],
                doc_type=DocType(r[3]),
                title=r[4] or "",
                source_url=r[5] or "",
                filing_date=r[6],
                page=r[7],
                section=r[8],
                workspace_id=r[9] or "public",
            )
            hits.append(SearchHit(r[0], float(r[10]), r[1], md))
        return hits

    @staticmethod
    def _row_to_chunk(r) -> Chunk:
        md = SourceMetadata(
            ticker=r[2],
            doc_type=DocType(r[3]),
            title=r[4] or "",
            source_url=r[5] or "",
            filing_date=r[6],
            page=r[7],
            section=r[8],
            workspace_id=r[12] if len(r) > 12 and r[12] else "public",
        )
        emb = list(r[11]) if r[11] is not None else None
        return Chunk(
            chunk_id=r[0],
            doc_id=r[1],
            text=r[9],
            metadata=md,
            token_estimate=r[10] or 0,
            embedding=emb,
        )
