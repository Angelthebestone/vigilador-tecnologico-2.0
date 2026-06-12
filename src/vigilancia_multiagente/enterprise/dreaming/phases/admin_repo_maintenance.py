# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Phase 9 — Admin repo maintenance: check cloned repos against upstream."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class RepoInspector(Protocol):
    """Port for inspecting cloned tool/MCP repos."""

    async def list_repos(self) -> list[str]: ...

    async def check_upstream(self, repo_id: str) -> dict[str, Any] | None: ...


class ImpactClassifier(Protocol):
    """Port for classifying change impact."""

    async def classify(self, change: dict[str, Any]) -> str: ...


class AdminProposalStore(Protocol):
    """Port for storing admin proposals (never auto-promotes)."""

    async def store_proposal(self, proposal: dict[str, Any]) -> None: ...


class AdminRepoMaintenancePhase:
    """Reviews repos against upstream, classifies impact, generates proposals."""

    def __init__(
        self,
        inspector: RepoInspector,
        classifier: ImpactClassifier,
        proposal_store: AdminProposalStore,
    ) -> None:
        self._inspector = inspector
        self._classifier = classifier
        self._proposal_store = proposal_store

    @property
    def name(self) -> str:
        return "admin_repo_maintenance"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        repos = await self._inspector.list_repos()
        updates_detected = 0
        proposals_created = 0

        for repo_id in repos:
            change = await self._inspector.check_upstream(repo_id)
            if change is None:
                continue
            updates_detected += 1
            impact = await self._classifier.classify(change)
            await self._proposal_store.store_proposal(
                {
                    "repo_id": repo_id,
                    "impact": impact,
                    "change": change,
                    "auto_promote": False,
                }
            )
            proposals_created += 1

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={
                "repos_checked": len(repos),
                "updates_detected": updates_detected,
                "proposals_created": proposals_created,
            },
        )
