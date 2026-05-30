"""Tests for DreamingReportPhase — T044."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import (
    CycleReport,
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.phases.dreaming_report import DreamingReportPhase


class FakeRenderer:
    async def render(self, report_data: dict[str, Any]) -> str:
        return f"Report: {len(report_data.get('phase_results', []))} phases"


class FakeDelivery:
    def __init__(self) -> None:
        self.delivered: list[tuple[str, str]] = []

    async def deliver(self, content: str, channel: str) -> None:
        self.delivered.append((content, channel))


class FakeApprovalsStore:
    def __init__(self, pending: list[dict[str, Any]] | None = None) -> None:
        self._pending = pending or []

    async def get_pending(self) -> list[dict[str, Any]]:
        return self._pending


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_generates_report_with_metrics() -> None:
    delivery = FakeDelivery()
    phase = DreamingReportPhase(FakeRenderer(), delivery, FakeApprovalsStore(), "email")
    cycle_report = CycleReport(
        cycle_id="c1",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        results=[PhaseResult(phase_name="p1", status=PhaseStatus.SUCCESS, duration_ms=10.0)],
    )
    phase.set_cycle_report(cycle_report)
    result = await phase.execute(_ctx())
    assert result.status == PhaseStatus.SUCCESS


@pytest.mark.asyncio
async def test_delivers_to_configured_channel() -> None:
    delivery = FakeDelivery()
    phase = DreamingReportPhase(FakeRenderer(), delivery, FakeApprovalsStore(), "slack")
    phase.set_cycle_report(CycleReport("c1", datetime.now(timezone.utc), datetime.now(timezone.utc)))
    await phase.execute(_ctx())
    assert delivery.delivered[0][1] == "slack"


@pytest.mark.asyncio
async def test_includes_pending_approvals() -> None:
    pending = [{"id": "a1", "type": "config_change"}]
    delivery = FakeDelivery()
    phase = DreamingReportPhase(FakeRenderer(), delivery, FakeApprovalsStore(pending), "log")
    phase.set_cycle_report(CycleReport("c1", datetime.now(timezone.utc), datetime.now(timezone.utc)))
    result = await phase.execute(_ctx())
    assert result.metrics_dict["pending_approvals"] == 1
