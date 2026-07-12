-- FinCopilot — Supabase / Postgres schema for the vector store.
-- Run once in the Supabase SQL editor (or let PgVectorStore create it at runtime).
-- NOTE: the vector() dimension must match the ingesting embedder:
--   gemini-embedding-001 -> 768   |   bge-small-en-v1.5 / hash -> 384
-- Adjust the literal below if you change embedding backends, then re-ingest.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id       TEXT PRIMARY KEY,      -- content hash (idempotency key)
    doc_id         TEXT NOT NULL,
    ticker         TEXT NOT NULL,
    doc_type       TEXT NOT NULL,         -- 10-K | 10-Q | 8-K | market | news
    title          TEXT,
    source_url     TEXT,
    filing_date    TEXT,
    page           INTEGER,               -- pseudo-page for citations
    section        TEXT,                  -- e.g. "Item 1A. Risk Factors"
    text           TEXT NOT NULL,
    token_estimate INTEGER,
    embedding      vector(384),           -- <-- match your embedder dim
    embed_model    TEXT,
    dim            INTEGER
);

CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON chunks (ticker);

-- Approximate-nearest-neighbour index for cosine similarity search.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
