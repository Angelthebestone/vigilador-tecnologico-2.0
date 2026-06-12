"""Tests for DreamingOrchestrator — T005."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.orchestrator import (
    DreamingOrchestrator,
    OrchestratorStatus,
)


class FakePhase:
    def __init__(self, name: str, fail: bool = False) -> None:
        self._name = name
        self._fail = fail
        self.executed = False

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context: DreamingContext) -> PhaseResult:
        if self._fail:
            raise RuntimeError(f"{self._name} failed intentionally")
        self.executed = True
        return PhaseResult(phase_name=self._name, status=PhaseStatus.SUCCESS, duration_ms=1.0)


class PausingPhase:
    """Phase that triggers pause on the orchestrator during execution."""

    def __init__(self, name: str, orchestrator: DreamingOrchestrator) -> None:
        self._name = name
        self._orchestrator = orchestrator
        self.executed = False

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context: DreamingContext) -> PhaseResult:
        self.executed = True
        self._orchestrator.pause()
        return PhaseResult(phase_name=self._name, status=PhaseStatus.SUCCESS, duration_ms=1.0)


@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    return tmp_path / "audit" / "dreaming"


@pytest.mark.asyncio
async def test_executes_phases_in_order(audit_dir: Path) -> None:
    orch = DreamingOrchestrator(audit_dir=audit_dir)
    p1 = FakePhase("phase_1")
    p2 = FakePhase("phase_2")
    p3 = FakePhase("phase_3")
    orch.register_phase(p1)
    orch.register_phase(p2)
    orch.register_phase(p3)

    report = await orch.run_cycle()

    assert len(report.results) == 3
    assert [r.phase_name for r in report.results] == ["phase_1", "phase_2", "phase_3"]
    assert all(p.executed for p in [p1, p2, p3])


@pytest.mark.asyncio
async def test_failure_does_not_stop_cycle(audit_dir: Path) -> None:
    orch = DreamingOrchestrator(audit_dir=audit_dir)
    p1 = FakePhase("ok_1")
    p2 = FakePhase("failing", fail=True)
    p3 = FakePhase("ok_2")
    orch.register_phase(p1)
    orch.register_phase(p2)
    orch.register_phase(p3)

    report = await orch.run_cycle()

    assert len(report.results) == 3
    assert report.results[1].status == PhaseStatus.FAILED
    assert "failed intentionally" in (report.results[1].error or "")
    assert report.results[0].status == PhaseStatus.SUCCESS
    assert report.results[2].status == PhaseStatus.SUCCESS


@pytest.mark.asyncio
async def test_pause_stops_at_end_of_current_phase(audit_dir: Path) -> None:
    orch = DreamingOrchestrator(audit_dir=audit_dir)
    p1 = PausingPhase("pauser", orch)
    p2 = FakePhase("after_pause")
    orch.register_phase(p1)
    orch.register_phase(p2)

    report = await orch.run_cycle()

    assert p1.executed
    assert not p2.executed
    assert orch.status == OrchestratorStatus.PAUSED
    assert len(report.results) == 1


@pytest.mark.asyncio
async def test_resume_allows_next_cycle(audit_dir: Path) -> None:
    orch = DreamingOrchestrator(audit_dir=audit_dir)
    p1 = PausingPhase("pauser", orch)
    p2 = FakePhase("second")
    orch.register_phase(p1)
    orch.register_phase(p2)

    # First cycle: p1 triggers pause, p2 not executed
    await orch.run_cycle()
    assert orch.status == OrchestratorStatus.PAUSED
    assert not p2.executed

    # Resume and run again: both phases execute
    orch.resume()
    p1_new = FakePhase("pauser")
    p2_new = FakePhase("second")
    orch._phases = [p1_new, p2_new]
    report2 = await orch.run_cycle()
    assert orch.status == OrchestratorStatus.IDLE
    assert len(report2.results) == 2


@pytest.mark.asyncio
async def test_jsonl_audit_written(audit_dir: Path) -> None:
    orch = DreamingOrchestrator(audit_dir=audit_dir)
    orch.register_phase(FakePhase("test_phase"))

    await orch.run_cycle()

    files = list(audit_dir.glob("*.jsonl"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8").strip()
    entry = json.loads(content)
    assert entry["results"][0]["phase"] == "test_phase"
    assert entry["results"][0]["status"] == "success"
