"""Typed structured outputs for every agent (no fragile regex parsing).

These are the contracts the LLM must fill (or the deterministic stub builds) and
what the API returns.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.retrieval.types import Citation


class Finding(BaseModel):
    """A single analytic claim tied to a source via its citation marker."""

    label: str  # e.g. "Total net sales FY2024" or "Current ratio"
    value: str  # e.g. "$391,035M" or "1.07"
    citation_marker: str = ""  # "[2]" — must reference a real citation
    kind: str = "figure"  # "figure" | "ratio" | "trend"


class AnalystOutput(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    notes: str = ""


class ComplianceFlag(BaseModel):
    category: str  # going_concern | restatement | litigation | material_weakness | ...
    detail: str
    citation_marker: str = ""


class ComplianceOutput(BaseModel):
    verdict: str = "ok"  # "ok" | "insufficient_evidence"
    flags: list[ComplianceFlag] = Field(default_factory=list)
    reason: str = ""
    uncited_findings: list[str] = Field(default_factory=list)


class ChartPoint(BaseModel):
    x: str
    y: float


class ChartSeries(BaseModel):
    name: str
    points: list[ChartPoint] = Field(default_factory=list)


class ChartSpec(BaseModel):
    type: str = "bar"  # "bar" | "line"
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    series: list[ChartSeries] = Field(default_factory=list)


class VizOutput(BaseModel):
    charts: list[ChartSpec] = Field(default_factory=list)


class ProviderCall(BaseModel):
    provider: str
    model: str
    cached: bool = False
    latency_ms: int = 0


class AgentAnswer(BaseModel):
    """The full, cited result the API returns for a query."""

    query: str
    route: str = "hybrid"
    verdict: str = "ok"  # "ok" | "insufficient_evidence"
    answer: str = ""
    citations: list[Citation] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    flags: list[ComplianceFlag] = Field(default_factory=list)
    charts: list[ChartSpec] = Field(default_factory=list)
    provider_trace: list[ProviderCall] = Field(default_factory=list)
    reranker: str = ""
    embed_backend: str = ""
    evidence_count: int = 0
    disclaimer: str = "Informational research only. Not investment advice."
