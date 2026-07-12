"""Cross-encoder reranker with a deterministic offline fallback.

Primary: local `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers),
no API required. Fallback (offline mode / torch or model unavailable): a
deterministic lexical relevance score based on query-term coverage + density, so
CI and offline demos still reorder candidates sensibly without heavy deps.

Like the embedder, the backend is resolved once. Offline mode forces "lexical"
because loading the cross-encoder would require a network model download.
"""

from __future__ import annotations

import logging
import math
import re

from src.config.settings import Settings, get_settings
from src.retrieval.types import RetrievedChunk

logger = logging.getLogger(__name__)

_CE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def resolve_rerank_backend(settings: Settings) -> str:
    choice = settings.fincopilot_rerank_backend.lower()
    if choice in ("cross-encoder", "lexical"):
        return choice
    # "auto"
    if settings.fincopilot_offline_mode:
        return "lexical"
    return "cross-encoder"


class Reranker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.backend = resolve_rerank_backend(self.settings)
        self._ce = None
        if self.backend == "cross-encoder" and not self._try_load_ce():
            logger.warning("Cross-encoder unavailable; using lexical reranker")
            self.backend = "lexical"
        self.name = _CE_MODEL if self.backend == "cross-encoder" else "lexical-v1"

    def _try_load_ce(self) -> bool:
        try:
            from sentence_transformers import CrossEncoder
        except Exception:
            return False
        try:
            self._ce = CrossEncoder(_CE_MODEL)
            return True
        except Exception as exc:
            logger.warning("Failed to load %s: %s", _CE_MODEL, exc)
            return False

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int = 6
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        if self.backend == "cross-encoder":
            scores = self._ce.predict([(query, c.text) for c in chunks])
            for c, s in zip(chunks, scores, strict=True):
                c.rerank_score = float(s)
        else:
            q_tokens = set(_TOKEN_RE.findall(query.lower()))
            for c in chunks:
                c.rerank_score = _lexical_score(q_tokens, c.text)
        ranked = sorted(chunks, key=lambda c: c.rerank_score, reverse=True)
        return ranked[:top_k]


def _lexical_score(q_tokens: set[str], text: str) -> float:
    """Query-term coverage weighted by log term frequency, length-normalized."""
    if not q_tokens:
        return 0.0
    doc_tokens = _TOKEN_RE.findall(text.lower())
    if not doc_tokens:
        return 0.0
    counts: dict[str, int] = {}
    for t in doc_tokens:
        if t in q_tokens:
            counts[t] = counts.get(t, 0) + 1
    coverage = len(counts) / len(q_tokens)
    density = sum(1.0 + math.log(v) for v in counts.values()) / math.sqrt(len(doc_tokens))
    return coverage + 0.1 * density
