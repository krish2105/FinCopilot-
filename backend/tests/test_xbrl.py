"""Phase 45: exact numeric facts from SEC XBRL.

The two bugs guarded here both produce *confidently wrong numbers*, which is the one
failure mode this product exists to prevent — so they get explicit tests.
"""

import pytest

from src.xbrl import lookup
from src.xbrl.concepts import match_metric


class _FakeDB:
    """Returns canned xbrl_facts rows; mimics Database.query/query_one."""

    def __init__(self, rows):
        self._rows = rows

    def query(self, sql, params=()):
        ticker, concept, form = params[0], params[1], params[2]
        return [
            r
            for r in self._rows
            if r["ticker"] == ticker and r["concept"] == concept and r["form"] == form
        ]

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None


def _row(concept, end, val, *, start=None, filed="2024-11-01", accn="a-1", fy=None):
    return {
        "ticker": "AAPL", "concept": concept, "unit": "USD", "period_end": end,
        "period_start": start, "fiscal_year": fy, "fiscal_period": "FY", "form": "10-K",
        "val": val, "accn": accn, "filed": filed,
    }


# --- metric matching ---------------------------------------------------------
def test_margin_means_a_ratio_not_a_dollar_amount():
    """'gross margin' once resolved to gross PROFIT, so Apple's margin came back as
    "$195,201,000,000" — a confidently wrong answer to the question asked."""
    assert match_metric("What is Apple's gross margin?") == "gross_margin_pct"
    assert match_metric("What is Apple's gross profit?") == "gross_profit"
    assert match_metric("net margin") == "net_margin_pct"


def test_longest_alias_wins():
    assert match_metric("operating income") == "operating_income"
    assert match_metric("net income") == "net_income"


def test_non_metric_question_matches_nothing():
    assert match_metric("What risk factors does Apple disclose?") is None


# --- the fiscal-year trap ----------------------------------------------------
def test_period_not_filing_year_determines_fiscal_year():
    """XBRL's `fy` is the fiscal year of the FILING, not of the fact. Apple's FY2025
    10-K restates FY2024 and FY2023, all tagged fy=2025. Keying on it shifted a 5-year
    revenue chart by two years."""
    rows = [
        # all three carry fy=2025 because they came from the FY2025 10-K
        _row("Revenues", "2025-09-27", 416_161_000_000, start="2024-09-29", fy=2025, accn="a25"),
        _row("Revenues", "2024-09-28", 391_035_000_000, start="2023-10-01", fy=2025, accn="a25"),
        _row("Revenues", "2023-09-30", 383_285_000_000, start="2022-10-02", fy=2025, accn="a25"),
    ]
    pts = lookup.series(_FakeDB(rows), "AAPL", "revenue", years=3)
    assert [p["fiscal_year"] for p in pts] == [2025, 2024, 2023]
    assert pts[1]["value"] == 391_035_000_000, "FY2024 must be FY2024's number"


def test_quarterly_rows_inside_a_10k_are_excluded():
    rows = [
        _row("Revenues", "2024-09-28", 391_035_000_000, start="2023-10-01"),  # ~annual
        _row("Revenues", "2024-06-29", 85_777_000_000, start="2024-03-31"),  # a quarter
    ]
    pts = lookup.series(_FakeDB(rows), "AAPL", "revenue", years=5)
    assert len(pts) == 1, "a 90-day span is a quarter, not a fiscal year"


def test_restatement_prefers_the_most_recently_filed_value():
    rows = [
        _row("Revenues", "2024-09-28", 100, start="2023-10-01", filed="2024-11-01", accn="orig"),
        _row("Revenues", "2024-09-28", 111, start="2023-10-01", filed="2025-11-01", accn="restated"),
    ]
    f = lookup.get_fact(_FakeDB(rows), "AAPL", "revenue")
    assert f["value"] == 111, "a restatement supersedes the original filing"


# --- the abandoned-tag trap --------------------------------------------------
def test_concept_chain_is_merged_not_first_match():
    """Companies abandon tags. Taking the first concept with ANY data returned NVDA's
    FY2022 revenue as the latest figure — off by ~$100bn."""
    rows = [
        # preferred concept, but only stale data
        _row("RevenueFromContractWithCustomerExcludingAssessedTax", "2022-01-30", 26_914_000_000,
             start="2021-02-01"),
        # fallback concept carries the recent years
        _row("Revenues", "2026-01-25", 215_900_000_000, start="2025-01-27"),
    ]
    f = lookup.get_fact(_FakeDB(rows), "AAPL", "revenue")
    assert f["fiscal_year"] == 2026, "must find the newest period across the whole chain"


# --- derived metrics ---------------------------------------------------------
def test_margin_is_computed_from_filed_values():
    rows = [
        _row("GrossProfit", "2024-09-28", 50, start="2023-10-01"),
        _row("Revenues", "2024-09-28", 200, start="2023-10-01"),
    ]
    d = lookup.derived(_FakeDB(rows), "AAPL", "gross_margin_pct")
    assert d["value"] == 25.0
    assert d["unit"] == "percent"
    assert d["components"]["revenue"] == 200


def test_answer_numeric_declines_a_non_metric_question():
    assert lookup.answer_numeric(_FakeDB([]), "What are the risk factors?", ["AAPL"]) is None


def test_answer_numeric_needs_a_ticker():
    assert lookup.answer_numeric(_FakeDB([]), "What was revenue?", None) is None
