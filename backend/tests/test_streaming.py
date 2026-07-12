import json

from fastapi.testclient import TestClient

import src.api.agent_routes as routes
from src.agents.orchestrator import AgentGraph
from src.agents.schemas import AgentAnswer
from src.api.main import app
from src.providers.router import ProviderRouter


def _graph(settings, seeded_retriever):
    return AgentGraph(
        retriever=seeded_retriever, router=ProviderRouter(settings), settings=settings
    )


def test_stream_emits_steps_and_answer(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    events = list(g.stream("What were Apple's total net sales?", tickers=["AAPL"]))
    kinds = [e["event"] for e in events]
    assert "step" in kinds
    assert "token" in kinds
    answers = [e for e in events if e["event"] == "answer"]
    assert len(answers) == 1
    assert isinstance(answers[0]["answer"], AgentAnswer)
    # steps cover the pipeline
    steps = [e["node"] for e in events if e["event"] == "step"]
    assert "classify" in steps and "research" in steps


def test_ask_stream_endpoint(monkeypatch, settings, seeded_retriever):
    monkeypatch.setattr(routes, "get_agent_graph", lambda: _graph(settings, seeded_retriever))
    client = TestClient(app)
    resp = client.post("/ask/stream", json={"query": "Apple net sales?", "tickers": ["AAPL"]})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = []
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    kinds = {e["event"] for e in events}
    assert {"step", "answer", "done"} <= kinds
    answer_ev = next(e for e in events if e["event"] == "answer")
    assert answer_ev["answer"]["citations"]


def test_token_usage_recorded_in_trace(settings, seeded_retriever):
    g = _graph(settings, seeded_retriever)
    ans = g.run("What were Apple's total net sales?", tickers=["AAPL"])
    # Stub estimates tokens; every provider call carries a token count.
    assert all(p.tokens >= 0 for p in ans.provider_trace)
    assert sum(p.tokens for p in ans.provider_trace) > 0
