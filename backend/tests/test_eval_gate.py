"""Phase 28: eval-as-a-CI-gate.

Runs the full agent pipeline over a real FinanceBench sample offline and **fails
the build** if core retrieval/grounding quality regresses below the committed
baseline. Because CI runs pytest, this is the PR-blocking quality gate: a change
that quietly breaks retrieval or the faithfulness guarantees can't merge.

Thresholds are conservative (headroom over observed offline scores) so they catch
real regressions, not noise. Tighten them as quality improves.
"""

from src.evaluation.harness import run_eval

# Committed baseline for the deterministic offline stack (hash/local embeddings,
# lexical reranker, extractive synthesizer — no API key).
BASELINE = {
    "context_hit": 0.90,  # retrieved the correct gold source
    "citation_coverage": 1.0,  # every answer is cited
    "faithful_rate": 1.0,  # Self-RAG gate passes (grounded or honestly refused)
    "max_refusal_rate": 0.10,  # extractive answers shouldn't mass-refuse
}

GATE_SAMPLE = 12  # enough signal to catch regressions; fast enough for CI


def test_eval_quality_gate(settings):
    m = run_eval(settings, limit=GATE_SAMPLE, write=False)["metrics"]
    assert m["context_hit"] >= BASELINE["context_hit"], (
        f"retrieval regressed: context_hit={m['context_hit']:.2f} < {BASELINE['context_hit']}"
    )
    assert m["citation_coverage"] >= BASELINE["citation_coverage"], "answers no longer fully cited"
    assert m["faithful_rate"] >= BASELINE["faithful_rate"], (
        "faithfulness gate regressed — answers no longer fully grounded/refused"
    )
    assert m["refusal_rate"] <= BASELINE["max_refusal_rate"], (
        f"refusal rate too high: {m['refusal_rate']:.2f} > {BASELINE['max_refusal_rate']}"
    )
