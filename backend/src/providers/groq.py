"""Groq provider (groq SDK, OpenAI-style chat). Imported lazily by the router."""

from __future__ import annotations

import logging
import time

from src.providers.base import (
    ChatMessage,
    LLMResponse,
    Provider,
    ProviderError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

_RATE_LIMIT_MARKERS = ("429", "rate limit", "rate_limit", "too many requests", "quota")


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    if any(m in msg for m in _RATE_LIMIT_MARKERS):
        return True
    return getattr(exc, "status_code", None) == 429


class GroqProvider(Provider):
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=self.api_key)
        return self._client

    def complete(self, messages: list[ChatMessage], json_mode: bool = False) -> LLMResponse:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = {"model": self.model, "messages": payload, "temperature": 0.0}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        try:
            resp = self._client_lazy().chat.completions.create(**kwargs)
        except Exception as exc:
            if _is_rate_limit(exc):
                raise RateLimitError(f"groq/{self.model}: {exc}") from exc
            raise ProviderError(f"groq/{self.model}: {exc}") from exc
        latency = int((time.monotonic() - start) * 1000)
        text = resp.choices[0].message.content or ""
        return LLMResponse(text=text, provider=self.name, model=self.model, latency_ms=latency)
