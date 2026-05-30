"""Dreaming orchestrator — runs phases sequentially with pause/resume support."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from vigilancia_multiagente.enterprise.dreaming.models import (
    CycleReport,
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.phase_protocol import DreamingPhase


class OrchestratorStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class DreamingOrchestrator:
    """Sequentially executes registered DreamingPhase instances."""

    def __init__(self, audit_dir: Path | None = None) -> None:
        self._phases: list[DreamingPhase] = []
        self._status = OrchestratorStatus.IDLE
        self._pause_requested = False
        self._last_completed_index: int = 0
        self._audit_dir = audit_dir or Path.home() / ".vigilador" / "audit" / "dreaming"

    @property
    def status(self) -> OrchestratorStatus:
        return self._status

    def register_phase(self, phase: DreamingPhase) -> None:
        self._phases.append(phase)

    def pause(self) -> None:
        self._pause_requested = True

    def resume(self) -> None:
        self._pause_requested = False

    async def run_cycle(
        self, tenant_id: str = "default", llm_available: bool = True
    ) -> CycleReport:
        cycle_id = uuid.uuid4().hex[:12]
        started_at = datetime.now(UTC)
        context = DreamingContext(
            cycle_id=cycle_id,
            started_at=started_at,
            tenant_id=tenant_id,
            llm_available=llm_available,
            phases_to_run=[p.name for p in self._phases],
        )
        self._status = OrchestratorStatus.RUNNING
        self._pause_requested = False
        results: list[PhaseResult] = []

        start_index = self._last_completed_index if self._status == OrchestratorStatus.PAUSED else 0
        self._last_completed_index = 0

        for i, phase in enumerate(self._phases[start_index:], start=start_index):
            if self._pause_requested:
                self._status = OrchestratorStatus.PAUSED
                self._last_completed_index = i
                break
            result = await self._execute_phase(phase, context)
            results.append(result)

        finished_at = datetime.now(UTC)
        if not self._pause_requested:
            self._status = OrchestratorStatus.IDLE
            self._last_completed_index = 0

        report = CycleReport(
            cycle_id=cycle_id,
            started_at=started_at,
            finished_at=finished_at,
            results=results,
        )
        self._write_audit(report)
        return report

    async def _execute_phase(self, phase: DreamingPhase, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        try:
            result = await phase.execute(context)
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            result = PhaseResult(
                phase_name=phase.name,
                status=PhaseStatus.FAILED,
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        return result

    def _write_audit(self, report: CycleReport) -> None:
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        date_str = report.started_at.strftime("%Y-%m-%d")
        path = self._audit_dir / f"{date_str}.jsonl"
        entry: dict[str, Any] = {
            "cycle_id": report.cycle_id,
            "started_at": report.started_at.isoformat(),
            "finished_at": report.finished_at.isoformat(),
            "results": [
                {
                    "phase": r.phase_name,
                    "status": r.status.value,
                    "duration_ms": round(r.duration_ms, 2),
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
