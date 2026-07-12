from fastapi.testclient import TestClient

import src.api.retrieval_routes as routes
from src.api.main import app


def test_retrieve_endpoint(monkeypatch, seeded_retriever):
    monkeypatch.setattr(routes, "get_retriever", lambda: seeded_retriever)
    client = TestClient(app)

    resp = client.post(
        "/retrieve", json={"query": "What were Apple's total net sales?", "top_k": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["route"] == "hybrid"
    assert body["chunks"]
    assert body["citations"][0]["marker"] == "[1]"
    assert "[1]" in body["answer"]


def test_retrieve_validation():
    client = TestClient(app)
    resp = client.post("/retrieve", json={"query": "", "top_k": 3})
    assert resp.status_code == 422  # empty query rejected


def test_retrieve_ticker_filter(monkeypatch, seeded_retriever):
    monkeypatch.setattr(routes, "get_retriever", lambda: seeded_retriever)
    client = TestClient(app)
    resp = client.post("/retrieve", json={"query": "total revenue", "tickers": ["AAPL"]})
    assert resp.status_code == 200
    assert all(c["metadata"]["ticker"] == "AAPL" for c in resp.json()["chunks"])
