"""HealthMonitor (F1.3) — monitoreo periódico de tools con circuit breaker.

Responsabilidades:
- Ejecutar healthcheck() en cada tool registrada cada N segundos.
- Persistir estado via ToolHealthRepository.upsert (CQS write).
- Circuit breaker: si fallos >= threshold en window → status DOWN.
- Cooldown: si status DOWN, no re-chequear hasta que pase cooldown_sec.
- Escribir línea JSONL a audit log.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult
from vigilancia_multiagente.infra.persistence.tool_health_repository import (
    ToolHealthRepository,
    ToolHealthRow,
)

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitorea la salud de las tools registradas con circuit breaker."""

    def __init__(
        self,
        tool_registry: object,
        tool_health_repo: ToolHealthRepository,
        settings: object,
        audit_dir: Path | None = None,
    ) -> None:
        self._registry = tool_registry
        self._repo = tool_health_repo
        self._settings = settings

        self._interval_sec: int = settings.health_monitor_interval_sec  # type: ignore[attr-defined]
        self._cb_threshold: int = settings.health_monitor_cb_threshold  # type: ignore[attr-defined]
        self._cb_window_sec: int = settings.health_monitor_cb_window_sec  # type: ignore[attr-defined]
        self._cooldown_sec: int = settings.health_monitor_cooldown_sec  # type: ignore[attr-defined]
        self._tenant_id = UUID(str(settings.default_tenant_id))  # type: ignore[attr-defined]

        # Circuit breaker state: tool_name -> list of failure timestamps
        self._failures: dict[str, list[datetime]] = {}
        # Track when a tool entered DOWN state
        self._down_since: dict[str, datetime] = {}

        # Audit log directory
        if audit_dir is None:
            audit_dir = Path.home() / ".vigilador" / "audit"
        self._audit_dir = audit_dir

        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        """Arranca el scheduler con el intervalo configurado."""
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(self._tick, "interval", seconds=self._interval_sec)
        self._scheduler.start()

    def stop(self) -> None:
        """Para el scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    async def _tick(self) -> None:
        """Ciclo de healthcheck para todas las tools."""
        tools: dict[str, object] = self._registry._tools  # type: ignore[attr-defined]

        for name, tool in tools.items():
            now = datetime.now(UTC)

            # Cooldown check: skip if tool is DOWN and cooldown hasn't elapsed
            if name in self._down_since:
                elapsed = (now - self._down_since[name]).total_seconds()
                if elapsed < self._cooldown_sec:
                    continue

            # Execute healthcheck
            try:
                result: HealthcheckResult = await tool.healthcheck()  # type: ignore[attr-defined]
            except Exception as exc:
                result = HealthcheckResult(status="DOWN", latency_ms=None, error=str(exc))

            # Update circuit breaker state
            if result.status != "UP":
                failures = self._failures.setdefault(name, [])
                failures.append(now)
                # Prune failures outside window
                cutoff = now.timestamp() - self._cb_window_sec
                self._failures[name] = [t for t in failures if t.timestamp() > cutoff]
                fail_count = len(self._failures[name])
            else:
                # Reset on success
                self._failures.pop(name, None)
                self._down_since.pop(name, None)
                fail_count = 0

            # Determine final status
            status = result.status
            if fail_count >= self._cb_threshold:
                status = "DOWN"
                if name not in self._down_since:
                    self._down_since[name] = now

            # Persist
            row = ToolHealthRow(
                name=name,
                tenant_id=self._tenant_id,
                status=status,
                last_check=now,
                fail_count=fail_count,
                last_error=result.error,
                domain=getattr(tool, "domain", None),
                requires_key=getattr(tool, "requires_auth", False),
            )
            await self._repo.upsert(row)

            # Write JSONL audit log
            self._write_audit(now, name, status, result.latency_ms, result.error)

    def _write_audit(
        self,
        ts: datetime,
        tool: str,
        status: str,
        latency_ms: float | None,
        error: str | None,
    ) -> None:
        """Append a JSONL line to the healthcheck audit log."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._audit_dir / "healthcheck.log"
        entry = {
            "ts": ts.isoformat(),
            "tool": tool,
            "status": status,
            "latency_ms": latency_ms,
            "error": error,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
