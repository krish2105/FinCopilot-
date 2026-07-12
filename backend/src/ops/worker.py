"""RQ worker entrypoint (Phase 17).

    REDIS_URL=redis://... python -m src.ops.worker

Processes queued document-ingestion jobs. Runs as a separate service (e.g. a
Render background worker) alongside the API. No-op guidance printed if RQ/Redis
aren't configured.
"""

from __future__ import annotations

import logging

from src.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    if not settings.redis_url:
        print("REDIS_URL not set — the API runs ingestion inline; no worker needed.")
        return
    import redis
    from rq import Queue, Worker

    conn = redis.from_url(settings.redis_url)
    worker = Worker([Queue("fincopilot", connection=conn)], connection=conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
