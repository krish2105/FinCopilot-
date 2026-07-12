"""SaaS extras API (Phase 14): feedback, API keys, watchlists, export."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.auth.principal import Principal, get_principal, require_role
from src.db.database import get_db
from src.tenancy import repo, saas

router = APIRouter(tags=["saas"])


# ---- feedback ----
class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=-1, le=1)  # -1 down, +1 up
    message_id: str | None = None
    note: str = ""
    query: str = ""


@router.post("/feedback")
def submit_feedback(body: FeedbackRequest, principal: Principal = Depends(get_principal)) -> dict:
    fid = saas.add_feedback(
        get_db(),
        principal.org_id,
        principal.user_id,
        body.message_id,
        body.rating,
        body.note,
        body.query,
    )
    return {"id": fid, "recorded": True}


# ---- API keys ----
class CreateKey(BaseModel):
    name: str = Field("default", max_length=80)


@router.post("/api-keys")
def create_key(body: CreateKey, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "admin")
    raw, record = saas.create_api_key(get_db(), principal.org_id, body.name)
    return {"api_key": raw, **record, "note": "Store this key now — it won't be shown again."}


@router.get("/api-keys")
def list_keys(principal: Principal = Depends(get_principal)) -> dict:
    return {"keys": saas.list_api_keys(get_db(), principal.org_id)}


@router.delete("/api-keys/{key_id}")
def delete_key(key_id: str, principal: Principal = Depends(get_principal)) -> dict:
    saas.delete_api_key(get_db(), principal.org_id, key_id)
    return {"deleted": key_id}


# ---- watchlists (filing alerts) ----
class AddWatch(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=12)


@router.get("/watchlists")
def get_watchlists(principal: Principal = Depends(get_principal)) -> dict:
    return {"watchlists": saas.list_watchlists(get_db(), principal.org_id)}


@router.post("/watchlists")
def add_watch(body: AddWatch, principal: Principal = Depends(get_principal)) -> dict:
    return saas.add_watchlist(get_db(), principal.org_id, body.ticker)


@router.delete("/watchlists/{wl_id}")
def remove_watch(wl_id: str, principal: Principal = Depends(get_principal)) -> dict:
    saas.delete_watchlist(get_db(), principal.org_id, wl_id)
    return {"deleted": wl_id}


# ---- export a conversation as a cited report ----
@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: str, format: str = "md", principal: Principal = Depends(get_principal)
) -> PlainTextResponse:
    db = get_db()
    messages = repo.list_messages(db, conversation_id)
    if format == "csv":
        return PlainTextResponse(_to_csv(messages), media_type="text/csv")
    return PlainTextResponse(_to_markdown(messages), media_type="text/markdown")


def _to_markdown(messages) -> str:
    lines = ["# FinCopilot research export\n"]
    for m in messages:
        if m.role == "user":
            lines.append(f"## Q: {m.content}\n")
        else:
            lines.append(f"{m.content}\n")
            if m.answer_json:
                data = json.loads(m.answer_json)
                cites = data.get("citations", [])
                if cites:
                    lines.append("\n**Sources**\n")
                    for c in cites:
                        page = f" p.{c['page']}" if c.get("page") is not None else ""
                        lines.append(f"- {c['marker']} {c['ticker']} {c['doc_type']}{page}")
            lines.append("\n---\n")
    lines.append("\n_Informational research only — not investment advice._\n")
    return "\n".join(lines)


def _to_csv(messages) -> str:
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["role", "content", "verdict", "route"])
    for m in messages:
        verdict = route = ""
        if m.answer_json:
            data = json.loads(m.answer_json)
            verdict, route = data.get("verdict", ""), data.get("route", "")
        w.writerow([m.role, m.content, verdict, route])
    return buf.getvalue()
