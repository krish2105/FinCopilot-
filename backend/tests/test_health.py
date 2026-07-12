"""Phase 0 smoke tests: the app boots and config parses."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.config.settings import get_settings

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root_lists_tickers():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert "AAPL" in body["tickers"]
    assert "not investment advice" in body["disclaimer"].lower()


def test_settings_ticker_parsing():
    settings = get_settings()
    assert isinstance(settings.tickers, list)
    assert all(t == t.upper() for t in settings.tickers)
