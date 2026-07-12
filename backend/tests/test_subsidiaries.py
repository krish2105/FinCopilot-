import os

from src.ingestion.chunk import chunk_document
from src.ingestion.models import DocType, RawDocument, SourceMetadata
from src.ingestion.parse import parse_document
from src.retrieval.graph import EntityGraph
from src.retrieval.graphrag import graphrag_retrieve
from src.retrieval.subsidiaries import parse_subsidiaries

EX21 = """EXHIBIT 21.1
SUBSIDIARIES OF THE REGISTRANT

Name                                   Jurisdiction
Apple Sales International              Ireland
Braeburn Capital, Inc.                 Nevada
Apple Operations Europe               Ireland
Beats Electronics, LLC                California
State of Incorporation
"""


def test_parse_subsidiaries():
    subs = parse_subsidiaries(EX21)
    assert "Apple Sales International" in subs
    assert "Braeburn Capital, Inc." in subs
    assert "Beats Electronics, LLC" in subs
    # header/jurisdiction lines excluded
    assert all("SUBSIDIARIES OF" not in s.upper() for s in subs)
    assert "State of Incorporation" not in subs


def _seed_graph_with_ex21(settings):
    from src.ingestion.embed import Embedder
    from src.retrieval.store import LocalVectorStore

    emb = Embedder(settings)
    store = LocalVectorStore(emb.dim, emb.name, os.path.join(settings.data_dir, "v.sqlite"))
    md = SourceMetadata(
        ticker="AAPL",
        doc_type=DocType.SUBSIDIARIES,
        title="AAPL EX-21",
        source_url="https://sec.gov/aapl/ex21",
        page=1,
    )
    doc = RawDocument(doc_id="aapl-ex21", metadata=md, content=EX21, content_type="text")
    chunks = chunk_document(doc, parse_document(doc))
    for c in chunks:
        c.embedding = emb.embed([c.text])[0]
    store.upsert(chunks)
    graph = EntityGraph.build(store, os.path.join(settings.data_dir, "g.json"))
    return graph, store


def test_graph_adds_subsidiary_nodes(settings):
    graph, _ = _seed_graph_with_ex21(settings)
    subs = graph.subsidiaries_of("AAPL")
    assert "Apple Sales International" in subs
    assert graph.stats()["by_kind"].get("subsidiary", 0) >= 3


def test_graphrag_answers_subsidiary_query(settings):
    graph, store = _seed_graph_with_ex21(settings)
    res = graphrag_retrieve(graph, store, "What subsidiaries does Apple have?")
    assert res.route == "graphrag"
    assert "subsidiaries" in res.answer.lower()
    assert "Braeburn Capital" in res.answer
    assert res.chunks  # Exhibit 21 evidence hydrated + cited
