"""In-process BM25 lexical index.

Built at the end of ingestion from every stored chunk and persisted as JSON
(tokenized corpus + citation metadata). rank_bm25's BM25Okapi is rebuilt on load
(cheap) rather than pickled, to avoid version-fragile pickles.
"""

from __future__ import annotations

import json
import logging
import os
import re

from src.config.settings import get_settings
from src.ingestion.models import Chunk, DocType, SourceMetadata
from src.retrieval.store import SearchHit

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, path: str):
        self.path = path
        self._records: list[dict] = []
        self._bm25 = None

    # --- build / persist ---
    @classmethod
    def build(cls, chunks: list[Chunk], path: str) -> BM25Index:
        from src.ingestion.contextualize import context_for, contextual_text

        idx = cls(path)
        idx._records = [
            {
                "chunk_id": c.chunk_id,
                # Contextual Retrieval (Phase 26): index the situating context too,
                # so lexical search also benefits. Display text stays original.
                "tokens": tokenize(contextual_text(c.text, context_for(c.metadata, c.context))),
                "text": c.text,
                "ticker": c.metadata.ticker,
                "doc_type": c.metadata.doc_type.value,
                "title": c.metadata.title,
                "source_url": c.metadata.source_url,
                "filing_date": c.metadata.filing_date,
                "page": c.metadata.page,
                "section": c.metadata.section,
                "workspace_id": c.metadata.workspace_id,
            }
            for c in chunks
        ]
        idx._fit()
        idx.save()
        return idx

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._records, f)
        logger.info("BM25 index saved: %d docs -> %s", len(self._records), self.path)

    @classmethod
    def load(cls, path: str) -> BM25Index | None:
        if not os.path.exists(path):
            return None
        idx = cls(path)
        with open(path) as f:
            idx._records = json.load(f)
        idx._fit()
        return idx

    def _fit(self) -> None:
        from rank_bm25 import BM25Okapi

        corpus = [r["tokens"] for r in self._records] or [[""]]
        self._bm25 = BM25Okapi(corpus)

    # --- query ---
    def query(
        self,
        text: str,
        k: int = 8,
        tickers: list[str] | None = None,
        workspaces: list[str] | None = None,
    ) -> list[SearchHit]:
        if not self._records:
            return []
        scores = self._bm25.get_scores(tokenize(text))
        allowed = {t.upper() for t in tickers} if tickers else None
        allowed_ws = set(workspaces) if workspaces else None
        candidates = [
            i
            for i in range(len(scores))
            if (allowed is None or self._records[i]["ticker"].upper() in allowed)
            and (allowed_ws is None or self._records[i].get("workspace_id", "public") in allowed_ws)
        ]
        ranked = sorted(candidates, key=lambda i: scores[i], reverse=True)
        hits: list[SearchHit] = []
        for i in ranked[:k]:
            r = self._records[i]
            md = SourceMetadata(
                ticker=r["ticker"],
                doc_type=DocType(r["doc_type"]),
                title=r["title"] or "",
                source_url=r["source_url"] or "",
                filing_date=r["filing_date"],
                page=r["page"],
                section=r["section"],
            )
            hits.append(SearchHit(r["chunk_id"], float(scores[i]), r["text"], md))
        return hits

    def __len__(self) -> int:
        return len(self._records)


def bm25_path() -> str:
    return os.path.join(get_settings().data_dir, "bm25_index.json")
