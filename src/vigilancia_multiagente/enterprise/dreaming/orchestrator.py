"""Dreaming orchestrator — runs phases sequentially with pause/resume support."""

from __future__ import annotations

import contextlib
import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from vigilancia_multiagente.enterprise.dreaming.models import (
    CycleReport,
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.phase_protocol import DreamingPhase
from vigilancia_multiagente.enterprise.dreaming.reporter import (
    DreamingReporter,
    ReporterError,
    ReporterPort,
)


class OrchestratorStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class DreamingOrchestrator:
    """Sequentially executes registered DreamingPhase instances."""

    def __init__(
        self,
        audit_dir: Path | None = None,
        reporter: ReporterPort | None = None,
    ) -> None:
        self._phases: list[DreamingPhase] = []
        self._status = OrchestratorStatus.IDLE
        self._pause_requested = False
        self._last_completed_index: int = 0
        # T126 — delegate JSONL writing to a dedicated reporter.
        if reporter is None:
            default_dir = audit_dir or Path.home() / ".vigilador" / "audit" / "dreaming"
            reporter = DreamingReporter(audit_dir=default_dir)
        self._reporter = reporter

    @property
    def status(self) -> OrchestratorStatus:
        return self._status

    def register_phase(self, phase: DreamingPhase) -> None:
        self._phases.append(phase)

    @property
    def registered_phase_names(self) -> tuple[str, ...]:
        """Tuple of names in registration order — useful for tests/assertions."""
        return tuple(p.name for p in self._phases)

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
        # Report persistence failures are logged inside the reporter; the
        # orchestrator must not let an IO failure bubble up over a
        # successfully completed cycle.
        with contextlib.suppress(ReporterError):
            self._reporter.report(report)
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
