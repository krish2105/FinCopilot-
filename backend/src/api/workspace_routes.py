"""Workspaces, document upload (data rooms), and conversation history (Phase 10)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.auth.principal import Principal, get_principal
from src.db.database import get_db
from src.ingestion.upload import UploadError, ingest_upload
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
    data = await file.read()
    doc = repo.create_document(
        db,
        principal.org_id,
        workspace_id,
        file.filename or "document",
        (file.filename or "").rsplit(".", 1)[-1],
        principal.user_id,
    )
    try:
        n = ingest_upload(
            get_retriever(),
            principal.org_id,
            workspace_id,
            doc.id,
            file.filename or "document",
            data,
        )
    except UploadError as exc:
        repo.delete_document(db, doc.id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repo.finalize_document(db, doc.id, n)
    doc.status = "ready"
    doc.chunk_count = n
    return doc.model_dump()


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    doc = repo.get_document(db, doc_id)
    if not doc or doc.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    repo.delete_document(db, doc_id)
    # Note: chunk purge from the vector store is a background job (Phase 12); the
    # record is removed immediately so it no longer appears in the data room.
    return {"deleted": doc_id}


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
