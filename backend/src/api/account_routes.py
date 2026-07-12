"""Account data export + deletion (Phase 13, GDPR-style).

Lets a tenant export or permanently delete all of their data — a compliance
requirement analysts/PE buyers expect. Deletion also purges the tenant's vectors
from the store so uploaded content is truly gone.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.principal import Principal, get_principal
from src.db.database import get_db
from src.retrieval.retriever import get_retriever
from src.tenancy import repo

router = APIRouter(tags=["account"])

_TABLES = ("audit", "usage_events", "conversations", "documents", "workspaces")


@router.get("/account/export")
def export_account(principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    org = principal.org_id
    workspaces = repo.list_workspaces(db, org)
    docs = [d for w in workspaces for d in repo.list_documents(db, w.id)]
    return {
        "org": repo.get_org(db, org).model_dump() if repo.get_org(db, org) else None,
        "workspaces": [w.model_dump() for w in workspaces],
        "documents": [d.model_dump() for d in docs],
        "conversations": [
            c.model_dump() for c in repo.list_conversations(db, org, principal.user_id)
        ],
        "usage_events": db.query("SELECT * FROM usage_events WHERE org_id = ?", (org,)),
        "audit": repo.recent_audit(db, org, limit=10000),
    }


@router.delete("/account")
def delete_account(principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    org = principal.org_id
    store = get_retriever().store

    # Purge vectors for every uploaded document in the org.
    purged = 0
    for ws in repo.list_workspaces(db, org):
        for doc in repo.list_documents(db, ws.id):
            purged += store.delete_by_doc_id(doc.id)

    # Messages are keyed by conversation, not org — purge them first.
    for conv in repo.list_conversations(db, org, principal.user_id):
        db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv.id,))
    for table in _TABLES:
        db.execute(f"DELETE FROM {table} WHERE org_id = ?", (org,))
    db.execute("DELETE FROM users WHERE org_id = ?", (org,))
    db.execute("DELETE FROM orgs WHERE id = ?", (org,))
    return {"deleted": True, "org_id": org, "chunks_purged": purged}
