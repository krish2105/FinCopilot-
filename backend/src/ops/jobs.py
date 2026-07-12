"""Background job queue (Phase 17).

When REDIS_URL is set and RQ is installed, jobs are enqueued to Redis and run by a
separate worker (`python -m src.ops.worker`) — so a large upload never blocks the
request. Otherwise jobs run inline (sync fallback), keeping local/CI behavior
identical and deterministic.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def _queue(settings: Settings):
    if not settings.redis_url:
        return None
    try:
        import redis
        from rq import Queue

        return Queue("fincopilot", connection=redis.from_url(settings.redis_url))
    except Exception as exc:  # rq/redis missing or unreachable -> inline
        logger.warning("Job queue unavailable (%s); running inline", exc)
        return None


def submit(func: Callable, *args, settings: Settings | None = None) -> bool:
    """Enqueue `func(*args)` for async execution. Returns True if enqueued (async),
    False if it ran inline (sync fallback)."""
    settings = settings or get_settings()
    q = _queue(settings)
    if q is not None:
        q.enqueue(func, *args, job_timeout=600)
        return True
    func(*args)
    return False


def is_async(settings: Settings | None = None) -> bool:
    return _queue(settings or get_settings()) is not None
