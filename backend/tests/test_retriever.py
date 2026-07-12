"""End-to-end advanced-RAG retrieval over the seeded corpus."""


def test_factual_query_returns_cited_answer(seeded_retriever):
    result = seeded_retriever.retrieve("What were Apple's total net sales?", top_k=3)

    assert result.route == "hybrid"
    assert result.chunks
    # The Apple net-sales chunk should rank first.
    top = result.chunks[0]
    assert "net sales" in top.text.lower()
    assert top.metadata.ticker == "AAPL"
    # Answer is cited and grounded.
    assert result.citations
    assert result.citations[0].marker == "[1]"
    assert "[1]" in result.answer
    assert result.citations[0].page is not None  # page-level citation


def test_ticker_filter_excludes_others(seeded_retriever):
    result = seeded_retriever.retrieve("total revenue", tickers=["AAPL"], top_k=6)
    assert result.chunks
    assert all(c.metadata.ticker == "AAPL" for c in result.chunks)


def test_scores_present(seeded_retriever):
    result = seeded_retriever.retrieve("risk factors", top_k=3)
    for c in result.chunks:
        assert c.rrf_score > 0
        assert c.rerank_score is not None


def test_no_match_still_returns_structure(seeded_retriever):
    # A ticker with no documents -> no chunks, insufficient-evidence answer.
    result = seeded_retriever.retrieve("total revenue", tickers=["ZZZZ"], top_k=3)
    assert result.chunks == []
    assert "insufficient evidence" in result.answer.lower()
