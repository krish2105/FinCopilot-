"""Structured audit log (Phase 5).

Every answered query appends one AuditRecord — query, routes, sources, providers
used, verdict, faithfulness, latency — to a JSONL file (append-only, greppable).
This is the compliance/audit trail and the FinOps story (providers + latency per
query). The audit-log UI (Phase 6) reads it via GET /audit.

Note: on Render's free tier the disk is ephemeral, so this file resets on
redeploy; a Supabase table is the durable option (Phase 9). The interface is the
same either way.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class AuditRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    query: str
    tickers: list[str] = Field(default_factory=list)
    planned_route: str = "simple"
    route: str = "hybrid"
    verdict: str = "ok"
    evidence_count: int = 0
    sources: list[str] = Field(default_factory=list)  # citation labels
    providers: list[str] = Field(default_factory=list)  # distinct provider:model
    faithfulness_score: float = 1.0
    latency_ms: int = 0


class AuditLog:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def record(self, rec: AuditRecord) -> None:
        try:
            with open(self.path, "a") as f:
                f.write(rec.model_dump_json() + "\n")
        except OSError as exc:  # never let audit logging break a request
            logger.warning("audit write failed: %s", exc)

    def recent(self, limit: int = 100) -> list[AuditRecord]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            lines = f.readlines()
        out: list[AuditRecord] = []
        for line in reversed(lines):  # newest first
            line = line.strip()
            if not line:
                continue
            try:
                out.append(AuditRecord.model_validate_json(line))
            except ValueError:
                continue
            if len(out) >= limit:
                break
        return out

    def count(self) -> int:
        if not os.path.exists(self.path):
            return 0
        with open(self.path) as f:
            return sum(1 for line in f if line.strip())


def audit_path(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return os.path.join(settings.data_dir, "audit_log.jsonl")


_audit_log: AuditLog | None = None


def get_audit_log(settings: Settings | None = None) -> AuditLog:
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog(audit_path(settings))
    return _audit_log


def reset_audit_log() -> None:
    global _audit_log
    _audit_log = None
