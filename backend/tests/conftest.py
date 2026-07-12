"""Test config: force the deterministic offline embedder so the suite needs no
torch, no network, and no API keys — and is fully reproducible in CI."""

import os

# Must be set before src.config.settings is first imported/cached.
os.environ.setdefault("FINCOPILOT_EMBED_BACKEND", "hash")
os.environ.setdefault("FINCOPILOT_RERANK_BACKEND", "lexical")
os.environ.setdefault("FINCOPILOT_OFFLINE_MODE", "true")

import pytest

from src.config.settings import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        fincopilot_embed_backend="hash",
        fincopilot_offline_mode=True,
        data_dir=str(tmp_path),
    )


SAMPLE_10K_HTML = """
<html><body>
<p>Item 1. Business</p>
<p>Acme Corp designs and sells widgets across global markets.</p>
<div><table>
<tr><th>Metric</th><th>2024</th><th>2023</th></tr>
<tr><td>Revenue</td><td>1,000</td><td>900</td></tr>
<tr><td>Net income</td><td>120</td><td>100</td></tr>
</table></div>
<p>Item 1A. Risk Factors</p>
<p>Our business faces competition, supply chain risk, and going concern uncertainty.</p>
<p>Foreign currency fluctuations may adversely affect results.</p>
</body></html>
"""


@pytest.fixture
def sample_html() -> str:
    return SAMPLE_10K_HTML


# A tiny real-shaped corpus for retrieval tests: (ticker, doc_type, section, text)
SEED_CORPUS = [
    (
        "AAPL",
        "10-K",
        "Item 7. MD&A",
        "Apple total net sales were 391 billion dollars in fiscal 2024, an increase "
        "driven by iPhone and Services revenue growth.",
    ),
    (
        "AAPL",
        "10-K",
        "Item 1A. Risk Factors",
        "Risk factors include supply chain concentration, component shortages, "
        "foreign exchange volatility, and intense competition affecting results.",
    ),
    (
        "AAPL",
        "market",
        "profile",
        "Apple gross margin expanded year over year due to a favorable Services mix.",
    ),
    (
        "MSFT",
        "10-K",
        "Item 7. MD&A",
        "Microsoft total revenue was 245 billion dollars, driven by Intelligent "
        "Cloud and Azure growth.",
    ),
    (
        "MSFT",
        "10-K",
        "Item 1A. Risk Factors",
        "Microsoft faces cybersecurity risk and intense competition in cloud computing markets.",
    ),
    (
        "AAPL",
        "8-K",
        "Body",
        "The annual shareholder meeting will be held in Cupertino next quarter.",
    ),
]


@pytest.fixture
def seeded_retriever(settings):
    """A Retriever over a small in-memory corpus (hash embed, lexical rerank)."""
    import os

    from src.ingestion.embed import Embedder
    from src.ingestion.models import Chunk, DocType, SourceMetadata
    from src.retrieval.bm25 import BM25Index
    from src.retrieval.reranker import Reranker
    from src.retrieval.retriever import Retriever
    from src.retrieval.store import LocalVectorStore

    embedder = Embedder(settings)
    store = LocalVectorStore(
        embedder.dim, embedder.name, os.path.join(settings.data_dir, "v.sqlite")
    )
    chunks = []
    for i, (ticker, dt, section, text) in enumerate(SEED_CORPUS):
        md = SourceMetadata(
            ticker=ticker,
            doc_type=DocType(dt),
            title=f"{ticker} {dt}",
            source_url=f"https://sec.gov/{ticker}/{i}",
            page=i + 1,
            section=section,
        )
        c = Chunk(
            chunk_id=Chunk.make_chunk_id(f"{ticker}-{i}", text),
            doc_id=f"{ticker}-{i}",
            text=text,
            metadata=md,
            embedding=embedder.embed([text])[0],
        )
        chunks.append(c)
    store.upsert(chunks)
    bm25 = BM25Index.build(chunks, os.path.join(settings.data_dir, "bm25.json"))
    reranker = Reranker(settings)
    return Retriever(
        settings=settings, embedder=embedder, store=store, bm25=bm25, reranker=reranker
    )


@pytest.fixture
def seeded_graph(seeded_retriever, settings):
    """Entity graph built from the same store the seeded_retriever uses."""
    import os

    from src.retrieval.graph import EntityGraph

    return EntityGraph.build(seeded_retriever.store, os.path.join(settings.data_dir, "graph.json"))
