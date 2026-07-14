"""Phase 48: two-stage DCF. Pure, deterministic math — the model computes, the LLM never does."""

import pytest

from src.valuation.dcf import DcfAssumptions, run_dcf, sensitivity


def test_projected_fcf_grows_at_the_growth_rate():
    r = run_dcf(DcfAssumptions(base_fcf=100.0, growth_rate=0.10, years=3))
    assert r.projected_fcf[0]["fcf"] == pytest.approx(110.0)
    assert r.projected_fcf[1]["fcf"] == pytest.approx(121.0)
    assert r.projected_fcf[2]["fcf"] == pytest.approx(133.1)


def test_present_value_discounts_correctly():
    r = run_dcf(DcfAssumptions(base_fcf=100.0, growth_rate=0.0, discount_rate=0.10, years=1, terminal_growth=0.0))
    # FCF yr1 = 100, PV = 100/1.1
    assert r.projected_fcf[0]["pv"] == pytest.approx(90.909, abs=0.01)


def test_per_share_needs_shares():
    assert run_dcf(DcfAssumptions(base_fcf=100.0, shares=None)).fair_value_per_share is None
    assert run_dcf(DcfAssumptions(base_fcf=100.0, shares=10.0)).fair_value_per_share is not None


def test_net_cash_lifts_equity_above_enterprise_value():
    r = run_dcf(DcfAssumptions(base_fcf=100.0, net_cash=500.0))
    assert r.equity_value == pytest.approx(r.enterprise_value + 500.0)


def test_terminal_growth_cannot_exceed_discount_rate():
    # Gordon growth diverges if terminal >= discount; the model must clamp, not explode.
    r = run_dcf(DcfAssumptions(base_fcf=100.0, discount_rate=0.05, terminal_growth=0.08))
    assert r.terminal_value > 0 and r.enterprise_value > 0


def test_higher_discount_rate_lowers_value():
    low = run_dcf(DcfAssumptions(base_fcf=100.0, discount_rate=0.07, shares=1.0)).fair_value_per_share
    high = run_dcf(DcfAssumptions(base_fcf=100.0, discount_rate=0.12, shares=1.0)).fair_value_per_share
    assert high < low, "a higher required return must mean a lower fair value"


def test_sensitivity_grid_shape():
    grid = sensitivity(DcfAssumptions(base_fcf=100.0, shares=1.0))
    assert len(grid["grid"]) == len(grid["growth_rates"])
    assert len(grid["grid"][0]) == len(grid["discount_rates"])
