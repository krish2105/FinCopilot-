from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.reranker import Reranker, resolve_rerank_backend
from src.retrieval.types import RetrievedChunk


def _chunk(cid, text):
    md = SourceMetadata(ticker="AAPL", doc_type=DocType.TEN_K, page=1)
    return RetrievedChunk(chunk_id=cid, text=text, metadata=md, rrf_score=0.1)


def test_offline_resolves_to_lexical(settings):
    assert resolve_rerank_backend(settings) == "lexical"


def test_lexical_reranker_prefers_relevant(settings):
    r = Reranker(settings)
    chunks = [
        _chunk("noise", "The cafeteria menu changed and the parking lot repaved."),
        _chunk("target", "Total net sales and revenue increased in fiscal 2024."),
    ]
    ranked = r.rerank("what were total net sales and revenue", chunks, top_k=2)
    assert ranked[0].chunk_id == "target"
    assert ranked[0].rerank_score >= ranked[1].rerank_score


def test_rerank_respects_top_k(settings):
    r = Reranker(settings)
    chunks = [_chunk(str(i), f"revenue figure number {i}") for i in range(5)]
    assert len(r.rerank("revenue", chunks, top_k=3)) == 3


def test_rerank_empty(settings):
    assert Reranker(settings).rerank("q", [], top_k=3) == []
