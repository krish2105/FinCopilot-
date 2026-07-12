from src.ingestion.models import DocType, RawDocument, SourceMetadata
from src.ingestion.parse import parse_document


def _doc(html: str) -> RawDocument:
    return RawDocument(
        doc_id="d1",
        metadata=SourceMetadata(ticker="ACME", doc_type=DocType.TEN_K),
        content=html,
        content_type="html",
    )


def test_parse_tracks_sections(sample_html):
    blocks = parse_document(_doc(sample_html))
    sections = {b.section for b in blocks}
    assert any("Item 1. Business" in s for s in sections)
    assert any("Item 1A. Risk Factors" in s for s in sections)


def test_parse_keeps_table_atomic(sample_html):
    blocks = parse_document(_doc(sample_html))
    tables = [b for b in blocks if b.is_table]
    assert len(tables) == 1
    # The whole table stays in one block.
    assert "Revenue" in tables[0].text
    assert "Net income" in tables[0].text
    assert "|" in tables[0].text  # row cells joined


def test_parse_assigns_pages():
    long_para = "word " * 2000  # ~10k chars -> spans multiple pseudo-pages
    html = f"<html><body><p>Item 1. Business</p><p>{long_para}</p></body></html>"
    blocks = parse_document(_doc(html))
    assert all(b.page >= 1 for b in blocks)


def test_parse_plaintext():
    doc = RawDocument(
        doc_id="d2",
        metadata=SourceMetadata(ticker="ACME", doc_type=DocType.MARKET),
        content="ACME revenue was 1000.\n\nNet income was 120.",
        content_type="text",
    )
    blocks = parse_document(doc)
    assert len(blocks) == 2
    assert "revenue" in blocks[0].text.lower()
