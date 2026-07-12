import os

from src.retrieval.graph import EntityGraph


def test_graph_has_company_and_risk_nodes(seeded_graph):
    assert set(seeded_graph.companies()) == {"AAPL", "MSFT"}
    topics = seeded_graph.risk_topics()
    assert "competition" in topics
    assert "supply chain" in topics


def test_companies_facing_shared_risk(seeded_graph):
    # Both AAPL and MSFT disclose competition risk.
    companies = seeded_graph.companies_facing_risk("competition")
    assert companies == ["AAPL", "MSFT"]


def test_shared_risks_between_two(seeded_graph):
    assert seeded_graph.shared_risks("AAPL", "MSFT") == ["competition"]


def test_risks_for_company(seeded_graph):
    aapl = seeded_graph.risks_for_company("AAPL")
    assert "supply chain" in aapl
    assert "foreign exchange" in aapl


def test_match_risk_from_query(seeded_graph):
    assert "competition" in seeded_graph.match_risk("which companies share competition risk?")


def test_edge_evidence_has_citation_metadata(seeded_graph):
    ev = seeded_graph.edge_evidence("AAPL", "competition")
    assert ev
    assert ev[0]["chunk_id"]
    assert ev[0]["ticker"] == "AAPL"


def test_save_and_load_roundtrip(seeded_graph, settings):
    path = os.path.join(settings.data_dir, "roundtrip.json")
    seeded_graph.save(path)
    loaded = EntityGraph.load(path)
    assert loaded is not None
    assert loaded.companies_facing_risk("competition") == ["AAPL", "MSFT"]


def test_load_missing_returns_none(settings):
    assert EntityGraph.load(os.path.join(settings.data_dir, "nope.json")) is None
