"""Two-stage discounted-cash-flow model (Phase 48).

A deliberate division of labour: **the model does the arithmetic, the LLM never does.**
An LLM may *suggest* assumptions (growth, discount rate) and *explain* the result, but
every number here is computed deterministically from the company's own filed free cash
flow. That is the only defensible way to put a "fair value" in front of a user — a
transparent calculator whose inputs they can see and change, not a figure a model made
up.

Free cash flow, growth and discount rates all come from, or are anchored to, SEC XBRL
facts (Phase 45), so the starting point is real. Everything is overridable.

This is a valuation *tool*, not investment advice — the output is only ever as good as
its assumptions, which is exactly why they're explicit and editable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DcfAssumptions:
    base_fcf: float  # most recent annual free cash flow (currency units)
    growth_rate: float = 0.10  # stage-1 annual FCF growth (decimal)
    terminal_growth: float = 0.025  # perpetual growth after the projection window
    discount_rate: float = 0.09  # WACC / required return (decimal)
    years: int = 5  # length of stage 1
    net_cash: float = 0.0  # cash minus debt, added to enterprise value
    shares: float | None = None  # diluted shares outstanding


@dataclass
class DcfResult:
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float | None
    projected_fcf: list[dict] = field(default_factory=list)
    terminal_value: float = 0.0
    pv_terminal: float = 0.0
    assumptions: dict = field(default_factory=dict)


def run_dcf(a: DcfAssumptions) -> DcfResult:
    """A textbook two-stage DCF. Every step is explicit so it can be audited."""
    if a.discount_rate <= a.terminal_growth:
        # Gordon growth diverges otherwise; clamp to keep the model finite and honest.
        a.terminal_growth = a.discount_rate - 0.005

    projected: list[dict] = []
    pv_sum = 0.0
    fcf = a.base_fcf
    for year in range(1, a.years + 1):
        fcf = fcf * (1 + a.growth_rate)
        discount = (1 + a.discount_rate) ** year
        pv = fcf / discount
        pv_sum += pv
        projected.append(
            {"year": year, "fcf": round(fcf, 2), "pv": round(pv, 2), "discount_factor": round(1 / discount, 4)}
        )

    # Terminal value via Gordon growth on the final projected FCF.
    final_fcf = fcf * (1 + a.terminal_growth)
    terminal_value = final_fcf / (a.discount_rate - a.terminal_growth)
    pv_terminal = terminal_value / ((1 + a.discount_rate) ** a.years)

    enterprise_value = pv_sum + pv_terminal
    equity_value = enterprise_value + a.net_cash
    per_share = equity_value / a.shares if a.shares else None

    return DcfResult(
        enterprise_value=round(enterprise_value, 2),
        equity_value=round(equity_value, 2),
        fair_value_per_share=round(per_share, 2) if per_share is not None else None,
        projected_fcf=projected,
        terminal_value=round(terminal_value, 2),
        pv_terminal=round(pv_terminal, 2),
        assumptions=a.__dict__.copy(),
    )


def sensitivity(
    a: DcfAssumptions,
    growth_range: list[float] | None = None,
    discount_range: list[float] | None = None,
) -> dict:
    """Fair-value-per-share across a grid of growth × discount rate.

    The single most honest thing a DCF can show: not one false-precision number, but how
    the answer moves with the two assumptions it's most sensitive to. This is what the
    frontend renders as a heatmap.
    """
    growth_range = growth_range or [a.growth_rate + d for d in (-0.04, -0.02, 0, 0.02, 0.04)]
    discount_range = discount_range or [a.discount_rate + d for d in (-0.02, -0.01, 0, 0.01, 0.02)]

    grid: list[list[float | None]] = []
    for g in growth_range:
        row: list[float | None] = []
        for r in discount_range:
            variant = DcfAssumptions(**{**a.__dict__, "growth_rate": g, "discount_rate": r})
            row.append(run_dcf(variant).fair_value_per_share)
        grid.append(row)

    return {
        "growth_rates": [round(g, 4) for g in growth_range],
        "discount_rates": [round(r, 4) for r in discount_range],
        "grid": grid,
    }
