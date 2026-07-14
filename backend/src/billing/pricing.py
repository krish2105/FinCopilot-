"""LLM cost estimation (Phase 18 FinOps).

Blended $/1M-token prices (rough, provider list-price order of magnitude — free
tiers cost $0). Used to surface $/query and per-org monthly spend. Adjust as
provider pricing changes.
"""

from __future__ import annotations

# USD per 1M tokens (blended input+output estimate).
MODEL_PRICE_PER_M: dict[str, float] = {
    "gemini-3.1-flash-lite": 0.15,
    "gemini-3-flash-preview": 0.30,
    "llama-3.3-70b-versatile": 0.59,
    "openai/gpt-oss-120b": 0.30,
    "stub-llm-v1": 0.0,
}
_DEFAULT_PRICE_PER_M = 0.30


def price_per_m(model: str) -> float:
    return MODEL_PRICE_PER_M.get(model, _DEFAULT_PRICE_PER_M)


def estimate_cost(provider_trace) -> float:
    """Sum cost across a provider trace (list of ProviderCall)."""
    total = 0.0
    for c in provider_trace:
        if getattr(c, "cached", False):
            continue
        total += (getattr(c, "tokens", 0) / 1_000_000) * price_per_m(getattr(c, "model", ""))
    return round(total, 6)


def estimate_cost_from_tokens(tokens: int, model: str = "") -> float:
    return round((tokens / 1_000_000) * price_per_m(model), 6)
