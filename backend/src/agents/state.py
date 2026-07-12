"""LangGraph state for the agent pipeline.

A TypedDict (maximally compatible across LangGraph versions). `provider_trace`
uses an additive reducer so each node can append its LLM calls without clobbering
earlier ones.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from src.agents.schemas import AnalystOutput, ComplianceOutput, VizOutput
from src.retrieval.types import RetrievalResult


class AgentState(TypedDict, total=False):
    # inputs
    query: str
    tickers: list[str] | None
    # routing
    route: str
    # agent outputs
    retrieval: RetrievalResult | None
    analyst: AnalystOutput | None
    compliance: ComplianceOutput | None
    viz: VizOutput | None
    # synthesis
    answer: str
    verdict: str
    # audit
    provider_trace: Annotated[list, operator.add]
