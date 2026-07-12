from src.ingestion.embed import Embedder, resolve_backend


def test_resolve_backend_offline(settings):
    assert resolve_backend(settings) == "hash"


def test_hash_embedder_dim_and_determinism(settings):
    emb = Embedder(settings)
    assert emb.backend == "hash"
    assert emb.dim == 384
    v1 = emb.embed(["Apple revenue grew year over year"])
    v2 = emb.embed(["Apple revenue grew year over year"])
    assert len(v1[0]) == 384
    assert v1 == v2  # deterministic


def test_hash_embedder_is_normalized(settings):
    emb = Embedder(settings)
    v = emb.embed(["some financial text about revenue and margins"])[0]
    norm = sum(x * x for x in v) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_similar_texts_more_similar_than_unrelated(settings):
    emb = Embedder(settings)
    a, b, c = emb.embed(
        [
            "revenue and net income increased",
            "revenue and net income grew strongly",
            "the weather today is sunny and warm",
        ]
    )

    def cos(x, y):
        return sum(i * j for i, j in zip(x, y, strict=True))

    assert cos(a, b) > cos(a, c)


def test_empty_input(settings):
    assert Embedder(settings).embed([]) == []
