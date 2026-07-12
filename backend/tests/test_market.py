"""Phase 25: live market-data endpoints (quotes / history / earnings).

Providers hit the network, so we monkeypatch the service layer and assert the
route contract: 200 with the payload when data exists, 404 when it doesn't,
400 on a bad range. Also covers the in-process TTL cache and NaN coercion.
"""

from fastapi.testclient import TestClient

from src.api.main import app
from src.market import quotes

client = TestClient(app)

_QUOTE = {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "price": 212.5,
    "previous_close": 210.0,
    "change": 2.5,
    "change_pct": 1.19,
    "currency": "USD",
    "market_cap": 3.2e12,
    "day_high": 213.0,
    "day_low": 209.5,
    "volume": 5.1e7,
    "pe": 33.4,
    "fifty_two_week_high": 260.1,
    "fifty_two_week_low": 164.0,
    "exchange": "NASDAQ",
    "sector": "Technology",
    "source": "test",
}


def test_quote_ok(monkeypatch):
    monkeypatch.setattr(quotes, "get_quote", lambda t: {**_QUOTE, "ticker": t.upper()})
    resp = client.get("/market/quote/aapl")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert body["price"] == 212.5
    assert body["change_pct"] == 1.19


def test_quote_404_when_none(monkeypatch):
    monkeypatch.setattr(quotes, "get_quote", lambda t: None)
    assert client.get("/market/quote/ZZZZ").status_code == 404


def test_history_ok(monkeypatch):
    payload = {
        "ticker": "MSFT",
        "range": "1M",
        "points": [{"x": "2026-06-01", "y": 400.0}, {"x": "2026-07-01", "y": 420.0}],
        "change_pct": 5.0,
        "source": "test",
    }
    monkeypatch.setattr(quotes, "get_history", lambda t, r: payload)
    resp = client.get("/market/history/msft?range=1M")
    assert resp.status_code == 200
    assert resp.json()["points"][0]["y"] == 400.0


def test_history_bad_range():
    assert client.get("/market/history/aapl?range=10Y").status_code == 400


def test_history_404_when_none(monkeypatch):
    monkeypatch.setattr(quotes, "get_history", lambda t, r: None)
    assert client.get("/market/history/aapl?range=1Y").status_code == 404


def test_earnings_ok(monkeypatch):
    payload = {
        "ticker": "AAPL",
        "next_date": "2026-10-30",
        "history": [
            {"date": "2026-05-01", "eps_estimate": 1.5, "eps_reported": 1.6, "surprise_pct": 6.7}
        ],
        "source": "test",
    }
    monkeypatch.setattr(quotes, "get_earnings", lambda t: payload)
    resp = client.get("/market/earnings/aapl")
    assert resp.status_code == 200
    assert resp.json()["next_date"] == "2026-10-30"


def test_float_coercion_handles_nan_and_junk():
    assert quotes._f(float("nan")) is None
    assert quotes._f("not-a-number") is None
    assert quotes._f(None) is None
    assert quotes._f("12.5") == 12.5


def test_cache_returns_memoized_value():
    quotes._CACHE.clear()
    calls = {"n": 0}

    def _fn():
        calls["n"] += 1
        return {"v": calls["n"]}

    a = quotes._cached("k", 60.0, _fn)
    b = quotes._cached("k", 60.0, _fn)
    assert a == b == {"v": 1}
    assert calls["n"] == 1  # second call served from cache
