"""Evaluation metrics.

Deterministic metrics (always computed, no LLM/API needed — these are the real
published numbers):
  * context_hit        — did retrieval surface the question's own gold source?
  * answer_match       — does the generated answer contain the gold answer?
  * faithful_rate      — Self-RAG gate verdict pass rate
  * citation_coverage  — answers carrying at least one citation
  * refusal_rate       — honest "insufficient evidence" rate
  * avg_latency_ms

Canonical RAGAS metrics (faithfulness, answer_relevancy, context_precision,
context_recall) are computed by `compute_ragas` when an LLM is configured (needs
GEMINI/OpenAI key + ragas). Guarded — returns None if unavailable.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"-?\(?\$?\d[\d,]*(?:\.\d+)?\)?")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the",
    "and",
    "for",
    "was",
    "were",
    "with",
    "that",
    "this",
    "from",
    "are",
    "based",
    "response",
    "question",
    "company",
    "usd",
    "millions",
    "million",
    "billion",
    "answer",
    "value",
    "give",
    "relying",
    "details",
    "shown",
}


def number_tokens(text: str) -> set[str]:
    """Integer-part digit strings (>=2 digits) of each numeric token."""
    out: set[str] = set()
    for m in _NUM_RE.finditer(text):
        digits = re.sub(r"[^\d]", "", m.group(0).split(".")[0])
        if len(digits) >= 2:
            out.add(digits.lstrip("0") or digits)
    return out


def _content_words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOP and len(w) > 2}


def answer_matches(gold: str, candidate: str) -> bool:
    gold_nums = number_tokens(gold)
    if gold_nums:
        return bool(gold_nums & number_tokens(candidate))
    # Non-numeric gold: token-overlap heuristic.
    g = _content_words(gold)
    if not g:
        return False
    overlap = len(g & _content_words(candidate)) / len(g)
    return overlap >= 0.5


def aggregate(per_question: list[dict]) -> dict:
    n = len(per_question) or 1

    def mean(key: str) -> float:
        return round(sum(float(r[key]) for r in per_question) / n, 4)

    return {
        "n_questions": len(per_question),
        "context_hit": mean("context_hit"),
        "answer_match": mean("answer_match"),
        "faithful_rate": mean("faithful"),
        "citation_coverage": mean("has_citation"),
        "refusal_rate": mean("refused"),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in per_question) / n, 1),
    }


def compute_ragas(records: list[dict]) -> dict | None:
    """Canonical RAGAS metrics. Requires a configured LLM + ragas; else None.

    `records`: [{question, answer, contexts:[str], ground_truth}]
    """
    try:
        import os

        if not (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
            logger.info("RAGAS skipped: no LLM key configured")
            return None
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        ds = Dataset.from_list(
            [
                {
                    "question": r["question"],
                    "answer": r["answer"],
                    "contexts": r["contexts"],
                    "ground_truth": r["ground_truth"],
                }
                for r in records
                if r["answer"] and r["contexts"]
            ]
        )
        result = evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        return {k: round(float(v), 4) for k, v in result.items()}
    except Exception as exc:  # missing deps / key / runtime — never fail the run
        logger.warning("RAGAS unavailable: %s", exc)
        return None
