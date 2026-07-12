"""Adaptive-routing complexity classifier (Phase 4).

Picks the cheapest pipeline that can answer:
  * simple        -> hybrid search (Phase 2 default)  [~80% of queries]
  * multi_hop     -> agentic iterative retrieval
  * relationship  -> GraphRAG entity-graph traversal

Live: the provider router classifies via structured output. Offline/fallback: a
deterministic keyword heuristic. Route names map 1:1 to the retrieval routes.
"""

from __future__ import annotations

import logging

from src.agents.schemas import RouteDecision
from src.providers.router import ProviderRouter

logger = logging.getLogger(__name__)

# Relationship: how entities relate/share (entity-graph traversal).
_RELATIONSHIP = (
    "share",
    "shared",
    "in common",
    "common",
    "both",
    "subsidiar",
    "related",
    "relationship",
    "same risk",
    "which companies",
    "who else",
    "between",
)
# Multi-hop: comparative/compound questions needing several retrieval steps.
_MULTI_HOP = (
    "compare",
    "versus",
    " vs ",
    "vs.",
    "trend",
    "over time",
    "across",
    "difference",
    " and ",
    "how did",
    "why did",
)

_CLASSIFIER_SYSTEM = (
    "Classify a financial research question into exactly one retrieval route:\n"
    "- 'relationship': asks how entities relate, share, or compare (e.g. which "
    "companies share a risk, what do A and B have in common).\n"
    "- 'multi_hop': compound/comparative questions needing several retrieval "
    "steps or reasoning across sub-parts.\n"
    "- 'simple': a single factual lookup answerable from one search.\n"
    "Prefer the cheapest route that suffices; default to 'simple'."
)


def heuristic_route(query: str) -> RouteDecision:
    q = f" {query.lower()} "
    if any(k in q for k in _RELATIONSHIP):
        return RouteDecision(route="relationship", reason="matched relationship keyword")
    if any(k in q for k in _MULTI_HOP):
        return RouteDecision(route="multi_hop", reason="matched multi-hop keyword")
    return RouteDecision(route="simple", reason="single factual lookup")


def classify(router: ProviderRouter, query: str, trace: list | None = None) -> RouteDecision:
    decision = router.structured(
        f"Question: {query}",
        RouteDecision,
        system=_CLASSIFIER_SYSTEM,
        stub=lambda: heuristic_route(query),
        trace=trace,
    )
    if decision.route not in ("simple", "multi_hop", "relationship"):
        decision = heuristic_route(query)
    logger.info("route=%s (%s) for %r", decision.route, decision.reason, query)
    return decision
