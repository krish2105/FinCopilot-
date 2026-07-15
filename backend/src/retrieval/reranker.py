"""Cross-encoder reranker (Phase 44).

The reranker is the single dominant component in a RAG stack — an ablation across
HetDocQA/MuSiQue/QASPER found that removing the cross-encoder collapsed nDCG@10 from
0.644 to 0.034, a bigger effect than GraphRAG, routing, fusion and corrective
re-retrieval *combined* (arXiv 2606.28367). Yet this service ran for weeks on the
lexical fallback, because the cross-encoder was loaded through sentence-transformers,
which drags in torch — far too heavy for a 512 MB free instance.

So we run the same model through **ONNX Runtime, int8-quantized**: ~20 MB of weights,
CPU-only, no torch, tens of milliseconds per batch. Backends, in order:

1. ``onnx``          — quantized cross-encoder. The production path.
2. ``cross-encoder`` — sentence-transformers, if torch happens to be installed (dev).
3. ``lexical``       — deterministic term-coverage score. CI/offline; never a silent
                       production default again (it logs loudly).
"""

from __future__ import annotations

import logging
import math
import re

from src.config.settings import Settings, get_settings
from src.retrieval.types import RetrievedChunk

logger = logging.getLogger(__name__)

_CE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Same model, exported to ONNX and int8-quantized (~20 MB, no torch).
_ONNX_REPO = "Xenova/ms-marco-MiniLM-L-6-v2"
_ONNX_FILE = "onnx/model_quantized.onnx"
_MAX_LEN = 512
_BATCH = 16  # keeps peak memory small on a 512 MB instance

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def resolve_rerank_backend(settings: Settings) -> str:
    choice = settings.fincopilot_rerank_backend.lower()
    if choice in ("onnx", "cross-encoder", "lexical"):
        return choice
    # "auto"
    if settings.fincopilot_offline_mode:
        return "lexical"
    return "onnx"


class Reranker:
    _NAMES = {
        "onnx": f"{_CE_MODEL} (onnx-int8)",
        "cross-encoder": _CE_MODEL,
        "lexical": "lexical-v1",
    }

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.backend = resolve_rerank_backend(self.settings)
        self._session = None
        self._tokenizer = None
        self._ce = None
        # The cross-encoder is ~184 MB resident. Load it lazily on the first rerank so
        # startup and light endpoints (stats, XBRL, valuation) never pay for it — that
        # matters on a 512 MB instance.
        self._loaded = self.backend == "lexical"
        self.name = self._NAMES[self.backend]

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.backend == "onnx" and not self._try_load_onnx():
            logger.warning("ONNX reranker unavailable; trying sentence-transformers")
            self.backend = "cross-encoder"
        if self.backend == "cross-encoder" and not self._try_load_ce():
            logger.warning(
                "NO CROSS-ENCODER — falling back to the lexical reranker. Retrieval "
                "quality is materially degraded; install onnxruntime + tokenizers."
            )
            self.backend = "lexical"
        self.name = self._NAMES[self.backend]

    # --- loading -------------------------------------------------------------
    def _try_load_onnx(self) -> bool:
        try:
            import onnxruntime as ort
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer
        except Exception as exc:  # noqa: BLE001
            logger.info("onnx deps unavailable: %s", exc)
            return False
        try:
            model_path = hf_hub_download(_ONNX_REPO, _ONNX_FILE)
            tok_path = hf_hub_download(_ONNX_REPO, "tokenizer.json")

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1  # free tier is ~1 vCPU; more threads only thrash
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                model_path, sess_options=opts, providers=["CPUExecutionProvider"]
            )

            tok = Tokenizer.from_file(tok_path)
            tok.enable_truncation(max_length=_MAX_LEN)
            tok.enable_padding()
            self._tokenizer = tok
            logger.info("ONNX cross-encoder ready (%s)", _ONNX_REPO)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load ONNX reranker: %s", exc)
            return False

    def _try_load_ce(self) -> bool:
        try:
            from sentence_transformers import CrossEncoder
        except Exception:
            return False
        try:
            self._ce = CrossEncoder(_CE_MODEL)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load %s: %s", _CE_MODEL, exc)
            return False

    # --- scoring -------------------------------------------------------------
    def _onnx_scores(self, query: str, texts: list[str]) -> list[float]:
        import numpy as np

        input_names = {i.name for i in self._session.get_inputs()}
        scores: list[float] = []
        for i in range(0, len(texts), _BATCH):
            window = texts[i : i + _BATCH]
            encs = self._tokenizer.encode_batch([(query, t) for t in window])
            feed = {
                "input_ids": np.array([e.ids for e in encs], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encs], dtype=np.int64),
            }
            if "token_type_ids" in input_names:
                feed["token_type_ids"] = np.array([e.type_ids for e in encs], dtype=np.int64)
            logits = self._session.run(None, feed)[0]
            scores.extend(float(x) for x in np.asarray(logits).reshape(len(window), -1)[:, 0])
        return scores

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int = 6
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        self._ensure_loaded()

        if self.backend == "onnx":
            try:
                for c, s in zip(chunks, self._onnx_scores(query, [c.text for c in chunks]), strict=True):
                    c.rerank_score = s
            except Exception as exc:  # noqa: BLE001
                logger.warning("ONNX rerank failed (%s); using lexical for this query", exc)
                self._lexical(query, chunks)
        elif self.backend == "cross-encoder":
            for c, s in zip(chunks, self._ce.predict([(query, c.text) for c in chunks]), strict=True):
                c.rerank_score = float(s)
        else:
            self._lexical(query, chunks)

        ranked = sorted(chunks, key=lambda c: c.rerank_score, reverse=True)
        return adaptive_k(ranked, top_k)

    def _lexical(self, query: str, chunks: list[RetrievedChunk]) -> None:
        q_tokens = set(_TOKEN_RE.findall(query.lower()))
        for c in chunks:
            c.rerank_score = _lexical_score(q_tokens, c.text)


# --- Adaptive-k (Phase 44) ---------------------------------------------------
# Instead of always taking a fixed top-k, cut at the largest *drop* in reranker
# score: the point where relevance falls off a cliff. Keeps genuinely relevant
# evidence when there's a lot of it, and drops distractors when there isn't —
# which also helps the faithfulness gate, since fewer distractors means fewer
# unsupported-looking claims. No tuning, no extra model call. (EMNLP 2025)
_ADAPTIVE_BUFFER = 2  # keep a couple past the cliff; recall matters more than precision here
_MIN_KEEP = 3
# The drop must account for this share of the whole score range to count as a cliff.
# Without it, a smoothly-decaying list (every candidate useful) gets trimmed for no reason.
_CLIFF_SHARE = 0.35


def adaptive_k(ranked: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if len(ranked) <= _MIN_KEEP:
        return ranked[:top_k]

    window = ranked[:top_k]
    scores = [c.rerank_score for c in window]
    gaps = [scores[i] - scores[i + 1] for i in range(len(scores) - 1)]
    if not gaps:
        return window

    span = scores[0] - scores[-1]
    max_gap = max(gaps)
    # Only cut at a genuine cliff. If relevance decays smoothly, every candidate is
    # plausibly useful and trimming would just throw away recall.
    if span <= 0 or max_gap < _CLIFF_SHARE * span:
        return window

    cut = gaps.index(max_gap) + 1  # keep everything above the cliff
    keep = max(_MIN_KEEP, min(top_k, cut + _ADAPTIVE_BUFFER))
    return window[:keep]


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
