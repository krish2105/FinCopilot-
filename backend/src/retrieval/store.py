"""Vector store abstraction.

Two backends behind one interface:
  * LocalVectorStore  — SQLite + numpy cosine. Zero external deps, so the whole
    ingestion pipeline runs offline (CI, demos, no Supabase project needed).
  * PgVectorStore     — Supabase Postgres + pgvector (production).

Selection: PgVectorStore when DATABASE_URL is set, else LocalVectorStore.
Both are idempotent on chunk_id and both record (embed_model, dim) so a query
embedded with a different backend fails loudly instead of returning garbage.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass

from src.config.settings import Settings, get_settings
from src.ingestion.models import Chunk, DocType, SourceMetadata

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    text: str
    metadata: SourceMetadata


class VectorStore:
    """Interface. `dim`/`embed_model` are set by the ingesting Embedder."""

    dim: int
    embed_model: str

    def upsert(self, chunks: list[Chunk]) -> int: ...
    def existing_ids(self, ids: list[str]) -> set[str]: ...
    def get_by_ids(self, ids: list[str]) -> list[Chunk]: ...
    def count(self) -> int: ...
    def iter_all(self) -> list[Chunk]: ...
    def search(
        self,
        query_vec: list[float],
        k: int = 8,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> list[SearchHit]: ...
    def assert_query_compatible(self, dim: int, embed_model: str) -> None:
        if dim != self.dim:
            raise ValueError(
                f"Query embedding dim {dim} != store dim {self.dim}. "
                f"The corpus was embedded with '{self.embed_model}'; re-ingest or "
                f"use the same embedder."
            )


def _row_to_chunk(row: dict) -> Chunk:
    md = SourceMetadata(
        ticker=row["ticker"],
        doc_type=DocType(row["doc_type"]),
        title=row["title"] or "",
        source_url=row["source_url"] or "",
        filing_date=row["filing_date"],
        page=row["page"],
        section=row["section"],
        workspace_id=row["workspace_id"] if row.get("workspace_id") else "public",
    )
    emb = json.loads(row["embedding"]) if row["embedding"] else None
    return Chunk(
        chunk_id=row["chunk_id"],
        doc_id=row["doc_id"],
        text=row["text"],
        metadata=md,
        token_estimate=row["token_estimate"] or 0,
        embedding=emb,
    )


class LocalVectorStore(VectorStore):
    def __init__(self, dim: int, embed_model: str, path: str):
        self.dim = dim
        self.embed_model = embed_model
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # check_same_thread=False: FastAPI runs sync handlers in a threadpool, so
        # the process-wide retriever/store is accessed from worker threads. Access
        # is effectively serialized (one query at a time) for our read/write mix.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
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
                embedding TEXT,
                embed_model TEXT,
                dim INTEGER,
                workspace_id TEXT DEFAULT 'public'
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON chunks(ticker)")
        # Migrate older stores that predate the workspace_id column.
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(chunks)")}
        if "workspace_id" not in cols:
            self.conn.execute("ALTER TABLE chunks ADD COLUMN workspace_id TEXT DEFAULT 'public'")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_ws ON chunks(workspace_id)")
        self.conn.commit()

    def upsert(self, chunks: list[Chunk]) -> int:
        rows = []
        for c in chunks:
            if c.embedding is not None and len(c.embedding) != self.dim:
                raise ValueError(
                    f"Chunk {c.chunk_id} embedding dim {len(c.embedding)} != store dim {self.dim}"
                )
            m = c.metadata
            rows.append(
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
                    json.dumps(c.embedding) if c.embedding is not None else None,
                    self.embed_model,
                    self.dim,
                    m.workspace_id,
                )
            )
        self.conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, doc_id, ticker, doc_type, title, source_url,
                filing_date, page, section, text, token_estimate, embedding,
                embed_model, dim, workspace_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(chunk_id) DO NOTHING
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        out: set[str] = set()
        # Chunk into batches to respect SQLite's variable limit.
        for i in range(0, len(ids), 500):
            batch = ids[i : i + 500]
            q = f"SELECT chunk_id FROM chunks WHERE chunk_id IN ({','.join('?' * len(batch))})"
            out.update(r[0] for r in self.conn.execute(q, batch))
        return out

    def get_by_ids(self, ids: list[str]) -> list[Chunk]:
        if not ids:
            return []
        out: list[Chunk] = []
        for i in range(0, len(ids), 500):
            batch = ids[i : i + 500]
            q = f"SELECT * FROM chunks WHERE chunk_id IN ({','.join('?' * len(batch))})"
            out.extend(_row_to_chunk(dict(r)) for r in self.conn.execute(q, batch))
        return out

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def iter_all(self) -> list[Chunk]:
        rows = self.conn.execute("SELECT * FROM chunks").fetchall()
        return [_row_to_chunk(dict(r)) for r in rows]

    def search(
        self,
        query_vec: list[float],
        k: int = 8,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> list[SearchHit]:
        import numpy as np

        self.assert_query_compatible(len(query_vec), self.embed_model)
        sql = "SELECT * FROM chunks WHERE embedding IS NOT NULL"
        params: list = []
        if tickers:
            sql += f" AND ticker IN ({','.join('?' * len(tickers))})"
            params += [t.upper() for t in tickers]
        if workspaces:
            sql += f" AND workspace_id IN ({','.join('?' * len(workspaces))})"
            params += list(workspaces)
        rows = self.conn.execute(sql, params).fetchall()
        if not rows:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        qn = np.linalg.norm(q) or 1.0
        hits: list[SearchHit] = []
        for r in rows:
            v = np.asarray(json.loads(r["embedding"]), dtype=np.float32)
            score = float(np.dot(q, v) / (qn * (np.linalg.norm(v) or 1.0)))
            hits.append(SearchHit(r["chunk_id"], score, r["text"], _row_to_chunk(dict(r)).metadata))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]


def get_vector_store(dim: int, embed_model: str, settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    if settings.database_url:
        from src.retrieval.pg_store import PgVectorStore

        logger.info("Using PgVectorStore (Supabase pgvector)")
        return PgVectorStore(dim, embed_model, settings.database_url)
    path = os.path.join(settings.data_dir, "vectors.sqlite")
    logger.info("Using LocalVectorStore at %s", path)
    return LocalVectorStore(dim, embed_model, path)
