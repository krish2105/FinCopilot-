from src.agents.faithfulness import verify
from src.config.settings import Settings
from src.ingestion.models import DocType, SourceMetadata
from src.providers.router import ProviderRouter
from src.retrieval.types import RetrievalResult, RetrievedChunk


def _result(texts):
    chunks = []
    for i, t in enumerate(texts):
        md = SourceMetadata(ticker="AAPL", doc_type=DocType.TEN_K, page=i + 1, section="Item 7")
        chunks.append(RetrievedChunk(chunk_id=f"c{i}", text=t, metadata=md, marker=f"[{i + 1}]"))
    return RetrievalResult(query="q", chunks=chunks)


def _router():
    return ProviderRouter(Settings(fincopilot_offline_mode=True))  # stub mode


def test_grounded_answer_is_faithful():
    res = _result(["Apple total net sales were $391,035 million in fiscal 2024."])
    v = verify(_router(), "Apple total net sales were $391,035 million. [1]", res)
    assert v.faithful
    assert v.score == 1.0


def test_hallucinated_number_is_blocked():
    res = _result(["Apple total net sales were $391,035 million in fiscal 2024."])
    v = verify(_router(), "Apple total net sales were $999,999 million. [1]", res)
    assert not v.faithful
    assert v.ungrounded_numbers
    assert "999" in v.ungrounded_numbers[0]


def test_unsupported_uncited_statement_flagged():
    res = _result(["Apple reported revenue growth driven by iPhone sales."])
    v = verify(_router(), "The company plans to acquire a rocket manufacturer next year.", res)
    assert not v.faithful
    assert v.unsupported_claims


def test_empty_answer_unfaithful():
    assert not verify(_router(), "", _result(["x"])).faithful


def test_no_evidence_unfaithful():
    assert not verify(_router(), "Some answer.", RetrievalResult(query="q")).faithful


# --- Phase 39: materiality-aware gate -----------------------------------------
# The gate used to refuse 56% of FinanceBench answers because a conservative judge
# flagged one prose sentence and a binary rule discarded the whole cited answer.
# Now: figures and arithmetic refuse unconditionally; prose doubt is only fatal when
# it overwhelms the answer.
from src.agents.faithfulness import _decide  # noqa: E402


def test_prose_doubt_does_not_discard_a_cited_answer():
    v = _decide(
        ["Both firms cite competition risk [1][2].", "Neither quantifies it."],
        ["Neither quantifies it."],
        [],
        [],
    )
    assert v.faithful, "a single prose doubt must not refuse a cited synthesis"


def test_flagged_claim_carrying_a_figure_still_refuses():
    v = _decide(
        ["Revenue was $391,035 million [1].", "Margins improved."],
        ["Revenue was $391,035 million [1]."],
        [],
        [],
    )
    assert not v.faithful, "an unsupported claim containing a figure is material"


def test_ungrounded_number_always_refuses():
    v = _decide(["Revenue was $999,999 million."], [], ["$999,999 million"], [])
    assert not v.faithful


def test_bad_arithmetic_always_refuses():
    err = "arithmetic error: 100 + 100 = 250 (correct: 200.0)"
    v = _decide(["100 + 100 = 250."], [err], [], [err])
    assert not v.faithful


def test_overwhelmingly_unsupported_answer_refuses():
    v = _decide(["A.", "B.", "C."], ["A.", "B.", "C."], [], [])
    assert not v.faithful, "if nearly everything is unsupported, refuse"
