"""Phase 44: reranker, adaptive-k, evidence ordering, safe query expansion,
and corpus-aligned embedding config."""

from src.agents.prompts import order_for_context
from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.expansion import expand, is_numeric_query, normalize_vocabulary
from src.retrieval.reranker import adaptive_k
from src.retrieval.types import RetrievedChunk


def _chunk(i: int, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(i),
        text=f"chunk {i}",
        metadata=SourceMetadata(ticker="AAPL", doc_type=DocType.TEN_K),
        rrf_score=0.5,
        rerank_score=score,
    )


# --- adaptive-k --------------------------------------------------------------
def test_adaptive_k_cuts_at_the_relevance_cliff():
    # two strong hits, then the score falls off a cliff -> keep the strong ones (+buffer)
    chunks = [_chunk(0, 9.0), _chunk(1, 8.5), _chunk(2, -6.0), _chunk(3, -7.0), _chunk(4, -8.0)]
    kept = adaptive_k(chunks, top_k=5)
    assert len(kept) < 5, "should drop the distractors after the cliff"
    assert kept[0].rerank_score == 9.0


def test_adaptive_k_keeps_everything_when_all_are_relevant():
    chunks = [_chunk(i, 9.0 - i * 0.1) for i in range(6)]  # no cliff
    assert len(adaptive_k(chunks, top_k=6)) == 6


def test_adaptive_k_never_starves_the_answer():
    chunks = [_chunk(0, 9.0), _chunk(1, -9.0), _chunk(2, -9.1), _chunk(3, -9.2)]
    assert len(adaptive_k(chunks, top_k=4)) >= 3, "always keep a floor of evidence"


# --- evidence ordering -------------------------------------------------------
def test_order_for_context_puts_best_at_both_ends():
    chunks = [_chunk(i, 9.0 - i) for i in range(5)]  # best-first
    out = order_for_context(chunks)
    assert out[0].chunk_id == "0", "rank 1 leads"
    assert out[-1].chunk_id == "1", "rank 2 closes"
    assert out[2].chunk_id == "4", "the weakest lands in the middle"
    assert {c.chunk_id for c in out} == {"0", "1", "2", "3", "4"}, "nothing lost"


def test_order_for_context_noop_for_short_lists():
    chunks = [_chunk(0, 1.0), _chunk(1, 0.5)]
    assert order_for_context(chunks) == chunks


# --- safe query expansion ----------------------------------------------------
def test_numeric_queries_are_detected():
    assert is_numeric_query("What was Apple's total revenue in FY24?")
    assert not is_numeric_query("How does Apple describe competition?")


def test_vocabulary_normalisation_speaks_filing_dialect():
    terms = normalize_vocabulary("What was Apple revenue in FY24?")
    assert "net sales" in terms, "filings say 'net sales', not 'revenue'"
    assert "fiscal 2024" in terms, "FY24 must expand to the filing's wording"


def test_quarter_normalisation():
    terms = normalize_vocabulary("Q3 FY25 operating margin")
    assert "third quarter" in terms
    assert "fiscal 2025" in terms


def test_numeric_query_never_gets_generative_expansion():
    """HyDE-style expansion hallucinates figures into the query and measurably HURTS
    financial retrieval. A numeric question must only ever be expanded lexically."""

    class ExplodingRouter:
        mode = "live"

        def text(self, *a, **k):  # pragma: no cover - must never be called
            raise AssertionError("generative expansion ran on a numeric query")

    out = expand("What was Apple's total revenue in FY24?", router=ExplodingRouter())
    assert "net sales" in out  # lexical expansion still happened
