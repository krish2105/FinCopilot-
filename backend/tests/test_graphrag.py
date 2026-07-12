from src.retrieval.graphrag import graphrag_retrieve


def test_which_companies_share_a_risk(seeded_graph, seeded_retriever):
    store = seeded_retriever.store
    res = graphrag_retrieve(seeded_graph, store, "Which companies share competition risk?", top_k=8)
    assert res.route == "graphrag"
    assert "AAPL" in res.answer and "MSFT" in res.answer
    assert res.chunks  # backing evidence hydrated from the store
    assert res.citations and res.citations[0].marker == "[1]"


def test_common_risks_between_two_companies(seeded_graph, seeded_retriever):
    res = graphrag_retrieve(
        seeded_graph, seeded_retriever.store, "What do Apple and Microsoft have in common?"
    )
    assert res.route == "graphrag"
    assert "competition" in res.answer.lower()
    assert res.chunks


def test_single_company_risks(seeded_graph, seeded_retriever):
    res = graphrag_retrieve(seeded_graph, seeded_retriever.store, "What risks does Apple disclose?")
    # 'disclose' isn't a relationship marker, but a company is named -> enumerate its risks.
    assert "AAPL" in res.answer
    assert "supply chain" in res.answer.lower()


def test_no_match_returns_empty(seeded_graph, seeded_retriever):
    res = graphrag_retrieve(seeded_graph, seeded_retriever.store, "hello world")
    assert res.chunks == []
