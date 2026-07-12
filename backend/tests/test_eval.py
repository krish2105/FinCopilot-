from src.evaluation import metrics as M
from src.evaluation.dataset import load_questions


def test_number_tokens():
    toks = M.number_tokens("The FY2018 capital expenditure was $1,577.00 million")
    assert "1577" in toks
    assert "2018" in toks


def test_answer_matches_numeric():
    assert M.answer_matches("$1577.00", "Capex was $1,577 million that year.")
    assert not M.answer_matches("$1577.00", "Revenue was $8,900 million.")


def test_answer_matches_textual():
    gold = "No material pending legal proceedings"
    assert M.answer_matches(gold, "There are no material pending legal proceedings disclosed.")
    assert not M.answer_matches(gold, "Revenue grew on strong iPhone demand.")


def test_aggregate():
    rows = [
        {
            "context_hit": 1,
            "answer_match": 1,
            "faithful": 1,
            "has_citation": 1,
            "refused": 0,
            "latency_ms": 100,
        },
        {
            "context_hit": 1,
            "answer_match": 0,
            "faithful": 1,
            "has_citation": 1,
            "refused": 0,
            "latency_ms": 200,
        },
    ]
    agg = M.aggregate(rows)
    assert agg["n_questions"] == 2
    assert agg["context_hit"] == 1.0
    assert agg["answer_match"] == 0.5
    assert agg["avg_latency_ms"] == 150.0


def test_ragas_skipped_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert (
        M.compute_ragas([{"question": "q", "answer": "a", "contexts": ["c"], "ground_truth": "g"}])
        is None
    )


def test_dataset_loads_real_questions():
    qs = load_questions()
    assert len(qs) >= 20
    q = qs[0]
    assert q.benchmark == "FinanceBench"
    assert q.question and q.answer and q.evidence
    assert q.ticker
