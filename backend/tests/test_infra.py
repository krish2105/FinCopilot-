"""Phase 16/17/18 infra: job queue (inline fallback), tracing no-op, tenant ctx."""

import os


def test_jobs_run_inline_without_redis(settings):
    from src.ops.jobs import is_async, submit

    calls = []
    ran_async = submit(lambda a, b: calls.append((a, b)), 1, 2, settings=settings)
    assert ran_async is False
    assert calls == [(1, 2)]
    assert is_async(settings) is False


def test_span_is_noop_offline():
    from src.ops.observability import span

    with span("agent.research", route="simple") as s:
        assert s is None  # no tracer configured -> plain no-op context


def test_set_tenant_contextvar(settings):
    from src.db.database import Database, current_org

    db = Database(None, settings.data_dir)
    db.set_tenant("org1")
    assert current_org.get() == "org1"
    db.clear_tenant()
    assert current_org.get() is None


def test_ingest_document_job_finalizes(settings, seeded_retriever, tmp_path):
    import src.retrieval.retriever as R
    from src.db.database import get_db
    from src.ingestion.jobs import ingest_document_job
    from src.tenancy import repo

    R._retriever = seeded_retriever  # the job uses the process retriever
    db = get_db()  # autouse temp DB
    ws = repo.create_workspace(db, "org1", "Deal room")
    doc = repo.create_document(db, "org1", ws.id, "deal.txt", "txt", "u1")

    path = os.path.join(str(tmp_path), "deal.txt")
    with open(path, "wb") as f:
        f.write(b"The target company FY2023 EBITDA was 42 million dollars.")

    ingest_document_job("org1", ws.id, doc.id, path, "deal.txt")

    fresh = repo.get_document(db, doc.id)
    assert fresh.status == "ready"
    assert fresh.chunk_count > 0
    assert not os.path.exists(path)  # staged file cleaned up

    # The uploaded content is retrievable only inside its workspace.
    res = seeded_retriever.retrieve("EBITDA", workspaces=[ws.id])
    assert any("EBITDA" in c.text for c in res.chunks)


def test_ingest_document_job_marks_failed_on_bad_file(settings, seeded_retriever, tmp_path):
    import src.retrieval.retriever as R
    from src.db.database import get_db
    from src.ingestion.jobs import ingest_document_job
    from src.tenancy import repo

    R._retriever = seeded_retriever
    db = get_db()
    ws = repo.create_workspace(db, "org1", "Deal")
    doc = repo.create_document(db, "org1", ws.id, "x.xyz", "xyz", "u1")
    path = os.path.join(str(tmp_path), "x.xyz")
    with open(path, "wb") as f:
        f.write(b"unsupported")
    ingest_document_job("org1", ws.id, doc.id, path, "x.xyz")
    assert repo.get_document(db, doc.id).status == "failed"
