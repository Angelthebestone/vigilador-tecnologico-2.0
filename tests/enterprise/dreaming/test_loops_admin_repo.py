"""Tests for AdminRepoLoop — T060."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.admin_repo_loop import AdminRepoLoop
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeChecker:
    def __init__(self, repos: list[str], releases: dict[str, list[dict[str, Any]]]) -> None:
        self._repos = repos
        self._releases = releases

    async def get_repos(self) -> list[str]:
        return self._repos

    async def check_new_releases(self, repo_id: str) -> list[dict[str, Any]]:
        return self._releases.get(repo_id, [])


class FakeClassifier:
    async def classify(self, release: dict[str, Any]) -> str:
        return release.get("impact", "patch")


class FakeProposalStore:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def store(self, proposal: dict[str, Any]) -> None:
        self.stored.append(proposal)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_detects_releases() -> None:
    checker = FakeChecker(["r1"], {"r1": [{"version": "2.0", "impact": "feature"}]})
    loop = AdminRepoLoop(checker, FakeClassifier(), FakeProposalStore())
    result = await loop.run(_ctx())
    assert result["releases_detected"] == 1


@pytest.mark.asyncio
async def test_classifies_impact() -> None:
    checker = FakeChecker(["r1"], {"r1": [{"version": "3.0", "impact": "breaking"}]})
    store = FakeProposalStore()
    loop = AdminRepoLoop(checker, FakeClassifier(), store)
    await loop.run(_ctx())
    assert store.stored[0]["impact"] == "breaking"


@pytest.mark.asyncio
async def test_never_auto_promotes() -> None:
    checker = FakeChecker(["r1"], {"r1": [{"version": "2.0", "impact": "security"}]})
    store = FakeProposalStore()
    loop = AdminRepoLoop(checker, FakeClassifier(), store)
    await loop.run(_ctx())
    assert store.stored[0]["auto_promote"] is False
