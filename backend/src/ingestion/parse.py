"""Parse fetched documents into located text blocks.

SEC filings are HTML with no real page numbers, so we derive:
  * a **pseudo-page**: cumulative character offset // page_char_size + 1
  * a **section**: the most recent "Item N." heading (10-K/10-Q structure)
Tables are kept intact as atomic blocks (is_table=True) so the chunker never
splits a financial statement down the middle.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from src.config.settings import get_settings
from src.ingestion.models import ParsedBlock, RawDocument

# "Item 1A.", "Item 7.", "ITEM 2." ... — the backbone of 10-K/10-Q structure.
_ITEM_RE = re.compile(r"^\s*(item\s+\d+[a-z]?)\s*[.\-:]", re.IGNORECASE)
# Collapse runs of whitespace introduced by HTML formatting.
_WS_RE = re.compile(r"[ \t ]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")

_BLOCK_TAGS = ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6")


def _clean(text: str) -> str:
    text = text.replace(" ", " ")
    text = _WS_RE.sub(" ", text)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _table_to_text(table) -> str:
    """Render an HTML table to whitespace-aligned text, preserving rows."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [_clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c != ""]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _looks_like_section(text: str) -> str | None:
    m = _ITEM_RE.match(text)
    if not m:
        return None
    # Keep the heading line itself as the section label (trimmed).
    return _clean(text.split("\n")[0])[:120]


def parse_document(doc: RawDocument) -> list[ParsedBlock]:
    settings = get_settings()
    page_size = settings.page_char_size

    if doc.content_type == "text":
        return _parse_text(doc.content, page_size)
    return _parse_html(doc.content, page_size)


def _emit(
    blocks: list[ParsedBlock],
    text: str,
    section: str,
    offset: int,
    page_size: int,
    is_table: bool,
) -> int:
    text = _clean(text)
    if not text:
        return offset
    page = offset // page_size + 1
    blocks.append(ParsedBlock(text=text, page=page, section=section, is_table=is_table))
    return offset + len(text)


def _parse_html(html: str, page_size: int) -> list[ParsedBlock]:
    soup = BeautifulSoup(html, "lxml")
    for junk in soup(["script", "style", "head", "noscript"]):
        junk.decompose()

    blocks: list[ParsedBlock] = []
    section = "Preamble"
    offset = 0
    seen_tables = set()

    body = soup.body or soup
    for el in body.find_all(_BLOCK_TAGS):
        # Tables handled atomically; skip the inner <tr> traversal for them.
        if el.name == "tr":
            continue
        table = el.find("table")
        if el.name == "div" and table is not None:
            tid = id(table)
            if tid in seen_tables:
                continue
            seen_tables.add(tid)
            offset = _emit(blocks, _table_to_text(table), section, offset, page_size, True)
            continue

        text = _clean(el.get_text(" ", strip=True))
        if not text:
            continue
        maybe_section = _looks_like_section(text)
        if maybe_section:
            section = maybe_section
        offset = _emit(blocks, text, section, offset, page_size, False)

    # Fallback: some filings are one big blob with no block tags.
    if not blocks:
        return _parse_text(soup.get_text("\n", strip=True), page_size)
    return blocks


def _parse_text(text: str, page_size: int) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    section = "Body"
    offset = 0
    for para in re.split(r"\n\s*\n", text):
        para = _clean(para)
        if not para:
            continue
        maybe_section = _looks_like_section(para)
        if maybe_section:
            section = maybe_section
        offset = _emit(blocks, para, section, offset, page_size, False)
    return blocks
