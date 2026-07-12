"""Ingest a user-uploaded document into a private workspace (data room).

Extracts text (PDF via pypdf, else decode), runs the same parse → chunk → embed →
store pipeline as public filings, tagging every chunk with the workspace_id so it
is only ever retrievable by that tenant. Rebuilds the live BM25 index so uploads
are searchable immediately.
"""

from __future__ import annotations

import logging

from src.ingestion.chunk import chunk_document
from src.ingestion.models import DocType, RawDocument, SourceMetadata
from src.ingestion.parse import parse_document
from src.retrieval.bm25 import BM25Index, bm25_path
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


class UploadError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Return (text, content_type). Raises UploadError on unsupported/empty."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError("File exceeds the 15 MB limit.")
    lower = filename.lower()
    if lower.endswith(".pdf"):
        try:
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise UploadError(f"Could not read PDF: {exc}") from exc
        return text, "text"
    if lower.endswith((".html", ".htm")):
        return data.decode("utf-8", errors="ignore"), "html"
    if lower.endswith((".txt", ".md", ".csv")):
        return data.decode("utf-8", errors="ignore"), "text"
    raise UploadError("Unsupported file type. Use PDF, HTML, TXT, MD, or CSV.")


def ingest_upload(
    retriever: Retriever,
    org_id: str,
    workspace_id: str,
    doc_id: str,
    filename: str,
    data: bytes,
) -> int:
    """Ingest into the retriever's live store; returns the chunk count."""
    text, content_type = extract_text(filename, data)
    if not text.strip():
        raise UploadError("No extractable text found in the document.")

    # Flag (don't block) prompt-injection attempts in untrusted uploads; the
    # synthesizer wraps all evidence as untrusted data regardless.
    from src.security.injection import detect_injection

    hits = detect_injection(text)
    if hits:
        logger.warning("Potential prompt-injection in upload %s: %s", filename, hits[:3])

    md = SourceMetadata(
        ticker=filename[:16].upper() or "DOC",
        doc_type=DocType.UPLOAD,
        title=filename,
        source_url=f"upload://{workspace_id}/{doc_id}",
        workspace_id=workspace_id,
    )
    doc = RawDocument(doc_id=doc_id, metadata=md, content=text, content_type=content_type)
    chunks = chunk_document(doc, parse_document(doc))

    embedder = retriever.embedder
    store = retriever.store
    new = [c for c in chunks if c.chunk_id not in store.existing_ids([c.chunk_id for c in chunks])]
    batch = 32
    for i in range(0, len(new), batch):
        window = new[i : i + batch]
        vectors = embedder.embed([c.text for c in window])
        for c, v in zip(window, vectors, strict=True):
            c.embedding = v
        store.upsert(window)

    # Rebuild BM25 over the full store so the upload is lexically searchable now.
    retriever.bm25 = BM25Index.build(store.iter_all(), bm25_path())
    logger.info(
        "upload %s ingested: %d chunks -> workspace %s", filename, len(chunks), workspace_id
    )
    return len(chunks)
