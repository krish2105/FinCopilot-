"""Tenancy metadata database over SQLite (local/CI) and Postgres (prod).

Postgres uses a connection pool and a per-request tenant context (a contextvar +
the `app.current_org` GUC), so **Row-Level Security** policies (see rls.sql) are
enforced safely under concurrency — a request only ever sees its own org's rows,
even if application code has a bug. SQLite (tests/local) keeps a single guarded
connection; RLS is a Postgres feature, so isolation there is the app-level
workspace filter (which is independently tested).
"""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import threading
from contextvars import ContextVar

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# The org whose data the current request may access (Postgres RLS + app scoping).
current_org: ContextVar[str | None] = ContextVar("current_org", default=None)

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS orgs (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT DEFAULT 'free',
        stripe_customer_id TEXT, stripe_subscription_id TEXT, created_at TEXT NOT NULL)""",
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
        key_hash TEXT NOT NULL, created_at TEXT NOT NULL, last_used TEXT, expires_at TEXT)""",
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


class Database:
    def __init__(self, dsn: str | None, data_dir: str):
        self.is_pg = bool(dsn and dsn.startswith(("postgres://", "postgresql://")))
        if self.is_pg:
            from psycopg_pool import ConnectionPool

            self._pool = ConnectionPool(
                dsn, min_size=1, max_size=10, kwargs={"autocommit": True}, open=True
            )
        else:
            os.makedirs(data_dir, exist_ok=True)
            self._lock = threading.Lock()
            self._sqlite = sqlite3.connect(
                os.path.join(data_dir, "app.sqlite"), check_same_thread=False
            )
            self._sqlite.row_factory = sqlite3.Row
            self._sqlite.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    # --- tenant context (Postgres RLS + app scoping) ---
    @staticmethod
    def set_tenant(org_id: str | None) -> None:
        current_org.set(org_id)

    @staticmethod
    def clear_tenant() -> None:
        current_org.set(None)

    def _ph(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.is_pg else sql

    @contextlib.contextmanager
    def _conn(self):
        if self.is_pg:
            with self._pool.connection() as conn:
                org = current_org.get()
                if org is not None:
                    # Set BEFORE every query so a pooled connection can't leak a
                    # previous request's tenant context (RLS reads this GUC).
                    conn.execute("SELECT set_config('app.current_org', %s, false)", (org,))
                yield conn
        else:
            with self._lock:
                yield self._sqlite

    # --- API ---
    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._conn() as conn:
            conn.execute(self._ph(sql), params)
            if not self.is_pg:
                conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._conn() as conn:
            cur = conn.execute(self._ph(sql), params)
            if self.is_pg:
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def _init_schema(self) -> None:
        for stmt in _SCHEMA:
            self.execute(stmt)


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
