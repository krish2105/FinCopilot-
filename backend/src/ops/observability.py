"""Guarded observability hooks (Phase 12): Sentry + Langfuse.

Both are no-ops unless configured, so the app stays dependency-light offline.
"""

from __future__ import annotations

import logging

from src.config.settings import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


def langfuse_enabled(settings: Settings) -> bool:
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


def trace_llm(settings: Settings, name: str, metadata: dict) -> None:
    """Record an LLM call to Langfuse when configured (best-effort, non-blocking)."""
    if not langfuse_enabled(settings):
        return
    try:
        from langfuse import Langfuse

        lf = Langfuse(
            public_key=settings.langfuse_public_key, secret_key=settings.langfuse_secret_key
        )
        lf.trace(name=name, metadata=metadata)
    except Exception as exc:  # never break a request on tracing
        logger.debug("Langfuse trace failed: %s", exc)
