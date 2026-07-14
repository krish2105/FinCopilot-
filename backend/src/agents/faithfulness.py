"""Self-RAG faithfulness gate (Phase 5).

Runs after synthesis. Verifies every claim in the drafted answer is supported by
the cited evidence; unsupported answers are refused ("insufficient evidence" +
what's missing) rather than returned.

Two layers:
  * A hard, always-on **numeric grounding** guardrail — every number in the answer
    must appear in the retrieved evidence. This blocks hallucinated figures
    regardless of what an LLM claims, honoring the plan's "uncited numbers are
    blocked" rule.
  * A semantic faithfulness check — LLM (structured) when live, deterministic
    lexical-grounding fallback offline. The LLM can only make the verdict
    stricter; it can never override the numeric guardrail.
"""

from __future__ import annotations

import logging
import re

from src.agents.schemas import FaithfulnessVerdict
from src.providers.router import ProviderRouter
from src.retrieval.types import RetrievalResult

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MARKER_RE = re.compile(r"\[\d+\]")
_WORD_RE = re.compile(r"[a-z0-9]+")
# A "number" worth grounding: money/percent/scaled/decimal/thousands (not a bare
# 1-2 digit int, which is too noisy and usually not a factual figure).
_ANSWER_NUM_RE = re.compile(
    r"\$?\d[\d,]*(?:\.\d+)?\s?(?:billion|million|thousand|bn|mm|%)?", re.IGNORECASE
)

_MIN_OVERLAP = 0.18  # below this, a marker-less sentence is deemed unsupported

# The "refuses to guess" promise is enforced by the *hard* guardrails: a figure that
# isn't in the evidence, or arithmetic that doesn't compute, refuses unconditionally
# and deterministically. Those are the claims that actually hurt someone.
#
# Semantic doubt from an LLM judge is fuzzy by comparison, so it only refuses when it
# overwhelms the answer (2/3+ of it). An earlier, stricter rule refused 56% of all
# FinanceBench answers — it was discarding correct, fully-cited work.
_MIN_FAITHFUL_SCORE = 0.34

_FAITH_SYSTEM = (
    "You are a fact-checker for a financial research assistant. Given an ANSWER and "
    "the EVIDENCE it was drawn from, identify only claims that are FABRICATED or "
    "CONTRADICTED by the evidence.\n\n"
    "These are SUPPORTED — do NOT flag them:\n"
    "- A claim that synthesises or aggregates across several pieces of evidence "
    "(e.g. 'both companies cite competition risk' when each says so separately). "
    "Combining evidence is the assistant's job, not a fabrication.\n"
    "- A paraphrase, summary, or restatement in different words.\n"
    "- A hedge or qualifier (e.g. 'the filing does not quantify this').\n"
    "- A statement about what the evidence does NOT say.\n\n"
    "Flag a claim ONLY if the evidence contradicts it, or if it asserts a specific "
    "fact or figure that appears nowhere in the evidence. When genuinely in doubt, "
    "treat the claim as supported."
)


def _norm_num(token: str) -> str:
    return re.sub(r"[^\d]", "", token)


def _is_groundable_text(text: str) -> bool:
    """True if `text` carries a figure worth grounding (money/percent/scale/3+ digits)."""
    return any(_is_groundable(m.group(0).strip().rstrip(",.")) for m in _ANSWER_NUM_RE.finditer(text))


def _is_groundable(token: str) -> bool:
    low = token.lower()
    if any(c in token for c in "$%") or any(
        w in low for w in ("billion", "million", "thousand", "bn", "mm")
    ):
        return True
    core = _norm_num(token)
    return len(core) >= 3  # 3+ digit figure


def verify(
    router: ProviderRouter,
    answer: str,
    retrieval: RetrievalResult | None,
    trace: list | None = None,
) -> FaithfulnessVerdict:
    if not answer.strip():
        return FaithfulnessVerdict(faithful=False, score=0.0, reason="Empty answer.")
    if not retrieval or not retrieval.chunks:
        return FaithfulnessVerdict(
            faithful=False, score=0.0, reason="No evidence to support the answer."
        )

    evidence_text = " ".join(" ".join(c.text.split()) for c in retrieval.chunks)
    evidence_digits = _norm_num(evidence_text)
    evidence_words = set(_WORD_RE.findall(evidence_text.lower()))

    # --- hard numeric guardrail ---
    ungrounded_numbers: list[str] = []
    for m in _ANSWER_NUM_RE.finditer(answer):
        token = m.group(0).strip().rstrip(",.")
        if not _is_groundable(token):
            continue
        core = _norm_num(token)
        if core and core not in evidence_digits:
            ungrounded_numbers.append(token)

    # --- exact-arithmetic guardrail (Phase 26) ---
    # Any explicit "A op B = C" the answer states must actually compute to C.
    from src.agents.calculator import verify_arithmetic

    arithmetic_errors = [
        f"arithmetic error: {e['expression']} (correct: {e['correct']})"
        for e in verify_arithmetic(answer)
    ]

    # --- semantic grounding ---
    # The lexical-overlap heuristic is a *fallback* for the offline extractive
    # stack, where answers copy evidence verbatim so overlap is naturally high.
    # A live LLM paraphrases, so well-grounded prose scores low on word overlap
    # and would be falsely refused. When an LLM is available we let it judge
    # semantic support (see _llm_refine) and keep only the hard, precise
    # guardrails here — ungrounded numbers and bad arithmetic — which no
    # paraphrase can excuse.
    live = router.mode != "stub"
    unsupported: list[str] = list(arithmetic_errors)
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(answer) if s.strip()]
    if not live:
        for sent in sentences:
            clean = _MARKER_RE.sub("", sent).strip()
            words = _WORD_RE.findall(clean.lower())
            if len(words) < 4:
                continue
            overlap = sum(1 for w in words if w in evidence_words) / len(words)
            has_marker = bool(_MARKER_RE.search(sent))
            if overlap < _MIN_OVERLAP and not has_marker:
                unsupported.append(clean[:120])

    verdict = _decide(sentences, unsupported, ungrounded_numbers, arithmetic_errors)

    # Live: the LLM judges semantic support. It can never excuse an ungrounded
    # number or a bad calculation — those guardrails are already baked into
    # `verdict` and are preserved through the refinement.
    if live:
        verdict = _llm_refine(
            router, answer, evidence_text, verdict, trace, sentences, arithmetic_errors
        )

    logger.info("faithfulness: %s score=%.2f", verdict.faithful, verdict.score)
    return verdict


def _decide(
    sentences: list[str],
    unsupported: list[str],
    ungrounded_numbers: list[str],
    arithmetic_errors: list[str],
) -> FaithfulnessVerdict:
    """Turn the individual checks into a verdict.

    Two classes of problem, deliberately treated differently:

    * **Hard** — an ungrounded figure or a wrong calculation. These are precise,
      objective, and exactly what this product promises never to emit. Any single
      one refuses the answer.
    * **Soft** — a claim a judge merely *thinks* isn't clearly supported. Judges are
      conservative and routinely flag a hedge or a summarising sentence. Refusing a
      well-cited answer over one such sentence throws away a good answer, so soft
      doubts are scored: we only refuse when they dominate the answer.
    """
    total = max(1, len(sentences))
    soft = [u for u in unsupported if u not in arithmetic_errors]
    score = max(0.0, 1.0 - (len(unsupported) + len(ungrounded_numbers)) / total)

    # A flagged claim that carries a *figure* is material — a wrong number is the harm
    # this product exists to prevent, so it refuses even if the rest of the answer is
    # fine. A flagged claim that is only prose is not, on its own, worth discarding a
    # cited answer over.
    material = [u for u in soft if _ANSWER_NUM_RE.search(u) and _is_groundable_text(u)]

    hard_fail = bool(ungrounded_numbers) or bool(arithmetic_errors) or bool(material)
    faithful = not hard_fail and score >= _MIN_FAITHFUL_SCORE

    return FaithfulnessVerdict(
        faithful=faithful,
        score=round(score, 3),
        unsupported_claims=unsupported,
        ungrounded_numbers=ungrounded_numbers,
        reason=_reason(ungrounded_numbers, soft),
    )


def _reason(ungrounded: list[str], unsupported: list[str]) -> str:
    if not ungrounded and not unsupported:
        return "All claims grounded in cited evidence."
    parts = []
    if ungrounded:
        parts.append(f"ungrounded figures: {', '.join(ungrounded[:5])}")
    if unsupported:
        parts.append(f"{len(unsupported)} unsupported statement(s)")
    return "; ".join(parts)


def _llm_refine(
    router: ProviderRouter,
    answer: str,
    evidence_text: str,
    base: FaithfulnessVerdict,
    trace: list | None,
    sentences: list[str] | None = None,
    arithmetic_errors: list[str] | None = None,
) -> FaithfulnessVerdict:
    prompt = (
        f"Evidence:\n{evidence_text[:6000]}\n\nAnswer:\n{answer}\n\n"
        "Is every factual claim in the answer supported by the evidence?"
    )
    llm = router.structured(
        prompt, FaithfulnessVerdict, system=_FAITH_SYSTEM, stub=lambda: base, trace=trace
    )
    # Union the doubts, then apply the same rule as everywhere else: hard guardrails
    # (ungrounded figures, bad arithmetic) refuse outright; the judge's semantic
    # doubts are scored, so one flagged sentence can't discard a well-cited answer.
    unsupported = sorted(set(base.unsupported_claims) | set(llm.unsupported_claims))
    return _decide(
        sentences or [],
        unsupported,
        base.ungrounded_numbers,
        arithmetic_errors or [],
    )
