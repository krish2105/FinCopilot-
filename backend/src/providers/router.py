"""LLM provider router with automatic fallback, backoff, caching, and tracing.

Fallback chain (per the plan):
  1. Gemini 2.5 Flash-Lite   (default: routing, simple retrieval, summarization)
  2. Gemini 2.5 Flash        (higher-quality synthesis)
  3. Groq llama-3.3-70b      (fast fallback)
  4. Groq openai/gpt-oss-120b (secondary fallback)

On a rate limit we back off and retry the same provider briefly, then fall
through to the next. Every answered call is recorded in an optional trace list
(the agent graph collects these for the audit log). Identical prompts are cached
(cost governance) so repeated demo hits don't burn free-tier quota.

Offline (no keys / FINCOPILOT_OFFLINE_MODE): a single deterministic StubProvider,
and structured calls use each agent's deterministic builder instead of an LLM.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time

from pydantic import BaseModel, ValidationError

from src.config.settings import Settings, get_settings
from src.providers.base import (
    ChatMessage,
    LLMResponse,
    Provider,
    ProviderError,
    RateLimitError,
)
from src.providers.stub import StubProvider

logger = logging.getLogger(__name__)

GEMINI_FLASH_LITE = "gemini-2.5-flash-lite"
GEMINI_FLASH = "gemini-2.5-flash"
GROQ_LLAMA = "llama-3.3-70b-versatile"
GROQ_GPT_OSS = "openai/gpt-oss-120b"

_MAX_RATE_LIMIT_RETRIES = 3
_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _build_providers(settings: Settings) -> tuple[list[Provider], str]:
    if settings.fincopilot_offline_mode or (
        not settings.gemini_api_key and not settings.groq_api_key
    ):
        return [StubProvider()], "stub"

    providers: list[Provider] = []
    if settings.gemini_api_key:
        from src.providers.gemini import GeminiProvider

        providers.append(GeminiProvider(settings.gemini_api_key, GEMINI_FLASH_LITE))
        providers.append(GeminiProvider(settings.gemini_api_key, GEMINI_FLASH))
    if settings.groq_api_key:
        from src.providers.groq import GroqProvider

        providers.append(GroqProvider(settings.groq_api_key, GROQ_LLAMA))
        providers.append(GroqProvider(settings.groq_api_key, GROQ_GPT_OSS))
    return providers, "live"


def _extract_json(text: str) -> str:
    m = _JSON_FENCE.search(text)
    if m:
        return m.group(1).strip()
    # Fall back to the first {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


class ProviderRouter:
    def __init__(self, settings: Settings | None = None, use_cache: bool = True):
        self.settings = settings or get_settings()
        self.providers, self.mode = _build_providers(self.settings)
        self.use_cache = use_cache
        self._cache: dict[str, str] = {}

    # --- public API ---
    def text(
        self,
        prompt: str,
        system: str | None = None,
        stub_text: str | None = None,
        trace: list | None = None,
    ) -> str:
        if self.mode == "stub" and stub_text is not None:
            self._record(trace, "stub", "stub-llm-v1", cached=False, latency_ms=0)
            return stub_text
        resp = self._complete(prompt, system, json_mode=False, trace=trace)
        return resp.text

    def structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        stub=None,
        trace: list | None = None,
    ):
        """Return a validated `schema` instance.

        Offline: use the agent's deterministic `stub` builder. Live: ask the LLM
        for JSON, parse+validate, falling through providers on error; if the whole
        chain fails and a stub is provided, degrade gracefully to it.
        """
        if self.mode == "stub":
            self._record(trace, "stub", "stub-llm-v1", cached=False, latency_ms=0)
            return stub() if stub else schema()

        schema_json = json.dumps(schema.model_json_schema())
        full_prompt = (
            f"{prompt}\n\nReturn ONLY a JSON object matching this JSON schema "
            f"(no prose, no markdown):\n{schema_json}"
        )
        last_err: Exception | None = None
        for provider in self.providers:
            try:
                resp = self._call_provider(provider, full_prompt, system, json_mode=True)
                obj = schema.model_validate_json(_extract_json(resp.text))
                self._record(trace, resp.provider, resp.model, resp.cached, resp.latency_ms)
                return obj
            except RateLimitError as exc:
                last_err = exc
                continue
            except (ProviderError, ValidationError, json.JSONDecodeError) as exc:
                last_err = exc
                logger.warning("structured parse/provider failed (%s): %s", provider.model, exc)
                continue
        if stub is not None:
            logger.warning("All providers failed for structured call; using stub. %s", last_err)
            self._record(trace, "stub", "stub-llm-v1", cached=False, latency_ms=0)
            return stub()
        raise ProviderError(f"All providers failed: {last_err}")

    # --- internals ---
    def _complete(
        self, prompt: str, system: str | None, json_mode: bool, trace: list | None
    ) -> LLMResponse:
        last_err: Exception | None = None
        for provider in self.providers:
            try:
                resp = self._call_provider(provider, prompt, system, json_mode)
                self._record(trace, resp.provider, resp.model, resp.cached, resp.latency_ms)
                return resp
            except RateLimitError as exc:
                last_err = exc
                continue
            except ProviderError as exc:
                last_err = exc
                logger.warning("provider %s failed: %s", provider.model, exc)
                continue
        raise ProviderError(f"All providers failed: {last_err}")

    def _call_provider(
        self, provider: Provider, prompt: str, system: str | None, json_mode: bool
    ) -> LLMResponse:
        key = self._cache_key(provider.model, system, prompt, json_mode)
        if self.use_cache and key in self._cache:
            return LLMResponse(
                text=self._cache[key], provider=provider.name, model=provider.model, cached=True
            )

        messages: list[ChatMessage] = []
        if system:
            messages.append(ChatMessage("system", system))
        messages.append(ChatMessage("user", prompt))

        delay = 1.0
        for attempt in range(_MAX_RATE_LIMIT_RETRIES):
            try:
                resp = provider.complete(messages, json_mode=json_mode)
                if self.use_cache:
                    self._cache[key] = resp.text
                return resp
            except RateLimitError:
                if attempt == _MAX_RATE_LIMIT_RETRIES - 1:
                    raise
                logger.info("rate limited on %s; backoff %.1fs", provider.model, delay)
                time.sleep(delay)
                delay *= 2
        raise RateLimitError(provider.model)  # unreachable

    @staticmethod
    def _cache_key(model: str, system: str | None, prompt: str, json_mode: bool) -> str:
        raw = f"{model}|{json_mode}|{system or ''}|{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _record(trace, provider, model, cached, latency_ms) -> None:
        if trace is not None:
            trace.append(
                {"provider": provider, "model": model, "cached": cached, "latency_ms": latency_ms}
            )


_router: ProviderRouter | None = None


def get_router() -> ProviderRouter:
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router


def reset_router() -> None:
    global _router
    _router = None
