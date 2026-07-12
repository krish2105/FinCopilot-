from fastapi.testclient import TestClient

import src.api.agent_routes as routes
from src.agents.orchestrator import AgentGraph
from src.api.main import app
from src.providers.router import ProviderRouter


def test_ask_endpoint(monkeypatch, settings, seeded_retriever):
    graph = AgentGraph(
        retriever=seeded_retriever, router=ProviderRouter(settings), settings=settings
    )
    monkeypatch.setattr(routes, "get_agent_graph", lambda: graph)
    client = TestClient(app)

    resp = client.post("/ask", json={"query": "Apple total net sales?", "tickers": ["AAPL"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "ok"
    assert body["citations"]
    assert body["answer"]
    assert "not investment advice" in body["disclaimer"].lower()


def test_ask_validation():
    client = TestClient(app)
    assert client.post("/ask", json={"query": ""}).status_code == 422
