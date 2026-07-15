"""Per-principal rate limiting (Phase 12).

Fixed-window counter. In-memory by default; backed by Redis when REDIS_URL is set
so limits hold across multiple backend instances. Fails open on Redis errors
(availability over strictness).
"""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, per_minute: int, redis_url: str | None = None):
        self.per_minute = per_minute
        self._mem: dict[str, tuple[int, int]] = {}  # key -> (window, count)
        self._redis = None
        if redis_url:
            # Upstash gives you both a REST URL (https://) and a redis:// connection
            # string — redis-py needs the latter. Detect the wrong scheme up front and
            # fall back to the in-memory limiter (fine for a single instance) with a
            # clear, one-time message instead of a scary "unavailable" warning.
            scheme = redis_url.split("://", 1)[0].lower() if "://" in redis_url else ""
            if scheme not in ("redis", "rediss", "unix"):
                logger.info(
                    "REDIS_URL scheme %r is not a redis:// connection string; using "
                    "in-memory rate limiting. Set the redis:// (or rediss://) URL to "
                    "share limits across instances.",
                    scheme or "(none)",
                )
            else:
                try:
                    import redis

                    self._redis = redis.from_url(redis_url)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Redis unavailable for rate limiting: %s", exc)

    def _window(self) -> int:
        return int(time.time() // 60)

    def check(self, key: str) -> None:
        if self.per_minute <= 0:
            return
        allowed = self._allow(key)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({self.per_minute}/min). Please slow down.",
            )

    def _allow(self, key: str) -> bool:
        window = self._window()
        if self._redis is not None:
            try:
                rkey = f"rl:{key}:{window}"
                count = self._redis.incr(rkey)
                if count == 1:
                    self._redis.expire(rkey, 65)
                return count <= self.per_minute
            except Exception as exc:  # fail open
                logger.warning("Redis rate-limit error (failing open): %s", exc)
                return True
        prev_window, count = self._mem.get(key, (window, 0))
        if prev_window != window:
            count = 0
        count += 1
        self._mem[key] = (window, count)
        return count <= self.per_minute


_limiter: RateLimiter | None = None


def get_limiter(settings: Settings | None = None) -> RateLimiter:
    global _limiter
    if _limiter is None:
        settings = settings or get_settings()
        _limiter = RateLimiter(settings.rate_limit_per_minute, settings.redis_url)
    return _limiter


def reset_limiter() -> None:
    global _limiter
    _limiter = None
