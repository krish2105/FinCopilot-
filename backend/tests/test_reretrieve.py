"""Re-retrieval-on-failure loop (Phase 22 core)."""

from src.agents.orchestrator import AgentGraph
from src.agents.schemas import FaithfulnessVerdict
from src.providers.router import ProviderRouter


def _graph(settings, seeded_retriever):
    return AgentGraph(
        retriever=seeded_retriever, router=ProviderRouter(settings), settings=settings
    )


def test_route_accepts_faithful(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    state = {"faithfulness": FaithfulnessVerdict(faithful=True), "retry_count": 0}
    assert g._route_after_verify(state) == "accept"


def test_route_retries_once_then_gives_up(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    unfaithful = FaithfulnessVerdict(faithful=False, reason="ungrounded")
    # first failure (retry_count incremented to 1) -> retry
    assert g._route_after_verify({"faithfulness": unfaithful, "retry_count": 1}) == "retry"
    # second failure (retry_count 2 > MAX_RERETRIEVE=1) -> give up
    assert g._route_after_verify({"faithfulness": unfaithful, "retry_count": 2}) == "giveup"


def test_grounded_query_still_accepts_end_to_end(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("What were Apple's total net sales?", tickers=["AAPL"])
    # Extractive answer is grounded -> no retry, verdict ok.
    assert ans.verdict == "ok"
    assert ans.faithfulness.faithful


def test_giveup_node_produces_refusal(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    out = g._giveup(
        {"faithfulness": FaithfulnessVerdict(faithful=False, reason="ungrounded figures")}
    )
    assert out["verdict"] == "insufficient_evidence"
    assert "re-retrieving" in out["answer"]
