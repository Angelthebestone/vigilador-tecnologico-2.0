"""Skill audit — JSONL logging for skill invocations (contract/hook for caller)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_AUDIT_PATH = Path.home() / ".vigilador" / "audit" / "skills.log"


def log_skill_invocation(
    skill_id: str,
    source: str,
    mode: str,
    capabilities_invoked: list[str],
    result_status: str,
) -> None:
    """Append a skill invocation record to the JSONL audit trail."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "skill_id": skill_id,
        "source": source,
        "mode": mode,
        "capabilities_invoked": capabilities_invoked,
        "result_status": result_status,
    }
    _write_record(record)


def log_skill_blocked(skill_id: str, reason: str) -> None:
    """Log a blocked skill invocation attempt."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "skill_id": skill_id,
        "event": "blocked",
        "reason": reason,
    }
    _write_record(record)


def _write_record(record: dict[str, object]) -> None:
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
