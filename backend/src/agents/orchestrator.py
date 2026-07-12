"""Orchestrator — the LangGraph state machine that runs the agent team.

Flow:
    research → analyze → comply → ┬─ (veto / no evidence) → refuse → END
                                  └─ visualize → synthesize → END

The Orchestrator never fabricates: it only composes verified pieces (retrieved
evidence, cited findings) and routes to an honest refusal when compliance vetoes
or no evidence was found. LLM synthesis uses the provider router with a
deterministic extractive fallback, so the graph runs live or fully offline.
"""

from __future__ import annotations

import logging
import time

from langgraph.graph import END, START, StateGraph

from src.agents import (
    analyst,
    classifier,
    compliance,
    faithfulness,
    researcher,
    visualization,
)
from src.agents.prompts import SYNTHESIS_SYSTEM, format_evidence, format_findings
from src.agents.schemas import AgentAnswer, FaithfulnessVerdict, ProviderCall
from src.agents.state import AgentState
from src.audit.log import AuditLog, AuditRecord, audit_path
from src.config.settings import Settings, get_settings
from src.providers.router import ProviderRouter, get_router
from src.retrieval import agentic, graphrag
from src.retrieval.graph import EntityGraph, graph_path
from src.retrieval.retriever import Retriever, get_retriever

logger = logging.getLogger(__name__)


class AgentGraph:
    def __init__(
        self,
        retriever: Retriever | None = None,
        router: ProviderRouter | None = None,
        settings: Settings | None = None,
        entity_graph: EntityGraph | None = None,
    ):
        self.settings = settings or get_settings()
        self.retriever = retriever or get_retriever()
        self.router = router or get_router()
        # May be None before the first ingestion; relationship route then falls
        # back to hybrid search.
        self.entity_graph = entity_graph or EntityGraph.load(graph_path())
        self.audit_log = AuditLog(audit_path(self.settings))
        self.graph = self._build()

    # --- graph wiring ---
    def _build(self):
        b = StateGraph(AgentState)
        b.add_node("classify", self._classify)
        b.add_node("research", self._research)
        b.add_node("analyze", self._analyze)
        b.add_node("comply", self._comply)
        b.add_node("visualize", self._visualize)
        b.add_node("synthesize", self._synthesize)
        b.add_node("verify", self._verify)
        b.add_node("refuse", self._refuse)

        b.add_edge(START, "classify")
        b.add_edge("classify", "research")
        b.add_edge("research", "analyze")
        b.add_edge("analyze", "comply")
        b.add_conditional_edges(
            "comply", self._route_after_comply, {"refuse": "refuse", "continue": "visualize"}
        )
        b.add_edge("visualize", "synthesize")
        b.add_edge("synthesize", "verify")  # Self-RAG faithfulness gate
        b.add_edge("verify", END)
        b.add_edge("refuse", END)
        return b.compile()

    # --- nodes ---
    def _classify(self, state: AgentState) -> dict:
        trace: list = []
        decision = classifier.classify(self.router, state["query"], trace)
        return {"planned_route": decision.route, "provider_trace": trace}

    def _research(self, state: AgentState) -> dict:
        query = state["query"]
        tickers = state.get("tickers")
        planned = state.get("planned_route", "simple")
        trace: list = []

        if planned == "relationship" and self.entity_graph is not None:
            result = graphrag.graphrag_retrieve(
                self.entity_graph, self.retriever.store, query, tickers, top_k=8
            )
            # Empty graph match -> fall back to hybrid so we still try to answer.
            if not result.chunks:
                result = researcher.research(self.retriever, query, tickers, top_k=6)
        elif planned == "multi_hop":
            result = agentic.agentic_retrieve(
                self.retriever, self.router, query, tickers, top_k=6, trace=trace
            )
        else:
            result = researcher.research(self.retriever, query, tickers, top_k=6)

        return {"retrieval": result, "route": result.route, "provider_trace": trace}

    def _analyze(self, state: AgentState) -> dict:
        trace: list = []
        out = analyst.analyze(self.router, state["query"], state.get("retrieval"), trace)
        return {"analyst": out, "provider_trace": trace}

    def _comply(self, state: AgentState) -> dict:
        out = compliance.check(state.get("retrieval"), state.get("analyst"))
        return {"compliance": out, "verdict": out.verdict}

    def _route_after_comply(self, state: AgentState) -> str:
        retrieval = state.get("retrieval")
        comp = state.get("compliance")
        if not retrieval or not retrieval.chunks:
            return "refuse"
        if comp and comp.verdict != "ok":
            return "refuse"
        return "continue"

    def _visualize(self, state: AgentState) -> dict:
        return {"viz": visualization.build(state.get("analyst"))}

    def _synthesize(self, state: AgentState) -> dict:
        trace: list = []
        retrieval = state["retrieval"]
        analyst_out = state.get("analyst")
        prompt = (
            f"Question: {state['query']}\n\n"
            f"Evidence:\n{format_evidence(retrieval)}\n\n"
            f"Analyst findings:\n{format_findings(analyst_out.findings if analyst_out else [])}\n\n"
            "Write a concise, fully-cited answer using only the evidence above."
        )
        answer = self.router.text(
            prompt,
            system=SYNTHESIS_SYSTEM,
            stub_text=retrieval.answer,  # Phase 2 extractive answer as offline fallback
            trace=trace,
        )
        return {"answer": answer, "verdict": "ok", "provider_trace": trace}

    def _verify(self, state: AgentState) -> dict:
        """Self-RAG gate: block the answer if any claim/number isn't grounded."""
        trace: list = []
        verdict = faithfulness.verify(
            self.router, state.get("answer", ""), state.get("retrieval"), trace
        )
        if verdict.faithful:
            return {"faithfulness": verdict, "provider_trace": trace}
        answer = (
            "I can't confidently answer from the retrieved sources — the drafted "
            f"answer failed the faithfulness check ({verdict.reason}). This is "
            "surfaced as insufficient evidence rather than risk an unsupported "
            "claim. Try narrowing the question or ingesting more documents."
        )
        return {
            "faithfulness": verdict,
            "answer": answer,
            "verdict": "insufficient_evidence",
            "provider_trace": trace,
        }

    def _refuse(self, state: AgentState) -> dict:
        comp = state.get("compliance")
        retrieval = state.get("retrieval")
        n = len(retrieval.chunks) if retrieval else 0
        reason = (
            comp.reason
            if comp and comp.reason
            else "the retrieved evidence does not support a confident answer."
        )
        answer = (
            "Insufficient evidence to answer this confidently. "
            f"Retrieved {n} source(s), but {reason} "
            "Try narrowing to a specific ticker/period, or ingest more documents."
        )
        return {"answer": answer, "verdict": "insufficient_evidence"}

    # --- run + assemble ---
    def run(self, query: str, tickers: list[str] | None = None) -> AgentAnswer:
        start = time.monotonic()
        final = self.graph.invoke({"query": query, "tickers": tickers, "provider_trace": []})
        latency_ms = int((time.monotonic() - start) * 1000)
        answer = self._to_answer(query, final, latency_ms)
        self._write_audit(answer, tickers)
        return answer

    def _to_answer(self, query: str, final: dict, latency_ms: int) -> AgentAnswer:
        retrieval = final.get("retrieval")
        analyst_out = final.get("analyst")
        comp = final.get("compliance")
        viz = final.get("viz")
        trace = [ProviderCall(**c) for c in final.get("provider_trace", [])]
        return AgentAnswer(
            query=query,
            route=final.get("route", "hybrid"),
            planned_route=final.get("planned_route", "simple"),
            verdict=final.get("verdict", "ok"),
            answer=final.get("answer", ""),
            citations=retrieval.citations if retrieval else [],
            findings=analyst_out.findings if analyst_out else [],
            flags=comp.flags if comp else [],
            charts=viz.charts if viz else [],
            provider_trace=trace,
            faithfulness=final.get("faithfulness") or FaithfulnessVerdict(),
            reranker=retrieval.reranker if retrieval else "",
            embed_backend=retrieval.embed_backend if retrieval else "",
            evidence_count=len(retrieval.chunks) if retrieval else 0,
            latency_ms=latency_ms,
        )

    def _write_audit(self, ans: AgentAnswer, tickers: list[str] | None) -> None:
        providers = sorted({f"{c.provider}:{c.model}" for c in ans.provider_trace})
        self.audit_log.record(
            AuditRecord(
                query=ans.query,
                tickers=tickers or [],
                planned_route=ans.planned_route,
                route=ans.route,
                verdict=ans.verdict,
                evidence_count=ans.evidence_count,
                sources=[c.label() for c in ans.citations],
                providers=providers,
                faithfulness_score=ans.faithfulness.score,
                latency_ms=ans.latency_ms,
            )
        )


_agent_graph: AgentGraph | None = None


def get_agent_graph() -> AgentGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = AgentGraph()
    return _agent_graph


def reset_agent_graph() -> None:
    global _agent_graph
    _agent_graph = None
