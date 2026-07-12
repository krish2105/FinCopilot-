import os

from src.audit.log import AuditLog, AuditRecord


def _log(settings):
    return AuditLog(os.path.join(settings.data_dir, "audit.jsonl"))


def test_record_and_read_back(settings):
    log = _log(settings)
    log.record(AuditRecord(query="q1", route="hybrid", verdict="ok"))
    log.record(AuditRecord(query="q2", route="graphrag", verdict="insufficient_evidence"))
    recent = log.recent()
    assert log.count() == 2
    assert recent[0].query == "q2"  # newest first
    assert recent[1].query == "q1"


def test_recent_limit(settings):
    log = _log(settings)
    for i in range(5):
        log.record(AuditRecord(query=f"q{i}"))
    assert len(log.recent(limit=3)) == 3


def test_record_captures_fields(settings):
    log = _log(settings)
    log.record(
        AuditRecord(
            query="q",
            tickers=["AAPL"],
            planned_route="relationship",
            route="graphrag",
            sources=["AAPL 10-K p.1"],
            providers=["stub:stub-llm-v1"],
            faithfulness_score=0.9,
            latency_ms=42,
        )
    )
    r = log.recent()[0]
    assert r.tickers == ["AAPL"]
    assert r.providers == ["stub:stub-llm-v1"]
    assert r.id and r.timestamp


def test_missing_file_is_empty(settings):
    assert _log(settings).recent() == []
    assert _log(settings).count() == 0
