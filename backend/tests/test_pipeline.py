"""End-to-end ingestion test with fetchers stubbed (no network)."""

import os

from src.ingestion import pipeline
from src.ingestion.embed import Embedder
from src.ingestion.models import DocType, RawDocument, SourceMetadata
from src.ingestion.pipeline import ingest
from src.retrieval.store import LocalVectorStore

_FILING_HTML = """
<html><body>
<p>Item 1A. Risk Factors</p>
<p>ACME faces competition and foreign currency risk in global markets.</p>
<div><table><tr><td>Revenue</td><td>1000</td></tr></table></div>
</body></html>
"""


def _stub_fetchers(monkeypatch):
    def fake_edgar(ticker, *a, **k):
        md = SourceMetadata(
            ticker=ticker,
            doc_type=DocType.TEN_K,
            title=f"{ticker} 10-K",
            source_url="https://sec.gov/x",
            filing_date="2024-01-01",
        )
        return [RawDocument(doc_id=f"{ticker}-10k", metadata=md, content=_FILING_HTML)]

    def fake_market(ticker, *a, **k):
        md = SourceMetadata(ticker=ticker, doc_type=DocType.MARKET, title="profile")
        return [
            RawDocument(
                doc_id=f"{ticker}-mkt",
                metadata=md,
                content=f"{ticker} revenue was 1000; net income was 120.",
                content_type="text",
            )
        ]

    def fake_news(ticker, *a, **k):
        return []

    monkeypatch.setattr(pipeline.edgar, "fetch_filings", fake_edgar)
    monkeypatch.setattr(pipeline.market, "fetch_market", fake_market)
    monkeypatch.setattr(pipeline.news, "fetch_news", fake_news)


def _make(settings):
    embedder = Embedder(settings)
    store = LocalVectorStore(
        embedder.dim, embedder.name, os.path.join(settings.data_dir, "v.sqlite")
    )
    return embedder, store


def test_end_to_end_ingest(monkeypatch, settings):
    _stub_fetchers(monkeypatch)
    embedder, store = _make(settings)
    stats = ingest(["ACME"], settings=settings, store=store, embedder=embedder)

    assert stats.docs_fetched == 2
    assert stats.chunks_new > 0
    assert store.count() == stats.chunks_new
    assert stats.bm25_docs == store.count()

    # Every stored chunk has an embedding of the right dim.
    for c in store.iter_all():
        assert c.embedding is not None and len(c.embedding) == embedder.dim


def test_reingest_is_idempotent(monkeypatch, settings):
    _stub_fetchers(monkeypatch)
    embedder, store = _make(settings)
    first = ingest(["ACME"], settings=settings, store=store, embedder=embedder)
    second = ingest(["ACME"], settings=settings, store=store, embedder=embedder)

    assert second.chunks_new == 0
    assert second.chunks_skipped == first.chunks_total
    assert store.count() == first.chunks_new  # no growth on re-run
