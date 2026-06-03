# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Loop 7 — Admin repo: detect releases, classify impact, never auto-promote."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class RepoReleaseChecker(Protocol):
    """Port for checking upstream releases of cloned repos."""

    async def get_repos(self) -> list[str]: ...

    async def check_new_releases(self, repo_id: str) -> list[dict[str, Any]]: ...


class ReleaseImpactClassifier(Protocol):
    """Port for classifying release impact: patch/feature/breaking/security."""

    async def classify(self, release: dict[str, Any]) -> str: ...


class AdminRepoProposalStore(Protocol):
    """Port for storing admin proposals (never auto-promotes)."""

    async def store(self, proposal: dict[str, Any]) -> None: ...


class AdminRepoLoop:
    """Detects new releases, classifies impact, stores proposals without promoting."""

    def __init__(
        self,
        checker: RepoReleaseChecker,
        classifier: ReleaseImpactClassifier,
        proposal_store: AdminRepoProposalStore,
    ) -> None:
        self._checker = checker
        self._classifier = classifier
        self._proposal_store = proposal_store

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        repos = await self._checker.get_repos()
        releases_detected = 0
        proposals_stored = 0

        for repo_id in repos:
            releases = await self._checker.check_new_releases(repo_id)
            for release in releases:
                releases_detected += 1
                impact = await self._classifier.classify(release)
                await self._proposal_store.store({
                    "repo_id": repo_id,
                    "release": release,
                    "impact": impact,
                    "auto_promote": False,
                })
                proposals_stored += 1

        return {
            "repos_checked": len(repos),
            "releases_detected": releases_detected,
            "proposals_stored": proposals_stored,
        }
