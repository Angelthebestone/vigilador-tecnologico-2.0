"""Tests for ScheduledArtifactsPhase — T040."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext
from vigilancia_multiagente.enterprise.dreaming.phases.scheduled_artifacts import (
    ScheduledArtifactsPhase,
)


class FakeSchedule:
    def __init__(self, due: list[dict[str, Any]]) -> None:
        self._due = due

    async def get_due_artifacts(self) -> list[dict[str, Any]]:
        return self._due


class FakeGenerator:
    def __init__(self) -> None:
        self.generated: list[dict[str, Any]] = []

    async def generate(self, artifact_spec: dict[str, Any]) -> dict[str, Any]:
        self.generated.append(artifact_spec)
        return {"status": "done"}


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_generates_due_reports() -> None:
    schedule = FakeSchedule([{"type": "weekly_report"}, {"type": "dashboard"}])
    gen = FakeGenerator()
    phase = ScheduledArtifactsPhase(schedule, gen)
    result = await phase.execute(_ctx())
    assert result.metrics_dict["generated"] == 2
    assert len(gen.generated) == 2


@pytest.mark.asyncio
async def test_respects_frequency_config() -> None:
    schedule = FakeSchedule([])  # nothing due
    gen = FakeGenerator()
    phase = ScheduledArtifactsPhase(schedule, gen)
    result = await phase.execute(_ctx())
    assert result.metrics_dict["generated"] == 0
