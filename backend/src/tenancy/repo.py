"""Tenancy repository: orgs, users, workspaces, documents, conversations.

Thin functions over the metadata Database. The pre-ingested public corpus lives
in the shared PUBLIC_WORKSPACE, readable by every tenant; each org additionally
gets its own private workspaces ("data rooms").
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from src.db.database import Database

PUBLIC_WORKSPACE = "public"
PUBLIC_ORG = "public"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Org(BaseModel):
    id: str
    name: str
    plan: str = "free"
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None


class Workspace(BaseModel):
    id: str
    org_id: str
    name: str
    kind: str = "private"  # public | private


class Document(BaseModel):
    id: str
    workspace_id: str
    org_id: str
    filename: str
    doc_type: str = ""
    status: str = "ready"
    chunk_count: int = 0
    created_at: str = ""


class Conversation(BaseModel):
    id: str
    workspace_id: str
    org_id: str
    user_id: str | None = None
    title: str = ""
    created_at: str = ""


class Message(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str = ""
    answer_json: str | None = None
    created_at: str = ""


# --- orgs / users ---
def ensure_org_user(db: Database, user_id: str, email: str | None, org_name: str) -> Org:
    """Idempotently ensure a user + their org + a default private workspace."""
    user = db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if user:
        org = db.query_one("SELECT * FROM orgs WHERE id = ?", (user["org_id"],))
        return Org(
            **{
                k: org[k]
                for k in ("id", "name", "plan", "stripe_customer_id", "stripe_subscription_id")
            }
        )

    org_id = _id("org")
    db.execute(
        "INSERT INTO orgs (id, name, plan, created_at) VALUES (?, ?, 'free', ?)",
        (org_id, org_name, _now()),
    )
    db.execute(
        "INSERT INTO users (id, email, org_id, role, created_at) VALUES (?, ?, ?, 'owner', ?)",
        (user_id, email, org_id, _now()),
    )
    create_workspace(db, org_id, "My Workspace")
    return Org(id=org_id, name=org_name, plan="free")


def get_org(db: Database, org_id: str) -> Org | None:
    row = db.query_one("SELECT * FROM orgs WHERE id = ?", (org_id,))
    return (
        Org(
            **{
                k: row[k]
                for k in ("id", "name", "plan", "stripe_customer_id", "stripe_subscription_id")
            }
        )
        if row
        else None
    )


# --- workspaces ---
def create_workspace(db: Database, org_id: str, name: str, kind: str = "private") -> Workspace:
    ws_id = _id("ws")
    db.execute(
        "INSERT INTO workspaces (id, org_id, name, kind, created_at) VALUES (?, ?, ?, ?, ?)",
        (ws_id, org_id, name, kind, _now()),
    )
    return Workspace(id=ws_id, org_id=org_id, name=name, kind=kind)


def list_workspaces(db: Database, org_id: str) -> list[Workspace]:
    rows = db.query("SELECT * FROM workspaces WHERE org_id = ? ORDER BY created_at", (org_id,))
    return [Workspace(**{k: r[k] for k in ("id", "org_id", "name", "kind")}) for r in rows]


def get_workspace(db: Database, ws_id: str) -> Workspace | None:
    r = db.query_one("SELECT * FROM workspaces WHERE id = ?", (ws_id,))
    return Workspace(**{k: r[k] for k in ("id", "org_id", "name", "kind")}) if r else None


def accessible_workspace_ids(db: Database, org_id: str) -> list[str]:
    """Every workspace a tenant may read: the shared public corpus + its own."""
    own = [w.id for w in list_workspaces(db, org_id)]
    return [PUBLIC_WORKSPACE, *own]


# --- documents ---
def create_document(
    db: Database, org_id: str, workspace_id: str, filename: str, doc_type: str, uploaded_by: str
) -> Document:
    doc_id = _id("doc")
    now = _now()
    db.execute(
        "INSERT INTO documents (id, workspace_id, org_id, filename, doc_type, status, "
        "chunk_count, uploaded_by, created_at) VALUES (?, ?, ?, ?, ?, 'processing', 0, ?, ?)",
        (doc_id, workspace_id, org_id, filename, doc_type, uploaded_by, now),
    )
    return Document(
        id=doc_id,
        workspace_id=workspace_id,
        org_id=org_id,
        filename=filename,
        doc_type=doc_type,
        status="processing",
        created_at=now,
    )


def finalize_document(db: Database, doc_id: str, chunk_count: int) -> None:
    db.execute(
        "UPDATE documents SET status = 'ready', chunk_count = ? WHERE id = ?",
        (chunk_count, doc_id),
    )


def set_document_status(db: Database, doc_id: str, status: str) -> None:
    db.execute("UPDATE documents SET status = ? WHERE id = ?", (status, doc_id))


def list_documents(db: Database, workspace_id: str) -> list[Document]:
    rows = db.query(
        "SELECT * FROM documents WHERE workspace_id = ? ORDER BY created_at DESC", (workspace_id,)
    )
    return [
        Document(
            **{
                k: r[k]
                for k in (
                    "id",
                    "workspace_id",
                    "org_id",
                    "filename",
                    "doc_type",
                    "status",
                    "chunk_count",
                    "created_at",
                )
            }
        )
        for r in rows
    ]


def get_document(db: Database, doc_id: str) -> Document | None:
    r = db.query_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    return (
        Document(
            **{
                k: r[k]
                for k in (
                    "id",
                    "workspace_id",
                    "org_id",
                    "filename",
                    "doc_type",
                    "status",
                    "chunk_count",
                    "created_at",
                )
            }
        )
        if r
        else None
    )


def delete_document(db: Database, doc_id: str) -> None:
    db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


# --- conversations / messages ---
def create_conversation(
    db: Database, org_id: str, workspace_id: str, user_id: str, title: str
) -> Conversation:
    cid = _id("conv")
    now = _now()
    db.execute(
        "INSERT INTO conversations (id, workspace_id, org_id, user_id, title, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (cid, workspace_id, org_id, user_id, title[:120], now),
    )
    return Conversation(
        id=cid,
        workspace_id=workspace_id,
        org_id=org_id,
        user_id=user_id,
        title=title[:120],
        created_at=now,
    )


def list_conversations(db: Database, org_id: str, user_id: str) -> list[Conversation]:
    rows = db.query(
        "SELECT * FROM conversations WHERE org_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 100",
        (org_id, user_id),
    )
    return [
        Conversation(
            **{k: r[k] for k in ("id", "workspace_id", "org_id", "user_id", "title", "created_at")}
        )
        for r in rows
    ]


def add_message(
    db: Database, conversation_id: str, role: str, content: str, answer_json: str | None = None
) -> str:
    mid = _id("msg")
    db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, answer_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (mid, conversation_id, role, content, answer_json, _now()),
    )
    return mid


# --- audit (tenant-scoped) ---
def write_audit(db: Database, org_id: str, user_id: str, answer, tickers: list[str] | None) -> None:
    providers = sorted({f"{c.provider}:{c.model}" for c in answer.provider_trace})
    db.execute(
        "INSERT INTO audit (id, org_id, user_id, ts, query, tickers, planned_route, route, "
        "verdict, evidence_count, sources, providers, faithfulness_score, latency_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _id("aud"),
            org_id,
            user_id,
            _now(),
            answer.query,
            ",".join(tickers or []),
            answer.planned_route,
            answer.route,
            answer.verdict,
            answer.evidence_count,
            " | ".join(c.label() for c in answer.citations),
            ",".join(providers),
            answer.faithfulness.score,
            answer.latency_ms,
        ),
    )


def recent_audit(db: Database, org_id: str, limit: int = 100) -> list[dict]:
    rows = db.query(
        "SELECT * FROM audit WHERE org_id = ? ORDER BY ts DESC LIMIT ?", (org_id, limit)
    )
    for r in rows:
        r["tickers"] = r["tickers"].split(",") if r.get("tickers") else []
        r["sources"] = r["sources"].split(" | ") if r.get("sources") else []
        r["providers"] = r["providers"].split(",") if r.get("providers") else []
    return rows


def audit_count(db: Database, org_id: str) -> int:
    row = db.query_one("SELECT COUNT(*) AS n FROM audit WHERE org_id = ?", (org_id,))
    return int(row["n"]) if row else 0


def list_messages(db: Database, conversation_id: str) -> list[Message]:
    rows = db.query(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,)
    )
    return [
        Message(
            **{
                k: r[k]
                for k in ("id", "conversation_id", "role", "content", "answer_json", "created_at")
            }
        )
        for r in rows
    ]
