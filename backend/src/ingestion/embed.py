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
import os
import time

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_HASH_DIM = 384
_ST_MODEL = "BAAI/bge-small-en-v1.5"  # 384 dims
_GEMINI_MODEL = "gemini-embedding-001"
_GEMINI_DIM = 768

# --- Gemini free-tier quota control -------------------------------------------
# The free tier caps embedding *tokens per minute*, not just requests. Bulk seeding
# a corpus blows through it in seconds, and a 429 means "you must wait out the
# current minute" — a 1/2/4/8s backoff can never clear it. So we (a) pace requests
# against a rolling token budget and (b) cool down a full minute on a quota error.
# Override via GEMINI_EMBED_TPM if your key has a higher tier.
_GEMINI_TPM = int(os.getenv("GEMINI_EMBED_TPM", "25000"))  # under the ~30k free cap
_QUOTA_COOLDOWN_S = 65
_MAX_EMBED_RETRIES = 8

_QUOTA_MARKERS = ("429", "resource_exhausted", "resource exhausted", "quota", "rate limit")
_token_window: list[tuple[float, int]] = []  # rolling (timestamp, tokens) over 60s


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _QUOTA_MARKERS)


def _throttle(tokens: int) -> None:
    """Block until `tokens` fit inside the rolling per-minute budget."""
    while True:
        now = time.monotonic()
        while _token_window and now - _token_window[0][0] > 60.0:
            _token_window.pop(0)
        used = sum(t for _, t in _token_window)
        if used + tokens <= _GEMINI_TPM or not _token_window:
            _token_window.append((now, tokens))
            return
        sleep_for = 60.0 - (now - _token_window[0][0]) + 0.5
        logger.info(
            "embed throttle: %d tok used in the last minute; sleeping %.1fs", used, sleep_for
        )
        time.sleep(max(0.5, sleep_for))


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

    def try_embed_query(self, text: str) -> list[float] | None:
        """Embed a single query, or return None if the provider is out of quota.

        Bulk ingestion can afford to wait out a quota window; a user's query cannot
        — retrying for minutes would hang the request. On a free tier the embedding
        quota routinely runs out, so the query path fails fast and the retriever
        degrades to lexical-only search (Postgres FTS), which still answers well.
        """
        try:
            if self.backend == "gemini":
                # Raw call: no ingest throttle (never make a user wait on the bulk
                # token budget) and no retries (fail fast, degrade to lexical).
                return self._gemini_call([text])[0]
            return self.embed([text])[0]
        except Exception as exc:  # noqa: BLE001
            if _is_quota_error(exc):
                logger.warning("embed quota exhausted; falling back to lexical-only search")
            else:
                logger.warning("query embedding failed (%s); lexical-only search", exc)
            return None

    # --- backends ---
    def _embed_st(self, texts: list[str]) -> list[list[float]]:
        vecs = self._st_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    def _gemini_call(self, texts: list[str]) -> list[list[float]]:
        """One raw embedding request — no throttle, no retries."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        resp = client.models.embed_content(
            model=_GEMINI_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=_GEMINI_DIM),
        )
        return [list(e.values) for e in resp.embeddings]

    def _embed_gemini(self, texts: list[str], _attempt: int = 0) -> list[list[float]]:
        # Bulk path: stay inside the free tier's tokens-per-minute budget.
        _throttle(sum(_est_tokens(t) for t in texts))
        try:
            return self._gemini_call(texts)
        except Exception as exc:
            # A 429 is a *quota window*, not a transient blip: short backoff can never
            # clear it. Wait out the full minute and retry generously. We never fall
            # through to another backend — that would corrupt the corpus with mixed dims.
            if _attempt >= _MAX_EMBED_RETRIES:
                raise
            if _is_quota_error(exc):
                wait = _QUOTA_COOLDOWN_S
                logger.warning(
                    "Gemini embed hit the quota window; cooling down %ss (attempt %d/%d)",
                    wait,
                    _attempt + 1,
                    _MAX_EMBED_RETRIES,
                )
            else:
                wait = min(2**_attempt, 30)
                logger.warning("Gemini embed failed (%s); retry in %ss", exc, wait)
            time.sleep(wait)
            return self._embed_gemini(texts, _attempt + 1)

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
