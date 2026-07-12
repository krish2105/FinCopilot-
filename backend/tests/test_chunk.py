from src.ingestion.chunk import chunk_document
from src.ingestion.models import DocType, RawDocument, SourceMetadata
from src.ingestion.parse import parse_document


def _doc(html: str, dt: DocType = DocType.TEN_K) -> RawDocument:
    return RawDocument(
        doc_id="d1",
        metadata=SourceMetadata(ticker="ACME", doc_type=dt, filing_date="2024-01-01"),
        content=html,
        content_type="html",
    )


def test_chunks_carry_metadata(sample_html):
    doc = _doc(sample_html)
    chunks = chunk_document(doc, parse_document(doc))
    assert chunks
    for c in chunks:
        assert c.metadata.ticker == "ACME"
        assert c.metadata.doc_type == DocType.TEN_K
        assert c.metadata.page is not None
        assert c.chunk_id and c.doc_id == "d1"


def test_table_becomes_its_own_chunk(sample_html):
    doc = _doc(sample_html)
    chunks = chunk_document(doc, parse_document(doc))
    table_chunks = [c for c in chunks if "Revenue" in c.text and "|" in c.text]
    assert len(table_chunks) == 1


def test_chunk_ids_are_deterministic(sample_html):
    doc = _doc(sample_html)
    a = [c.chunk_id for c in chunk_document(doc, parse_document(doc))]
    b = [c.chunk_id for c in chunk_document(doc, parse_document(doc))]
    assert a == b  # content-addressed -> stable across runs (idempotency)


def test_oversized_block_is_split():
    big = "alpha beta gamma delta " * 800  # far exceeds target tokens
    html = f"<html><body><p>Item 1. Business</p><p>{big}</p></body></html>"
    doc = _doc(html)
    chunks = chunk_document(doc, parse_document(doc))
    assert len(chunks) > 1
