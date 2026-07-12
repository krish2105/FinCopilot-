"""Guarded observability (Phase 12/18): Sentry + OpenTelemetry → Langfuse.

All no-ops unless configured, so the app stays dependency-light offline. When
Langfuse keys are present and the OpenTelemetry packages are installed, `span()`
emits a trace span per agent step (retrieve/analyze/generate/judge), exported to
Langfuse over OTLP for trace-level root-cause analysis.
"""

from __future__ import annotations

import base64
import logging
from contextlib import contextmanager

from src.config.settings import Settings

logger = logging.getLogger(__name__)

_tracer = None
_LANGFUSE_OTLP = "https://cloud.langfuse.com/api/public/otel/v1/traces"


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


def init_tracing(settings: Settings) -> None:
    """Wire an OpenTelemetry tracer that exports spans to Langfuse (guarded)."""
    global _tracer
    if not langfuse_enabled(settings):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        auth = base64.b64encode(
            f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
        ).decode()
        exporter = OTLPSpanExporter(
            endpoint=_LANGFUSE_OTLP, headers={"Authorization": f"Basic {auth}"}
        )
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("fincopilot")
        logger.info("OpenTelemetry tracing -> Langfuse initialized")
    except Exception as exc:
        logger.warning("Tracing init failed: %s", exc)


@contextmanager
def span(name: str, **attributes):
    """A trace span; a no-op context manager when tracing isn't configured."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as s:
        for k, v in attributes.items():
            try:
                s.set_attribute(k, v)
            except Exception:
                pass
        yield s
