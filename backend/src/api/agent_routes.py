"""Agent API (Phase 3+): run the multi-agent graph and return a cited answer.

Phase 10: scoped to the caller's tenant — retrieval spans the shared public corpus
plus the caller's own workspaces (or a specific data room), and the exchange is
persisted to the conversation history.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.orchestrator import get_agent_graph
from src.agents.schemas import AgentAnswer
from src.auth.principal import Principal, get_principal
from src.billing.quota import enforce_query_quota
from src.db.database import get_db
from src.ops.ratelimit import get_limiter
from src.tenancy import repo

router = APIRouter(tags=["agents"])


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    tickers: list[str] | None = None
    workspace_id: str | None = None  # restrict to a specific data room
    conversation_id: str | None = None  # append to an existing conversation


@router.post("/ask", response_model=AgentAnswer)
def ask(req: AskRequest, principal: Principal = Depends(get_principal)) -> AgentAnswer:
    """Orchestrator → Researcher → Analyst → Compliance → (Viz → Synthesis | Refuse)
    → Self-RAG gate, scoped to the caller's accessible workspaces."""
    db = get_db()
    get_limiter().check(principal.user_id)

    # Enforce the org's monthly query quota before doing expensive work.
    org = repo.get_org(db, principal.org_id)
    enforce_query_quota(db, principal.org_id, org.plan if org else "free")

    # Resolve the workspace scope (always includes the shared public corpus).
    scope = _resolve_scope(db, principal, req)
    answer = get_agent_graph().run(req.query, tickers=req.tickers, workspaces=scope)

    _persist(db, principal, req, answer)
    return answer


def _resolve_scope(db, principal: Principal, req: AskRequest) -> list[str]:
    if req.workspace_id:
        ws = repo.get_workspace(db, req.workspace_id)
        if not ws or ws.org_id != principal.org_id:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return [req.workspace_id, repo.PUBLIC_WORKSPACE]
    return repo.accessible_workspace_ids(db, principal.org_id)


@router.post("/ask/stream")
def ask_stream(req: AskRequest, principal: Principal = Depends(get_principal)) -> StreamingResponse:
    """Server-Sent Events: agent-step events, streamed answer tokens, then the
    full cited AgentAnswer. Same tenant scoping, quota, and persistence as /ask."""
    db = get_db()
    get_limiter().check(principal.user_id)
    org = repo.get_org(db, principal.org_id)
    enforce_query_quota(db, principal.org_id, org.plan if org else "free")
    scope = _resolve_scope(db, principal, req)

    def gen():
        answer: AgentAnswer | None = None
        for ev in get_agent_graph().stream(req.query, tickers=req.tickers, workspaces=scope):
            if ev["event"] == "answer":
                answer = ev["answer"]
                payload = {"event": "answer", "answer": answer.model_dump()}
            else:
                payload = ev
            yield f"data: {json.dumps(payload)}\n\n"
        if answer is not None:
            _persist(db, principal, req, answer)
        yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _persist(db, principal: Principal, req: AskRequest, answer: AgentAnswer) -> None:
    conv_id = req.conversation_id
    if not conv_id:
        ws = req.workspace_id or repo.PUBLIC_WORKSPACE
        conv = repo.create_conversation(db, principal.org_id, ws, principal.user_id, req.query)
        conv_id = conv.id
    repo.add_message(db, conv_id, "user", req.query)
    repo.add_message(db, conv_id, "assistant", answer.answer, answer.model_dump_json())

    # Usage event (Phase 11 quotas) + tenant-scoped audit trail (Phase 12).
    import uuid
    from datetime import UTC, datetime

    tokens = sum(p.tokens for p in answer.provider_trace)  # real token usage
    db.execute(
        "INSERT INTO usage_events (id, org_id, user_id, ts, kind, tokens, providers) "
        "VALUES (?, ?, ?, ?, 'query', ?, ?)",
        (
            f"use_{uuid.uuid4().hex[:16]}",
            principal.org_id,
            principal.user_id,
            datetime.now(UTC).isoformat(),
            tokens,
            ",".join(sorted({p.provider for p in answer.provider_trace})),
        ),
    )
    repo.write_audit(db, principal.org_id, principal.user_id, answer, req.tickers)
