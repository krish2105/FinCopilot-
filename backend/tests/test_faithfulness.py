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
