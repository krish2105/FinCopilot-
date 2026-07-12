"""Embedding backends with a resolve-once fallback chain.

Priority (per the plan): Gemini `gemini-embedding-001` primary, local
sentence-transformers `bge-small-en-v1.5` fallback. A deterministic hashing
embedder is the last resort so CI/tests need neither torch nor network.

IMPORTANT — dimension consistency: the backend is resolved ONCE per process and
its (model, dim) is fixed for the whole corpus AND for queries. We do NOT switch
backends mid-run, because different backends produce different-dimension vectors
that cannot be compared. Switching backends means re-ingesting; the vector store
records (embed_model, dim) and refuses a mismatched query.
"""

from __future__ import annotations

import hashlib
import logging
import time

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_HASH_DIM = 384
_ST_MODEL = "BAAI/bge-small-en-v1.5"  # 384 dims
_GEMINI_MODEL = "gemini-embedding-001"
_GEMINI_DIM = 768


def resolve_backend(settings: Settings) -> str:
    choice = settings.fincopilot_embed_backend.lower()
    if choice in ("gemini", "local", "hash"):
        return choice
    # "auto"
    if settings.fincopilot_offline_mode or not settings.gemini_api_key:
        return "local"
    return "gemini"


class Embedder:
    """Uniform interface over the selected backend. `dim` and `name` are fixed."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.backend = resolve_backend(self.settings)
        self._st_model = None  # lazily loaded sentence-transformers model
        self.name, self.dim = self._probe()

    def _probe(self) -> tuple[str, int]:
        if self.backend == "gemini":
            return _GEMINI_MODEL, _GEMINI_DIM
        if self.backend == "local":
            if self._try_load_st():
                return _ST_MODEL, 384
            logger.warning("sentence-transformers unavailable; falling back to hash embedder")
            self.backend = "hash"
        return "hash-embedder-v1", _HASH_DIM

    def _try_load_st(self) -> bool:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            return False
        try:
            self._st_model = SentenceTransformer(_ST_MODEL)
            return True
        except Exception as exc:  # model download / runtime failure
            logger.warning("Failed to load %s: %s", _ST_MODEL, exc)
            return False

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.backend == "gemini":
            return self._embed_gemini(texts)
        if self.backend == "local":
            return self._embed_st(texts)
        return [self._embed_hash(t) for t in texts]

    # --- backends ---
    def _embed_st(self, texts: list[str]) -> list[list[float]]:
        vecs = self._st_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    def _embed_gemini(self, texts: list[str], _attempt: int = 0) -> list[list[float]]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            resp = client.models.embed_content(
                model=_GEMINI_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=_GEMINI_DIM),
            )
            return [list(e.values) for e in resp.embeddings]
        except Exception as exc:
            # Bounded backoff; we do NOT fall through to a different dim.
            if _attempt < 4:
                wait = 2**_attempt
                logger.warning("Gemini embed failed (%s); retry in %ss", exc, wait)
                time.sleep(wait)
                return self._embed_gemini(texts, _attempt + 1)
            raise

    def _embed_hash(self, text: str) -> list[float]:
        """Signed hashing bag-of-words, L2-normalized.

        Deterministic and dependency-free. Shared tokens raise cosine similarity,
        so BM25/vector behaviour is realistic enough for tests and offline demos.
        """
        vec = [0.0] * _HASH_DIM
        tokens = _tokenize(text)
        for tok in tokens:
            h = int.from_bytes(hashlib.md5(tok.encode()).digest()[:8], "big")
            idx = h % _HASH_DIM
            sign = 1.0 if (h >> 63) & 1 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def _tokenize(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", text.lower())
