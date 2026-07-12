"""Phase 26: exact-arithmetic tool + faithfulness guardrail."""

from src.agents.calculator import (
    cagr,
    percent_change,
    ratio,
    safe_eval,
    verify_arithmetic,
)


def test_safe_eval_basic():
    assert safe_eval("2 + 3 * 4") == 14.0
    assert safe_eval("(391035 - 365817) / 365817 * 100") == (391035 - 365817) / 365817 * 100
    assert safe_eval("2 ** 10") == 1024.0


def test_safe_eval_rejects_unsafe():
    assert safe_eval("__import__('os')") is None
    assert safe_eval("len([1,2,3])") is None
    assert safe_eval("a + b") is None
    assert safe_eval("1/0") is None  # ZeroDivisionError -> None


def test_finance_helpers():
    assert round(percent_change(100, 125), 2) == 25.0
    assert percent_change(0, 5) is None
    assert round(cagr(100, 200, 3), 2) == 25.99
    assert cagr(-1, 200, 3) is None
    assert ratio(10, 4) == 2.5
    assert ratio(10, 0) is None


def test_verify_arithmetic_flags_wrong():
    errs = verify_arithmetic("Revenue grew: 100 + 100 = 250, a big jump.")
    assert len(errs) == 1
    assert errs[0]["correct"] == 200.0


def test_verify_arithmetic_passes_correct():
    assert verify_arithmetic("Margin math: 20 / 100 = 0.2 holds.") == []


def test_verify_arithmetic_tolerates_rounding():
    # 25218 / 365817 = 0.0689... commonly written as 0.07
    assert verify_arithmetic("ratio 25218 / 365817 = 0.07") == []
