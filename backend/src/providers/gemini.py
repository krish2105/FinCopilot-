"""Google Gemini provider (google-genai SDK). Imported lazily by the router."""

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

_RATE_LIMIT_MARKERS = ("429", "resource_exhausted", "resource exhausted", "quota", "rate limit")


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _RATE_LIMIT_MARKERS)


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def complete(self, messages: list[ChatMessage], json_mode: bool = False) -> LLMResponse:
        from google.genai import types

        system = "\n".join(m.content for m in messages if m.role == "system") or None
        user = "\n\n".join(m.content for m in messages if m.role != "system")

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
            response_mime_type="application/json" if json_mode else None,
        )
        start = time.monotonic()
        try:
            resp = self._client_lazy().models.generate_content(
                model=self.model, contents=user, config=config
            )
        except Exception as exc:
            if _is_rate_limit(exc):
                raise RateLimitError(f"gemini/{self.model}: {exc}") from exc
            raise ProviderError(f"gemini/{self.model}: {exc}") from exc
        latency = int((time.monotonic() - start) * 1000)
        text = resp.text or ""
        tokens = 0
        usage = getattr(resp, "usage_metadata", None)
        if usage is not None:
            tokens = getattr(usage, "total_token_count", 0) or 0
        return LLMResponse(
            text=text, provider=self.name, model=self.model, latency_ms=latency, tokens=tokens
        )
