"""Document-ingestion job (Phase 17).

Runs inline (sync fallback) or on an RQ worker. Reads the staged upload from disk,
ingests it into the tenant's workspace, finalizes the document record, and cleans
up — marking the document 'failed' on any error so the UI can surface it.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def ingest_document_job(
    org_id: str, workspace_id: str, doc_id: str, path: str, filename: str
) -> None:
    from src.db.database import get_db
    from src.ingestion.upload import UploadError, ingest_upload
    from src.retrieval.retriever import get_retriever
    from src.tenancy import repo

    db = get_db()
    try:
        with open(path, "rb") as f:
            data = f.read()
        n = ingest_upload(get_retriever(), org_id, workspace_id, doc_id, filename, data)
        repo.finalize_document(db, doc_id, n)
        logger.info("job: ingested %s -> %d chunks", filename, n)
    except UploadError as exc:
        repo.set_document_status(db, doc_id, "failed")
        logger.warning("job: upload rejected for %s: %s", filename, exc)
    except Exception as exc:  # noqa: BLE001 — never crash the worker on one doc
        repo.set_document_status(db, doc_id, "failed")
        logger.exception("job: ingestion failed for %s: %s", filename, exc)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
