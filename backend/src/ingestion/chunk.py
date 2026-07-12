"""Structure-aware chunking.

Rules:
  * A table block is never split — it becomes its own chunk (financial statements
    stay intact for the Analyst agent).
  * Prose blocks are packed greedily up to ~chunk_target_tokens, with a small
    overlap carried into the next chunk for context continuity.
  * Section boundaries flush the current chunk so a chunk never spans two Items.
Each chunk inherits its source metadata plus the page/section of its content.
"""

from __future__ import annotations

from src.config.settings import get_settings
from src.ingestion.models import Chunk, ParsedBlock, RawDocument, SourceMetadata


def _est_tokens(text: str) -> int:
    # Cheap, dependency-free token estimate (~4 chars/token).
    return max(1, len(text) // 4)


def _make_chunk(doc: RawDocument, text: str, page: int, section: str) -> Chunk:
    md = doc.metadata.model_copy(update={"page": page, "section": section})
    chunk_id = Chunk.make_chunk_id(doc.doc_id, text)
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc.doc_id,
        text=text,
        metadata=md,
        token_estimate=_est_tokens(text),
    )


def chunk_document(doc: RawDocument, blocks: list[ParsedBlock]) -> list[Chunk]:
    settings = get_settings()
    target = settings.chunk_target_tokens
    overlap = settings.chunk_overlap_tokens

    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    cur_page: int | None = None
    cur_section: str | None = None

    def flush() -> None:
        nonlocal buf, buf_tokens
        if not buf:
            return
        text = "\n\n".join(buf).strip()
        if text:
            chunks.append(_make_chunk(doc, text, cur_page or 1, cur_section or ""))
        buf = []
        buf_tokens = 0

    for block in blocks:
        # Tables are atomic and get their own chunk.
        if block.is_table:
            flush()
            chunks.append(_make_chunk(doc, block.text, block.page, block.section))
            continue

        # A new section flushes the current buffer.
        if cur_section is not None and block.section != cur_section:
            flush()

        if cur_page is None:
            cur_page = block.page
        cur_section = block.section

        btokens = _est_tokens(block.text)

        # An oversized single block: hard-split it into token windows.
        if btokens > target:
            flush()
            for piece in _split_oversized(block.text, target, overlap):
                chunks.append(_make_chunk(doc, piece, block.page, block.section))
            cur_page = block.page
            continue

        if buf_tokens + btokens > target:
            flush()
            cur_page = block.page
        buf.append(block.text)
        buf_tokens += btokens

    flush()
    return _dedupe(chunks)


def _split_oversized(text: str, target: int, overlap: int) -> list[str]:
    step_chars = max(1, (target - overlap) * 4)
    win_chars = target * 4
    pieces = []
    i = 0
    while i < len(text):
        pieces.append(text[i : i + win_chars].strip())
        i += step_chars
    return [p for p in pieces if p]


def _dedupe(chunks: list[Chunk]) -> list[Chunk]:
    seen: set[str] = set()
    out: list[Chunk] = []
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        out.append(c)
    return out


def chunks_from_metadata_text(ticker: str, metadata: SourceMetadata, text: str) -> list[Chunk]:
    """Convenience for text-native sources (market/news) built outside HTML."""
    doc = RawDocument(
        doc_id=RawDocument.make_doc_id(ticker, metadata.doc_type, text[:64]),
        metadata=metadata,
        content=text,
        content_type="text",
    )
    from src.ingestion.parse import parse_document

    return chunk_document(doc, parse_document(doc))
