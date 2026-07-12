"""Agent API (Phase 3): run the multi-agent graph and return a cited answer."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.agents.orchestrator import get_agent_graph
from src.agents.schemas import AgentAnswer

router = APIRouter(tags=["agents"])


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    tickers: list[str] | None = None


@router.post("/ask", response_model=AgentAnswer)
def ask(req: AskRequest) -> AgentAnswer:
    """Orchestrator → Researcher → Analyst → Compliance → (Viz → Synthesis | Refuse).

    Returns a fully-cited answer or an honest 'insufficient evidence' verdict,
    with the LLM provider trace for the audit log.
    """
    return get_agent_graph().run(req.query, tickers=req.tickers)
