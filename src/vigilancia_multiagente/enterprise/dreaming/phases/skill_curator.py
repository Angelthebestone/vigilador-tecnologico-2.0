"""Phase 2 — Skill curator: revalidate learned skills against recent executions."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class SkillExecutionStore(Protocol):
    """Port for querying skill execution history."""

    async def get_recent_executions(self, skill_id: str, limit: int) -> list[dict[str, Any]]: ...

    async def get_all_skill_ids(self) -> list[str]: ...


class SkillStatusUpdater(Protocol):
    """Port for updating skill status (deprecate/promote)."""

    async def deprecate(self, skill_id: str, reason: str) -> None: ...

    async def promote_to_stable(self, skill_id: str) -> None: ...


class SkillCuratorPhase:
    """Revalidates skills: deprecates failing ones, promotes stable ones."""

    def __init__(
        self,
        execution_store: SkillExecutionStore,
        status_updater: SkillStatusUpdater,
    ) -> None:
        self._execution_store = execution_store
        self._status_updater = status_updater

    @property
    def name(self) -> str:
        return "skill_curator"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        skill_ids = await self._execution_store.get_all_skill_ids()
        deprecated_count = 0
        promoted_count = 0

        for skill_id in skill_ids:
            executions = await self._execution_store.get_recent_executions(skill_id, limit=5)
            if not executions:
                continue
            failures = sum(1 for e in executions if e.get("status") == "failed")
            failure_rate = failures / len(executions)

            if failure_rate > 0.5:
                await self._status_updater.deprecate(
                    skill_id, f"Failure rate {failure_rate:.0%} in last {len(executions)} runs"
                )
                deprecated_count += 1
            elif all(e.get("status") == "success" for e in executions) and len(executions) >= 5:
                await self._status_updater.promote_to_stable(skill_id)
                promoted_count += 1

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={
                "skills_evaluated": len(skill_ids),
                "deprecated": deprecated_count,
                "promoted": promoted_count,
            },
        )
