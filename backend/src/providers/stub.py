"""Deterministic offline provider.

Used when no API keys are configured or FINCOPILOT_OFFLINE_MODE is set, so the
whole agent graph runs in CI/tests without network. For structured calls the
router prefers each agent's deterministic `stub` builder; this provider only
backs plain-text calls, returning a stable, grounded-looking response.
"""

from __future__ import annotations

from src.providers.base import ChatMessage, LLMResponse, Provider


class StubProvider(Provider):
    name = "stub"
    model = "stub-llm-v1"

    def complete(self, messages: list[ChatMessage], json_mode: bool = False) -> LLMResponse:
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        if json_mode:
            text = "{}"
        else:
            # Deterministic, non-fabricating: echo intent without inventing facts.
            first_line = user.strip().splitlines()[0] if user.strip() else ""
            text = f"[offline stub] {first_line[:200]}"
        est_tokens = (sum(len(m.content) for m in messages) + len(text)) // 4
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=est_tokens)
