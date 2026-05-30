"""Tests for AdminRepoMaintenancePhase — T042."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext, PhaseStatus
from vigilancia_multiagente.enterprise.dreaming.phases.admin_repo_maintenance import (
    AdminRepoMaintenancePhase,
)


class FakeInspector:
    def __init__(self, repos: list[str], changes: dict[str, dict[str, Any] | None]) -> None:
        self._repos = repos
        self._changes = changes

    async def list_repos(self) -> list[str]:
        return self._repos

    async def check_upstream(self, repo_id: str) -> dict[str, Any] | None:
        return self._changes.get(repo_id)


class FakeClassifier:
    def __init__(self, classifications: dict[str, str] | None = None) -> None:
        self._classifications = classifications or {}

    async def classify(self, change: dict[str, Any]) -> str:
        return self._classifications.get(change.get("repo_id", ""), "patch")


class FakeProposalStore:
    def __init__(self) -> None:
        self.proposals: list[dict[str, Any]] = []

    async def store_proposal(self, proposal: dict[str, Any]) -> None:
        self.proposals.append(proposal)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_detects_new_releases() -> None:
    inspector = FakeInspector(["repo1"], {"repo1": {"version": "2.0", "repo_id": "repo1"}})
    phase = AdminRepoMaintenancePhase(inspector, FakeClassifier(), FakeProposalStore())
    result = await phase.execute(_ctx())
    assert result.metrics_dict["updates_detected"] == 1


@pytest.mark.asyncio
async def test_classifies_impact() -> None:
    inspector = FakeInspector(["r1"], {"r1": {"version": "3.0", "repo_id": "r1"}})
    classifier = FakeClassifier({"r1": "breaking"})
    store = FakeProposalStore()
    phase = AdminRepoMaintenancePhase(inspector, classifier, store)
    await phase.execute(_ctx())
    assert store.proposals[0]["impact"] == "breaking"


@pytest.mark.asyncio
async def test_generates_proposal_with_diff() -> None:
    change = {"version": "2.1", "diff": "+new_feature", "repo_id": "r1"}
    inspector = FakeInspector(["r1"], {"r1": change})
    store = FakeProposalStore()
    phase = AdminRepoMaintenancePhase(inspector, FakeClassifier(), store)
    await phase.execute(_ctx())
    assert store.proposals[0]["change"]["diff"] == "+new_feature"


@pytest.mark.asyncio
async def test_never_auto_promotes() -> None:
    inspector = FakeInspector(["r1"], {"r1": {"version": "2.0", "repo_id": "r1"}})
    store = FakeProposalStore()
    phase = AdminRepoMaintenancePhase(inspector, FakeClassifier(), store)
    await phase.execute(_ctx())
    assert store.proposals[0]["auto_promote"] is False
