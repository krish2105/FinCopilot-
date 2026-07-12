"""Tiny metadata database abstraction over SQLite (local/CI) and Postgres (prod).

Everything tenant-related — orgs, users, workspaces, documents, conversations,
usage, billing, feedback, api keys, audit — lives here. SQL uses `?` placeholders
(translated to `%s` for Postgres). Kept deliberately small; not an ORM.

Selection: Postgres when DATABASE_URL is a postgres URL, else a local SQLite file.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, dsn: str | None, data_dir: str):
        self.is_pg = bool(dsn and dsn.startswith(("postgres://", "postgresql://")))
        self._lock = threading.Lock()
        if self.is_pg:
            import psycopg

            self._conn = psycopg.connect(dsn, autocommit=True)
        else:
            os.makedirs(data_dir, exist_ok=True)
            path = os.path.join(data_dir, "app.sqlite")
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _ph(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.is_pg else sql

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self._conn.execute(self._ph(sql), params)
            if not self.is_pg:
                self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(self._ph(sql), params)
            if self.is_pg:
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def _init_schema(self) -> None:
        # JSON stored as TEXT; timestamps as ISO TEXT — portable across both engines.
        stmts = [
            """CREATE TABLE IF NOT EXISTS orgs (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT DEFAULT 'free',
                stripe_customer_id TEXT, stripe_subscription_id TEXT,
                created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT, org_id TEXT NOT NULL,
                role TEXT DEFAULT 'member', created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY, org_id TEXT NOT NULL, name TEXT NOT NULL,
                kind TEXT DEFAULT 'private', created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, org_id TEXT NOT NULL,
                filename TEXT NOT NULL, doc_type TEXT, status TEXT DEFAULT 'ready',
                chunk_count INTEGER DEFAULT 0, uploaded_by TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, org_id TEXT NOT NULL,
                user_id TEXT, title TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT, answer_json TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS usage_events (
                id TEXT PRIMARY KEY, org_id TEXT NOT NULL, user_id TEXT, ts TEXT NOT NULL,
                kind TEXT, tokens INTEGER DEFAULT 0, providers TEXT)""",
            """CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY, message_id TEXT, org_id TEXT, user_id TEXT,
                rating INTEGER, note TEXT, query TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY, org_id TEXT NOT NULL, name TEXT, prefix TEXT,
                key_hash TEXT NOT NULL, created_at TEXT NOT NULL, last_used TEXT,
                expires_at TEXT)""",
            """CREATE TABLE IF NOT EXISTS watchlists (
                id TEXT PRIMARY KEY, org_id TEXT NOT NULL, ticker TEXT NOT NULL,
                last_accession TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS audit (
                id TEXT PRIMARY KEY, org_id TEXT, user_id TEXT, ts TEXT NOT NULL,
                query TEXT, tickers TEXT, planned_route TEXT, route TEXT, verdict TEXT,
                evidence_count INTEGER, sources TEXT, providers TEXT,
                faithfulness_score REAL, latency_ms INTEGER)""",
            "CREATE INDEX IF NOT EXISTS idx_ws_org ON workspaces(org_id)",
            "CREATE INDEX IF NOT EXISTS idx_docs_ws ON documents(workspace_id)",
            "CREATE INDEX IF NOT EXISTS idx_conv_ws ON conversations(workspace_id)",
            "CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_org ON usage_events(org_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_org ON audit(org_id)",
        ]
        for s in stmts:
            self.execute(s)


_db: Database | None = None


def get_db(settings: Settings | None = None) -> Database:
    global _db
    if _db is None:
        settings = settings or get_settings()
        _db = Database(settings.database_url, settings.data_dir)
    return _db


def reset_db() -> None:
    global _db
    _db = None
