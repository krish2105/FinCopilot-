"""Visualization agent — builds chart specs from VALIDATED figures only.

Deterministic: turns numeric analyst findings into a Recharts-friendly ChartSpec.
The frontend (Phase 6) renders these; here we only emit the data contract. Only
figures that parse to a real number are charted (never fabricated).
"""

from __future__ import annotations

import re

from src.agents.schemas import (
    AnalystOutput,
    ChartPoint,
    ChartSeries,
    ChartSpec,
    VizOutput,
)

_NUMERIC = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_SCALE = {"billion": 1e9, "bn": 1e9, "million": 1e6, "mm": 1e6, "thousand": 1e3}


def _to_number(value: str) -> float | None:
    m = _NUMERIC.search(value)
    if not m:
        return None
    num = float(m.group(0).replace(",", ""))
    low = value.lower()
    for word, mult in _SCALE.items():
        if word in low:
            num *= mult
            break
    return num


def build(analyst: AnalystOutput | None) -> VizOutput:
    if not analyst or not analyst.findings:
        return VizOutput()

    points: list[ChartPoint] = []
    seen_labels: set[str] = set()
    for f in analyst.findings:
        if f.kind == "ratio":
            continue  # charts are for absolute figures; ratios shown as findings
        num = _to_number(f.value)
        if num is None:
            continue
        label = f.label[:40] or f.citation_marker or "figure"
        if label in seen_labels:
            continue
        seen_labels.add(label)
        points.append(ChartPoint(x=label, y=num))
        if len(points) >= 8:
            break

    if not points:
        return VizOutput()

    chart = ChartSpec(
        type="bar",
        title="Key figures from the evidence",
        x_label="Metric",
        y_label="Value",
        series=[ChartSeries(name="value", points=points)],
    )
    return VizOutput(charts=[chart])
