import os

from src.ingestion.models import Chunk, DocType, SourceMetadata
from src.retrieval.bm25 import BM25Index


def _chunk(text: str, cid: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id="d1",
        text=text,
        metadata=SourceMetadata(ticker="ACME", doc_type=DocType.TEN_K, page=2),
    )


def test_build_query_and_persist(settings):
    path = os.path.join(settings.data_dir, "bm25.json")
    chunks = [
        _chunk("total revenue increased to one billion dollars", "c1"),
        _chunk("risk factors include foreign currency fluctuation", "c2"),
        _chunk("the board declared a quarterly dividend", "c3"),
    ]
    idx = BM25Index.build(chunks, path)
    assert len(idx) == 3
    assert os.path.exists(path)

    hits = idx.query("what was total revenue", k=2)
    assert hits[0].chunk_id == "c1"
    assert hits[0].metadata.page == 2


def test_load_roundtrip(settings):
    path = os.path.join(settings.data_dir, "bm25.json")
    BM25Index.build([_chunk("dividend declared by the board", "c1")], path)
    loaded = BM25Index.load(path)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded.query("dividend", k=1)[0].chunk_id == "c1"


def test_load_missing_returns_none(settings):
    assert BM25Index.load(os.path.join(settings.data_dir, "nope.json")) is None
