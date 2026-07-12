"""Workspaces, document upload (data rooms), and conversation history (Phase 10)."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.auth.principal import Principal, get_principal
from src.billing.quota import enforce_document_quota
from src.db.database import get_db
from src.retrieval.retriever import get_retriever
from src.tenancy import repo

router = APIRouter(tags=["workspace"])


def _owned_workspace(db, principal: Principal, workspace_id: str):
    ws = repo.get_workspace(db, workspace_id)
    if not ws or ws.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


# ---- workspaces ----
class CreateWorkspace(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


@router.get("/workspaces")
def list_workspaces(principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    return {"workspaces": [w.model_dump() for w in repo.list_workspaces(db, principal.org_id)]}


@router.post("/workspaces")
def create_workspace(body: CreateWorkspace, principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    return repo.create_workspace(db, principal.org_id, body.name).model_dump()


# ---- documents ----
@router.get("/workspaces/{workspace_id}/documents")
def list_documents(workspace_id: str, principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    _owned_workspace(db, principal, workspace_id)
    return {"documents": [d.model_dump() for d in repo.list_documents(db, workspace_id)]}


@router.post("/workspaces/{workspace_id}/documents")
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
) -> dict:
    db = get_db()
    _owned_workspace(db, principal, workspace_id)
    org = repo.get_org(db, principal.org_id)
    enforce_document_quota(db, principal.org_id, org.plan if org else "free")

    filename = file.filename or "document"
    data = await file.read()
    doc = repo.create_document(
        db, principal.org_id, workspace_id, filename, filename.rsplit(".", 1)[-1], principal.user_id
    )

    # Stage the file, then run the ingestion job (async on RQ, else inline).
    from src.config.settings import get_settings
    from src.ingestion.jobs import ingest_document_job
    from src.ops.jobs import submit

    upload_dir = os.path.join(get_settings().data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, f"{doc.id}_{filename}")
    with open(path, "wb") as f:
        f.write(data)

    ran_async = submit(ingest_document_job, principal.org_id, workspace_id, doc.id, path, filename)
    # Re-read status: async -> 'processing' (frontend polls); inline -> ready/failed.
    fresh = repo.get_document(db, doc.id) or doc
    if not ran_async and fresh.status == "failed":
        repo.delete_document(db, doc.id)
        raise HTTPException(status_code=400, detail="Could not ingest the document.")
    return fresh.model_dump()


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    doc = repo.get_document(db, doc_id)
    if not doc or doc.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    repo.delete_document(db, doc_id)
    purged = get_retriever().store.delete_by_doc_id(doc_id)
    return {"deleted": doc_id, "chunks_purged": purged}


# ---- conversations ----
@router.get("/conversations")
def list_conversations(principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    convs = repo.list_conversations(db, principal.org_id, principal.user_id)
    return {"conversations": [c.model_dump() for c in convs]}


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    msgs = repo.list_messages(db, conversation_id)
    out = []
    for m in msgs:
        item = {"role": m.role, "content": m.content, "created_at": m.created_at}
        if m.answer_json:
            item["answer"] = json.loads(m.answer_json)
        out.append(item)
    return {"messages": out}
