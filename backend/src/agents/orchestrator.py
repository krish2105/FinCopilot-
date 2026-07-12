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
from src.config.settings import Settings, get_settings
from src.ops.observability import span
from src.providers.router import ProviderRouter, get_router
from src.retrieval import agentic, graphrag
from src.retrieval.graph import EntityGraph, graph_path
from src.retrieval.retriever import Retriever, get_retriever
from src.security.injection import wrap_untrusted

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
        b.add_node("giveup", self._giveup)
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
        # On failure, loop back to broaden retrieval (bounded); else accept or give up.
        b.add_conditional_edges(
            "verify",
            self._route_after_verify,
            {"accept": END, "retry": "research", "giveup": "giveup"},
        )
        b.add_edge("giveup", END)
        b.add_edge("refuse", END)
        return b.compile()

    MAX_RERETRIEVE = 1

    # --- nodes ---
    def _classify(self, state: AgentState) -> dict:
        trace: list = []
        decision = classifier.classify(self.router, state["query"], trace)
        return {"planned_route": decision.route, "provider_trace": trace}

    def _research(self, state: AgentState) -> dict:
        query = state["query"]
        # On a re-retrieval attempt, broaden: more candidates and drop the ticker
        # filter so the second pass has a better chance of grounding the answer.
        broadened = state.get("retry_count", 0) > 0
        tickers = None if broadened else state.get("tickers")
        top_k = 10 if broadened else 6
        workspaces = state.get("workspaces")
        planned = state.get("planned_route", "simple")
        trace: list = []

        with span("agent.research", route=planned, broadened=broadened):
            if planned == "relationship" and self.entity_graph is not None:
                result = graphrag.graphrag_retrieve(
                    self.entity_graph, self.retriever.store, query, tickers, top_k=8
                )
                # Empty graph match -> fall back to hybrid so we still try to answer.
                if not result.chunks:
                    result = researcher.research(
                        self.retriever, query, tickers, top_k=top_k, workspaces=workspaces
                    )
            elif planned == "multi_hop":
                result = agentic.agentic_retrieve(
                    self.retriever,
                    self.router,
                    query,
                    tickers,
                    top_k=top_k,
                    trace=trace,
                    workspaces=workspaces,
                )
            else:
                result = researcher.research(
                    self.retriever, query, tickers, top_k=top_k, workspaces=workspaces
                )

        return {"retrieval": result, "route": result.route, "provider_trace": trace}

    def _analyze(self, state: AgentState) -> dict:
        with span("agent.analyze"):
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
        with span("agent.synthesize"):
            trace: list = []
            retrieval = state["retrieval"]
            analyst_out = state.get("analyst")
            prompt = (
                f"Question: {state['query']}\n\n"
                f"Evidence:\n{wrap_untrusted(format_evidence(retrieval))}\n\n"
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
        """Self-RAG gate: verify grounding. On failure the graph may loop back to
        re-retrieve (broadened) before giving up — the re-retrieval-on-failure
        pattern that keeps unsupported answers from slipping through."""
        with span("agent.verify"):
            trace: list = []
            verdict = faithfulness.verify(
                self.router, state.get("answer", ""), state.get("retrieval"), trace
            )
            out: dict = {"faithfulness": verdict, "provider_trace": trace}
            if not verdict.faithful:
                out["retry_count"] = state.get("retry_count", 0) + 1
            return out

    def _route_after_verify(self, state: AgentState) -> str:
        v = state.get("faithfulness")
        if v and v.faithful:
            return "accept"
        if state.get("retry_count", 0) <= self.MAX_RERETRIEVE:
            return "retry"
        return "giveup"

    def _giveup(self, state: AgentState) -> dict:
        verdict = state.get("faithfulness")
        reason = verdict.reason if verdict else "the drafted answer was not grounded."
        answer = (
            "I can't confidently answer from the retrieved sources — after "
            f"re-retrieving, the answer still failed the faithfulness check ({reason}). "
            "This is surfaced as insufficient evidence rather than risk an unsupported "
            "claim. Try narrowing the question or ingesting more documents."
        )
        return {"answer": answer, "verdict": "insufficient_evidence"}

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
    def run(
        self,
        query: str,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> AgentAnswer:
        start = time.monotonic()
        final = self.graph.invoke(
            {
                "query": query,
                "tickers": tickers,
                "workspaces": workspaces,
                "provider_trace": [],
                "retry_count": 0,
            }
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        return self._to_answer(query, final, latency_ms)

    _STEP_LABELS = {
        "classify": "Classifying & routing",
        "research": "Researching evidence",
        "analyze": "Analyzing figures",
        "comply": "Checking compliance",
        "visualize": "Building visualization",
        "synthesize": "Synthesizing answer",
        "verify": "Verifying faithfulness",
        "refuse": "Insufficient evidence",
    }

    def stream(self, query: str, tickers=None, workspaces=None):
        """Generator of SSE events: one 'step' per agent node, streamed answer
        tokens, then a final 'answer' with the full AgentAnswer.

        (Live per-token LLM streaming is a further enhancement; here we stream the
        synthesized answer word-by-word for a responsive UX in every mode.)"""
        start = time.monotonic()
        acc: dict = {
            "query": query,
            "tickers": tickers,
            "workspaces": workspaces,
            "provider_trace": [],
            "retry_count": 0,
        }
        for update in self.graph.stream(acc, stream_mode="updates"):
            for node, delta in update.items():
                label = self._STEP_LABELS.get(node, node)
                yield {"event": "step", "node": node, "label": label}
                for k, v in (delta or {}).items():
                    if k == "provider_trace":
                        acc["provider_trace"] = acc.get("provider_trace", []) + (v or [])
                    else:
                        acc[k] = v

        latency_ms = int((time.monotonic() - start) * 1000)
        answer = self._to_answer(query, acc, latency_ms)
        for word in answer.answer.split(" "):
            yield {"event": "token", "text": word + " "}
        yield {"event": "answer", "answer": answer}

    def _to_answer(self, query: str, final: dict, latency_ms: int) -> AgentAnswer:
        retrieval = final.get("retrieval")
        analyst_out = final.get("analyst")
        comp = final.get("compliance")
        viz = final.get("viz")
        trace = [ProviderCall(**c) for c in final.get("provider_trace", [])]
        from src.billing.pricing import estimate_cost

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
            cost_usd=estimate_cost(trace),
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
