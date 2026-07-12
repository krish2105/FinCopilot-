from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.citations import (
    assign_citations,
    build_extractive_answer,
)
from src.retrieval.types import RetrievedChunk


def _chunk(cid, text, ticker="AAPL", page=54, section="Item 8"):
    md = SourceMetadata(
        ticker=ticker,
        doc_type=DocType.TEN_K,
        title=f"{ticker} 10-K",
        source_url="https://sec.gov/x",
        page=page,
        section=section,
    )
    return RetrievedChunk(chunk_id=cid, text=text, metadata=md)


def test_assign_citations_numbers_in_order():
    chunks = [_chunk("a", "first"), _chunk("b", "second")]
    cites = assign_citations(chunks)
    assert [c.marker for c in cites] == ["[1]", "[2]"]
    assert chunks[0].marker == "[1]"
    assert cites[0].label() == "AAPL 10-K p.54 · Item 8"


def test_extractive_answer_is_cited():
    chunks = [
        _chunk("a", "Apple total net sales were 391 billion dollars in fiscal 2024."),
        _chunk("b", "Risk factors include foreign exchange volatility."),
    ]
    assign_citations(chunks)
    ans = build_extractive_answer("what were apple total net sales", chunks)
    assert "[1]" in ans
    assert "net sales" in ans.lower()


def test_empty_answer_is_insufficient_evidence():
    ans = build_extractive_answer("anything", [])
    assert "insufficient evidence" in ans.lower()
