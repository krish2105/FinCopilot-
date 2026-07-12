"""Phase 26: Contextual Retrieval — chunks carry a situating blurb that is
embedded and lexically indexed (but not shown in citations)."""

from src.ingestion.contextualize import (
    context_for,
    contextual_text,
    template_context,
)
from src.ingestion.models import DocType, ParsedBlock, RawDocument, SourceMetadata
from src.ingestion.chunk import chunk_document
from src.retrieval.bm25 import BM25Index


def _md(**kw) -> SourceMetadata:
    base = dict(ticker="AAPL", doc_type=DocType.TEN_K, title="FY2024 10-K", section="Risk Factors")
    base.update(kw)
    return SourceMetadata(**base)


def test_template_context_mentions_entity_and_section():
    ctx = template_context(_md())
    assert "AAPL" in ctx
    assert "annual report" in ctx.lower()
    assert "Risk Factors" in ctx


def test_contextual_text_prepends_and_is_optional():
    assert contextual_text("body", "CTX").startswith("CTX")
    assert contextual_text("body", "") == "body"


def test_context_for_recomputes_when_missing():
    md = _md()
    assert context_for(md, "") == template_context(md)
    assert context_for(md, "kept") == "kept"


def test_chunk_gets_context_set():
    doc = RawDocument(
        doc_id="d1",
        metadata=_md(),
        content="Supply chain disruptions could harm results.",
        content_type="text",
    )
    blocks = [ParsedBlock(text="Supply chain disruptions could harm results.", page=1, section="Risk Factors")]
    chunks = chunk_document(doc, blocks)
    assert chunks and chunks[0].context
    assert "AAPL" in chunks[0].context


def test_bm25_indexes_context_tokens(tmp_path):
    doc = RawDocument(
        doc_id="d2",
        metadata=_md(ticker="NVDA", title="FY2025 10-K", section="Competition"),
        content="We face intense rivalry.",
        content_type="text",
    )
    blocks = [ParsedBlock(text="We face intense rivalry.", page=1, section="Competition")]
    chunks = chunk_document(doc, blocks)
    idx = BM25Index.build(chunks, str(tmp_path / "bm25.json"))
    # "competition" only appears in the situating context, not the body text —
    # it must still be searchable, proving contextual lexical indexing works.
    hits = idx.query("competition", k=3)
    assert hits and hits[0].metadata.ticker == "NVDA"
    # ...but the displayed excerpt stays the original body text.
    assert hits[0].text == "We face intense rivalry."
