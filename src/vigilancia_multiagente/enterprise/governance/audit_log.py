"""AuditLog — runtime JSONL audit trail (Spec 021 F5a.D / T135, FR-045).

Writes one JSON line per relevant runtime event to the daily file
``~/.vigilador/audit/events_<YYYY-MM-DD>.jsonl``. Four event types are
supported in the MVP:

* ``tool_invocation``  — every ``ToolRegistry.execute()`` call.
* ``llm_call``        — every adapter call (prompt + model + tokens + latency).
* ``complexity``      — output of :class:`ComplexityClassifier.classify`.
* ``subagent_spawn``  — every :class:`SubagentRegistry.spawn`.

The richer ``agent_modifications`` SQL table (which the older
``audit_persistence.py`` writes to) is kept on the F5b roadmap and is
unrelated to this module.

Constitución:
* SRP: append-only JSONL writer + 4 thin event constructors. No DB,
  no network, no event filtering — callers decide what to log.
* DIP: callers depend on the :class:`AuditLogPort` Protocol; tests inject
  fakes; the production wire-up uses :class:`AuditLog` directly.
* CQS: every ``log_*`` method returns ``None`` (command); ``read_today``
  is the only query helper.
* #4 explicit: IO failures raise :class:`AuditLogError` with the
  offending path; the caller logs + degrades instead of swallowing.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


_DEFAULT_AUDIT_DIR = Path.home() / ".vigilador" / "audit"
_FILE_PREFIX = "events_"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AuditLogError(RuntimeError):
    """Raised when the JSONL audit line cannot be persisted."""


# ---------------------------------------------------------------------------
# Port (DIP — Tool/LLM/Complexity/Subagent depend on this surface only)
# ---------------------------------------------------------------------------


class AuditLogPort(Protocol):
    """Surface every audit producer depends on."""

    def log_tool_invocation(
        self,
        tool_id: str,
        operation: str,
        outcome: str,
        duration_ms: float,
        agent_id: str | None = None,
        session_id: str | None = None,
        error: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None: ...

    def log_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        agent_id: str | None = None,
        session_id: str | None = None,
        prompt_excerpt: str | None = None,
        error: str | None = None,
    ) -> None: ...

    def log_complexity_decision(
        self,
        query_excerpt: str,
        level: str,
        reason: str,
        latency_ms: float,
        session_id: str | None = None,
    ) -> None: ...

    def log_subagent_spawn(
        self,
        subagent_id: str,
        parent_session_id: str,
        parent_agent_id: str | None,
        depth: int,
        role: str,
        tenant_id: str | None = None,
    ) -> None: ...


# ---------------------------------------------------------------------------
# AuditLog implementation
# ---------------------------------------------------------------------------


@dataclass
class AuditLog:
    """Daily-rotated JSONL writer for runtime audit events."""

    audit_dir: Path = _DEFAULT_AUDIT_DIR
    excerpt_max_chars: int = 500

    def log_tool_invocation(
        self,
        tool_id: str,
        operation: str,
        outcome: str,
        duration_ms: float,
        agent_id: str | None = None,
        session_id: str | None = None,
        error: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._write(
            {
                "event": "tool_invocation",
                "tool_id": tool_id,
                "operation": operation,
                "outcome": outcome,
                "duration_ms": round(duration_ms, 2),
                "agent_id": agent_id,
                "session_id": session_id,
                "error": error,
                "metadata": dict(metadata) if metadata else None,
            }
        )

    def log_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        agent_id: str | None = None,
        session_id: str | None = None,
        prompt_excerpt: str | None = None,
        error: str | None = None,
    ) -> None:
        self._write(
            {
                "event": "llm_call",
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "latency_ms": round(latency_ms, 2),
                "agent_id": agent_id,
                "session_id": session_id,
                "prompt_excerpt": (
                    prompt_excerpt[: self.excerpt_max_chars]
                    if prompt_excerpt is not None
                    else None
                ),
                "error": error,
            }
        )

    def log_complexity_decision(
        self,
        query_excerpt: str,
        level: str,
        reason: str,
        latency_ms: float,
        session_id: str | None = None,
    ) -> None:
        self._write(
            {
                "event": "complexity",
                "query_excerpt": query_excerpt[: self.excerpt_max_chars],
                "level": level,
                "reason": reason,
                "latency_ms": round(latency_ms, 2),
                "session_id": session_id,
            }
        )

    def log_subagent_spawn(
        self,
        subagent_id: str,
        parent_session_id: str,
        parent_agent_id: str | None,
        depth: int,
        role: str,
        tenant_id: str | None = None,
    ) -> None:
        self._write(
            {
                "event": "subagent_spawn",
                "subagent_id": subagent_id,
                "parent_session_id": parent_session_id,
                "parent_agent_id": parent_agent_id,
                "depth": depth,
                "role": role,
                "tenant_id": tenant_id,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def read_today(self) -> list[dict[str, Any]]:
        """Read today's events as a list of dicts (testing aid)."""
        path = self._path_for(datetime.now(UTC))
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _write(self, payload: dict[str, Any]) -> None:
        try:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AuditLogError(
                f"Cannot create audit directory {self.audit_dir}: {exc}"
            ) from exc

        now = datetime.now(UTC)
        payload = {"timestamp": now.isoformat(), **payload}
        path = self._path_for(now)
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            raise AuditLogError(f"Cannot write audit line to {path}: {exc}") from exc

    def _path_for(self, when: datetime) -> Path:
        return self.audit_dir / f"{_FILE_PREFIX}{when.strftime('%Y-%m-%d')}.jsonl"
