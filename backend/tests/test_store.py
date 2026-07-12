import os

from src.ingestion.embed import Embedder
from src.ingestion.models import Chunk, DocType, SourceMetadata
from src.retrieval.store import LocalVectorStore


def _chunk(text: str, emb, cid: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id="d1",
        text=text,
        metadata=SourceMetadata(ticker="ACME", doc_type=DocType.TEN_K, page=1),
        embedding=emb,
    )


def _store(settings) -> LocalVectorStore:
    path = os.path.join(settings.data_dir, "v.sqlite")
    return LocalVectorStore(dim=384, embed_model="hash-embedder-v1", path=path)


def test_upsert_is_idempotent(settings):
    emb = Embedder(settings)
    store = _store(settings)
    chunks = [_chunk("revenue grew", emb.embed(["revenue grew"])[0], "c1")]
    store.upsert(chunks)
    store.upsert(chunks)  # second time must not duplicate
    assert store.count() == 1


def test_existing_ids(settings):
    emb = Embedder(settings)
    store = _store(settings)
    store.upsert([_chunk("a", emb.embed(["a"])[0], "c1")])
    assert store.existing_ids(["c1", "c2"]) == {"c1"}


def test_search_returns_nearest(settings):
    emb = Embedder(settings)
    store = _store(settings)
    texts = {
        "c1": "revenue and net income increased this year",
        "c2": "risk factors include supply chain disruption",
        "c3": "the cafeteria menu changed last week",
    }
    for cid, t in texts.items():
        store.upsert([_chunk(t, emb.embed([t])[0], cid)])

    q = emb.embed(["how did revenue and income change"])[0]
    hits = store.search(q, k=3)
    assert hits[0].chunk_id == "c1"
    assert hits[0].metadata.ticker == "ACME"


def test_dim_mismatch_rejected(settings):
    store = _store(settings)
    bad = _chunk("x", [0.0] * 10, "c1")  # wrong dim
    try:
        store.upsert([bad])
        raise AssertionError("expected dim mismatch error")
    except ValueError as e:
        assert "dim" in str(e).lower()
