"""Phase 49: personalization profile derived from the audit trail."""

from src.tenancy import profile


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, sql, params=()):
        return self._rows

    def query_one(self, sql, params=()):
        return {"n": len(self._rows)}


def _audit(query, tickers, route="hybrid", verdict="ok"):
    return {"query": query, "tickers": ",".join(tickers), "route": route, "verdict": verdict}


def test_profile_ranks_most_researched_tickers():
    # repo.recent_audit splits tickers into a list; emulate that shape here.
    rows = [
        {"query": "Apple revenue?", "tickers": ["AAPL"], "route": "hybrid", "verdict": "ok"},
        {"query": "Apple risks?", "tickers": ["AAPL"], "route": "hybrid", "verdict": "ok"},
        {"query": "Microsoft cloud?", "tickers": ["MSFT"], "route": "hybrid", "verdict": "ok"},
    ]
    import src.tenancy.repo as repo

    # patch recent_audit/audit_count to use our rows directly
    orig_recent, orig_count = repo.recent_audit, repo.audit_count
    repo.recent_audit = lambda db, org, limit=200: rows
    repo.audit_count = lambda db, org: len(rows)
    try:
        p = profile.build_profile(_FakeDB(rows), "org1")
    finally:
        repo.recent_audit, repo.audit_count = orig_recent, orig_count

    assert p["returning"] is True
    assert p["top_tickers"][0] == "AAPL", "most-researched ticker leads"
    assert "MSFT" in p["top_tickers"]
    assert p["total_queries"] == 3


def test_profile_dedupes_recent_questions():
    rows = [
        {"query": "Apple revenue?", "tickers": ["AAPL"], "route": "hybrid", "verdict": "ok"},
        {"query": "apple revenue?", "tickers": ["AAPL"], "route": "hybrid", "verdict": "ok"},
    ]
    import src.tenancy.repo as repo

    orig_recent, orig_count = repo.recent_audit, repo.audit_count
    repo.recent_audit = lambda db, org, limit=200: rows
    repo.audit_count = lambda db, org: len(rows)
    try:
        p = profile.build_profile(_FakeDB(rows), "org1")
    finally:
        repo.recent_audit, repo.audit_count = orig_recent, orig_count

    assert len(p["recent_questions"]) == 1, "case-insensitive dedupe of recent questions"


def test_empty_profile_is_not_returning():
    import src.tenancy.repo as repo

    orig_recent, orig_count = repo.recent_audit, repo.audit_count
    repo.recent_audit = lambda db, org, limit=200: []
    repo.audit_count = lambda db, org: 0
    try:
        p = profile.build_profile(_FakeDB([]), "org1")
    finally:
        repo.recent_audit, repo.audit_count = orig_recent, orig_count
    assert p["returning"] is False
    assert p["top_tickers"] == []
