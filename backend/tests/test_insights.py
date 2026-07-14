"""Phase 40: the insight layer — proactive findings rather than answers to questions."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.insights import service
from src.insights.schemas import PortfolioOverlap

client = TestClient(app)


class _FakeGraph:
    """Minimal stand-in for EntityGraph."""

    def __init__(self, mapping: dict[str, list[str]]):
        self._m = mapping

    def risks_for_company(self, ticker: str) -> list[str]:
        return self._m.get(ticker.upper(), [])


def test_portfolio_overlap_finds_shared_concentration():
    graph = _FakeGraph(
        {
            "AAPL": ["supply_chain", "competition", "regulation"],
            "MSFT": ["competition", "regulation"],
            "NVDA": ["supply_chain", "competition"],
        }
    )
    out = service.portfolio_overlap(graph, ["AAPL", "MSFT", "NVDA"])
    topics = {s.topic: s for s in out.shared_risks}

    # competition is in all three -> 100% concentration and ranked first
    assert topics["competition"].concentration == 1.0
    assert out.shared_risks[0].topic == "competition"
    # supply_chain in 2 of 3
    assert topics["supply_chain"].companies == ["AAPL", "NVDA"]
    assert round(topics["supply_chain"].concentration, 2) == 0.67
    assert "competition" in out.summary


def test_portfolio_overlap_needs_two_holdings():
    out = service.portfolio_overlap(_FakeGraph({}), ["AAPL"])
    assert out.shared_risks == []
    assert "at least two" in out.summary


def test_portfolio_overlap_reports_no_shared_risk():
    graph = _FakeGraph({"AAPL": ["supply_chain"], "JPM": ["credit"]})
    out = service.portfolio_overlap(graph, ["AAPL", "JPM"])
    assert out.shared_risks == []
    assert "No risk topic is shared" in out.summary


def test_portfolio_endpoint(monkeypatch):
    monkeypatch.setattr(
        service,
        "portfolio_overlap",
        lambda g, t: PortfolioOverlap(tickers=t, summary="ok"),
    )
    r = client.post("/insights/portfolio", json={"tickers": ["AAPL", "MSFT"]})
    assert r.status_code == 200
    assert r.json()["summary"] == "ok"


def test_peers_endpoint_requires_tickers():
    assert client.get("/insights/peers?tickers=").status_code == 400


def test_fundamentals_404_without_data(monkeypatch):
    from src.market import quotes

    monkeypatch.setattr(quotes, "get_fundamentals", lambda t, years=5: None)
    assert client.get("/insights/fundamentals/AAPL").status_code == 404


def test_red_flags_reports_clean_when_nothing_found(monkeypatch):
    from src.insights.schemas import RedFlagReport

    monkeypatch.setattr(
        service, "red_flags", lambda r, t: RedFlagReport(ticker=t.upper(), clean=True)
    )
    r = client.get("/insights/red-flags/AAPL")
    assert r.status_code == 200
    assert r.json()["clean"] is True
