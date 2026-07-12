from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.hybrid import hybrid_search
from src.retrieval.store import SearchHit


class _FakeStore:
    def __init__(self, hits):
        self._hits = hits

    def search(self, query_vec, k=8, tickers=None):
        return self._hits[:k]


class _FakeBM25:
    def __init__(self, hits):
        self._hits = hits

    def query(self, text, k=8, tickers=None):
        return self._hits[:k]


def _hit(cid, text="t"):
    md = SourceMetadata(ticker="AAPL", doc_type=DocType.TEN_K, page=1)
    return SearchHit(cid, 1.0, text, md)


def test_rrf_rewards_documents_in_both_lists():
    dense = [_hit("a"), _hit("b"), _hit("c")]
    bm25 = [_hit("b"), _hit("d"), _hit("e")]
    fused = hybrid_search([0.0], "q", _FakeStore(dense), _FakeBM25(bm25))
    # 'b' appears in both -> highest RRF score.
    assert fused[0].chunk_id == "b"
    assert fused[0].dense_rank is not None and fused[0].bm25_rank is not None


def test_union_of_candidates():
    dense = [_hit("a"), _hit("b")]
    bm25 = [_hit("c"), _hit("d")]
    fused = hybrid_search([0.0], "q", _FakeStore(dense), _FakeBM25(bm25))
    assert {c.chunk_id for c in fused} == {"a", "b", "c", "d"}


def test_works_without_bm25():
    dense = [_hit("a"), _hit("b")]
    fused = hybrid_search([0.0], "q", _FakeStore(dense), None)
    assert [c.chunk_id for c in fused] == ["a", "b"]
