"""SaaS extras (Phase 14): feedback, API keys, watchlists.

Kept separate from core tenancy for readability. All functions are tenant-scoped.
"""

from __future__ import annotations

import hashlib
import secrets

from src.db.database import Database
from src.tenancy.repo import _id, _now


# --- feedback (seeds the eval set) ---
def add_feedback(
    db: Database,
    org_id: str,
    user_id: str,
    message_id: str | None,
    rating: int,
    note: str,
    query: str,
) -> str:
    fid = _id("fb")
    db.execute(
        "INSERT INTO feedback (id, message_id, org_id, user_id, rating, note, query, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (fid, message_id, org_id, user_id, rating, note[:2000], query[:2000], _now()),
    )
    return fid


# --- API keys (public API access) ---
def create_api_key(db: Database, org_id: str, name: str) -> tuple[str, dict]:
    """Returns (raw_key, record). The raw key is shown once and never stored."""
    raw = "fk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    kid = _id("key")
    prefix = raw[:10]
    db.execute(
        "INSERT INTO api_keys (id, org_id, name, prefix, key_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (kid, org_id, name[:80], prefix, key_hash, _now()),
    )
    return raw, {"id": kid, "name": name[:80], "prefix": prefix}


def list_api_keys(db: Database, org_id: str) -> list[dict]:
    rows = db.query(
        "SELECT id, name, prefix, created_at, last_used FROM api_keys WHERE org_id = ? "
        "ORDER BY created_at DESC",
        (org_id,),
    )
    return rows


def delete_api_key(db: Database, org_id: str, key_id: str) -> None:
    db.execute("DELETE FROM api_keys WHERE id = ? AND org_id = ?", (key_id, org_id))


# --- watchlists (filing alerts) ---
def add_watchlist(db: Database, org_id: str, ticker: str) -> dict:
    wid = _id("wl")
    db.execute(
        "INSERT INTO watchlists (id, org_id, ticker, created_at) VALUES (?, ?, ?, ?)",
        (wid, org_id, ticker.upper(), _now()),
    )
    return {"id": wid, "ticker": ticker.upper()}


def list_watchlists(db: Database, org_id: str) -> list[dict]:
    return db.query(
        "SELECT id, ticker, last_accession, created_at FROM watchlists WHERE org_id = ? "
        "ORDER BY created_at DESC",
        (org_id,),
    )


def delete_watchlist(db: Database, org_id: str, wl_id: str) -> None:
    db.execute("DELETE FROM watchlists WHERE id = ? AND org_id = ?", (wl_id, org_id))


def set_watchlist_accession(db: Database, wl_id: str, accession: str) -> None:
    db.execute("UPDATE watchlists SET last_accession = ? WHERE id = ?", (accession, wl_id))
