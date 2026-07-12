"""End-to-end agent graph over the seeded corpus, in offline (stub) mode."""

from src.agents.orchestrator import AgentGraph
from src.providers.router import ProviderRouter


def _graph(settings, seeded_retriever, entity_graph=None):
    router = ProviderRouter(settings)  # offline settings -> stub mode
    assert router.mode == "stub"
    return AgentGraph(
        retriever=seeded_retriever,
        router=router,
        settings=settings,
        entity_graph=entity_graph,
    )


def test_factual_query_returns_cited_answer(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("What were Apple's total net sales?", tickers=["AAPL"])

    assert ans.verdict == "ok"
    assert ans.route == "hybrid"
    assert ans.answer
    assert ans.evidence_count > 0
    assert ans.citations and ans.citations[0].marker == "[1]"
    # Analyst produced cited findings from the evidence.
    assert all(f.citation_marker.startswith("[") for f in ans.findings)
    # Provider trace recorded (stub calls from analyze + synthesize).
    assert ans.provider_trace


def test_refusal_when_no_evidence(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("What are the results?", tickers=["ZZZZ"])  # no such ticker
    assert ans.verdict == "insufficient_evidence"
    assert "insufficient evidence" in ans.answer.lower()
    assert ans.evidence_count == 0
    assert ans.charts == []


def test_compliance_flags_surface(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("What risk factors are disclosed?", tickers=["AAPL"])
    # The seeded AAPL risk-factors chunk should trigger a risk_factors flag.
    assert ans.verdict == "ok"
    assert any(f.category == "risk_factors" for f in ans.flags)


def test_relationship_query_uses_graphrag(settings, seeded_retriever, seeded_graph):
    g = _graph(settings, seeded_retriever, entity_graph=seeded_graph)
    ans = g.run("Which companies share competition risk?")
    assert ans.planned_route == "relationship"
    assert ans.route == "graphrag"
    assert "AAPL" in ans.answer and "MSFT" in ans.answer
    assert ans.citations


def test_multi_hop_query_uses_agentic(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("Compare Apple net sales and Microsoft revenue")
    assert ans.planned_route == "multi_hop"
    assert ans.route == "agentic"
    assert ans.evidence_count > 0


def test_simple_query_uses_hybrid(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("What were Apple's total net sales?", tickers=["AAPL"])
    assert ans.planned_route == "simple"
    assert ans.route == "hybrid"
