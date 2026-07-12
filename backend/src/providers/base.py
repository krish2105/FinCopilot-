"""Provider abstraction shared by Gemini, Groq, and the offline stub.

Uniform message interface so the router can treat every backend the same and
fall through the chain on rate limits / errors.
"""

from __future__ import annotations

from dataclasses import dataclass


class ProviderError(Exception):
    """Non-retryable provider failure (or exhausted retries)."""


class RateLimitError(ProviderError):
    """Provider is rate-limited (HTTP 429 / resource exhausted) — fall through."""


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    provider: str  # "gemini" | "groq" | "stub"
    model: str
    latency_ms: int = 0
    cached: bool = False


class Provider:
    """Interface: one text completion call, optionally in JSON mode."""

    name: str = "provider"
    model: str = "unknown"

    def complete(self, messages: list[ChatMessage], json_mode: bool = False) -> LLMResponse:
        raise NotImplementedError
