"""Tests for ConfigRefresherPhase — T033."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.config_refresher import (
    ConfigRefresherPhase,
)


class FakeGapDetector:
    def __init__(self, gaps: list[dict[str, Any]]) -> None:
        self._gaps = gaps

    async def detect_gaps(self, tenant_id: str) -> list[dict[str, Any]]:
        return self._gaps


class FakeProposalGenerator:
    async def generate_proposal(self, gap: dict[str, Any]) -> dict[str, Any]:
        return {"target_file": gap.get("target_file", "other.md"), "content": "new paragraph"}


class FakeApplier:
    def __init__(self) -> None:
        self.applied: list[dict[str, Any]] = []
        self.enqueued: list[dict[str, Any]] = []

    async def apply_direct(self, proposal: dict[str, Any]) -> None:
        self.applied.append(proposal)

    async def enqueue_approval(self, proposal: dict[str, Any]) -> None:
        self.enqueued.append(proposal)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_detects_gaps() -> None:
    gaps = [{"target_file": "systems.md", "question": "What CRM?"}]
    phase = ConfigRefresherPhase(FakeGapDetector(gaps), FakeProposalGenerator(), FakeApplier())
    result = await phase.execute(_ctx())
    assert result.metrics_dict["gaps_detected"] == 1


@pytest.mark.asyncio
async def test_generates_proposal() -> None:
    gaps = [{"target_file": "processes.md"}]
    applier = FakeApplier()
    phase = ConfigRefresherPhase(FakeGapDetector(gaps), FakeProposalGenerator(), applier)
    await phase.execute(_ctx())
    assert len(applier.applied) == 1


@pytest.mark.asyncio
async def test_policies_enqueued_for_approval() -> None:
    gaps = [{"target_file": "policies.md"}]
    applier = FakeApplier()
    gen = FakeProposalGenerator()
    phase = ConfigRefresherPhase(FakeGapDetector(gaps), gen, applier)
    await phase.execute(_ctx())
    assert len(applier.enqueued) == 1
    assert len(applier.applied) == 0


@pytest.mark.asyncio
async def test_never_deletes_content() -> None:
    # The phase only appends — verify no "delete" action in proposals
    gaps = [{"target_file": "systems.md"}]
    applier = FakeApplier()
    phase = ConfigRefresherPhase(FakeGapDetector(gaps), FakeProposalGenerator(), applier)
    await phase.execute(_ctx())
    for p in applier.applied:
        assert "delete" not in p.get("action", "")
