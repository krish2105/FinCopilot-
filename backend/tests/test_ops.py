import os

import pytest
from fastapi import HTTPException

from src.agents.schemas import AgentAnswer, ProviderCall
from src.db.database import Database
from src.ingestion.embed import Embedder
from src.ingestion.models import Chunk, DocType, SourceMetadata
from src.ops.ratelimit import RateLimiter
from src.retrieval.store import LocalVectorStore
from src.retrieval.types import Citation
from src.tenancy import repo


def test_rate_limiter_blocks_over_limit():
    rl = RateLimiter(per_minute=2)
    rl.check("k")  # 1
    rl.check("k")  # 2
    with pytest.raises(HTTPException) as exc:
        rl.check("k")  # 3 -> blocked
    assert exc.value.status_code == 429
    rl.check("other")  # different key unaffected


def test_rate_limiter_disabled_when_zero():
    rl = RateLimiter(per_minute=0)
    for _ in range(100):
        rl.check("k")  # never raises


def test_delete_by_doc_id_purges_chunks(settings):
    emb = Embedder(settings)
    store = LocalVectorStore(emb.dim, emb.name, os.path.join(settings.data_dir, "v.sqlite"))
    md = SourceMetadata(ticker="DOC", doc_type=DocType.UPLOAD, workspace_id="ws1")
    store.upsert(
        [
            Chunk(
                chunk_id="c1",
                doc_id="doc1",
                text="hello world",
                metadata=md,
                embedding=emb.embed(["x"])[0],
            )
        ]
    )
    assert store.count() == 1
    assert store.delete_by_doc_id("doc1") == 1
    assert store.count() == 0


def _answer(query: str) -> AgentAnswer:
    return AgentAnswer(
        query=query,
        route="hybrid",
        planned_route="simple",
        verdict="ok",
        answer="cited answer [1]",
        citations=[Citation(marker="[1]", ticker="AAPL", doc_type="10-K", page=1)],
        provider_trace=[ProviderCall(provider="stub", model="stub-llm-v1")],
        evidence_count=1,
        latency_ms=12,
    )


def test_audit_is_tenant_scoped(settings):
    db = Database(None, settings.data_dir)
    repo.write_audit(db, "orgA", "u1", _answer("q1"), ["AAPL"])
    repo.write_audit(db, "orgB", "u2", _answer("q2"), None)

    a = repo.recent_audit(db, "orgA")
    assert len(a) == 1 and a[0]["query"] == "q1"
    assert a[0]["tickers"] == ["AAPL"]
    assert a[0]["sources"]  # citation label captured
    assert repo.audit_count(db, "orgB") == 1
    # Org A never sees Org B's audit rows.
    assert all(r["query"] != "q2" for r in repo.recent_audit(db, "orgA"))
