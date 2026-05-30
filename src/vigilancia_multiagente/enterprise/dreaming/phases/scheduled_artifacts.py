"""Phase 8 — Scheduled artifacts: generate programmed reports/dashboards."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class ArtifactSchedule(Protocol):
    """Port for reading artifact generation schedules."""

    async def get_due_artifacts(self) -> list[dict[str, Any]]: ...


class ArtifactGenerator(Protocol):
    """Port for generating scheduled artifacts."""

    async def generate(self, artifact_spec: dict[str, Any]) -> dict[str, Any]: ...


class ScheduledArtifactsPhase:
    """Generates reports and dashboards that are due according to schedule."""

    def __init__(
        self,
        schedule: ArtifactSchedule,
        generator: ArtifactGenerator,
    ) -> None:
        self._schedule = schedule
        self._generator = generator

    @property
    def name(self) -> str:
        return "scheduled_artifacts"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        due = await self._schedule.get_due_artifacts()
        generated = 0

        for spec in due:
            await self._generator.generate(spec)
            generated += 1

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={"due": len(due), "generated": generated},
        )
