"""Multi-tenancy: DB/repo, workspace-scoped retrieval isolation, uploads."""

import os

import pytest

from src.db.database import Database
from src.ingestion.embed import Embedder
from src.ingestion.models import Chunk, DocType, SourceMetadata
from src.ingestion.upload import UploadError, extract_text
from src.retrieval.store import LocalVectorStore
from src.tenancy import repo


@pytest.fixture
def db(settings) -> Database:
    return Database(None, settings.data_dir)


def test_ensure_org_user_idempotent(db):
    a = repo.ensure_org_user(db, "u1", "u1@x.com", "Org1")
    b = repo.ensure_org_user(db, "u1", "u1@x.com", "Org1")
    assert a.id == b.id  # same org on repeat
    # A default workspace was created.
    assert len(repo.list_workspaces(db, a.id)) == 1


def test_workspaces_are_org_isolated(db):
    o1 = repo.ensure_org_user(db, "u1", None, "Org1")
    o2 = repo.ensure_org_user(db, "u2", None, "Org2")
    ws1 = repo.create_workspace(db, o1.id, "Deal A")
    # org2's accessible ids never include org1's workspace
    acc2 = repo.accessible_workspace_ids(db, o2.id)
    assert ws1.id not in acc2
    assert repo.PUBLIC_WORKSPACE in acc2  # everyone sees public


def test_documents_and_conversations(db):
    o = repo.ensure_org_user(db, "u1", None, "Org1")
    ws = repo.create_workspace(db, o.id, "Deal A")
    doc = repo.create_document(db, o.id, ws.id, "q3.pdf", "pdf", "u1")
    repo.finalize_document(db, doc.id, 12)
    docs = repo.list_documents(db, ws.id)
    assert docs[0].chunk_count == 12 and docs[0].status == "ready"

    conv = repo.create_conversation(db, o.id, ws.id, "u1", "hello")
    repo.add_message(db, conv.id, "user", "hi")
    repo.add_message(db, conv.id, "assistant", "hello", '{"a":1}')
    assert len(repo.list_messages(db, conv.id)) == 2


def test_retrieval_workspace_isolation(settings):
    """A chunk in workspace X must never surface when scoped to workspace Y."""
    emb = Embedder(settings)
    store = LocalVectorStore(emb.dim, emb.name, os.path.join(settings.data_dir, "v.sqlite"))

    def chunk(text, ws, cid):
        md = SourceMetadata(ticker="DOC", doc_type=DocType.UPLOAD, workspace_id=ws)
        return Chunk(
            chunk_id=cid, doc_id=cid, text=text, metadata=md, embedding=emb.embed([text])[0]
        )

    store.upsert([chunk("secret revenue was 500 million", "ws_A", "c1")])
    store.upsert([chunk("public risk factors and competition", "public", "c2")])

    q = emb.embed(["revenue"])[0]
    # Scoped to ws_B -> cannot see ws_A's private chunk
    assert store.search(q, k=5, workspaces=["ws_B", "public"]) == [] or all(
        h.chunk_id != "c1" for h in store.search(q, k=5, workspaces=["ws_B", "public"])
    )
    # Scoped to ws_A -> sees it
    hits = store.search(q, k=5, workspaces=["ws_A"])
    assert any(h.chunk_id == "c1" for h in hits)


def test_upload_extract_text():
    text, ct = extract_text("notes.txt", b"Revenue was 500 million dollars.")
    assert "Revenue" in text and ct == "text"
    with pytest.raises(UploadError):
        extract_text("bad.xyz", b"data")


def test_ingest_upload_is_workspace_scoped(settings, seeded_retriever):
    from src.ingestion.upload import ingest_upload

    n = ingest_upload(
        seeded_retriever,
        "org1",
        "ws_private",
        "doc1",
        "deal.txt",
        b"The target company FY2023 EBITDA was 42 million dollars.",
    )
    assert n > 0
    # Retrievable inside its workspace...
    res = seeded_retriever.retrieve("EBITDA", workspaces=["ws_private"])
    assert any("EBITDA" in c.text for c in res.chunks)
    # ...but not from the public scope.
    pub = seeded_retriever.retrieve("EBITDA", workspaces=["public"])
    assert all("EBITDA" not in c.text for c in pub.chunks)
