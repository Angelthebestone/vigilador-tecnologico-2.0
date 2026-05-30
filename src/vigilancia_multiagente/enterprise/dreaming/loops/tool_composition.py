"""Loop 4 — Tool composition: detect repeated tool sequences and compose skills."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class ToolSequenceDetector(Protocol):
    """Port for detecting repeated tool invocation sequences."""

    async def find_repeated_sequences(
        self, tenant_id: str, min_occurrences: int, days: int
    ) -> list[dict[str, Any]]: ...


class ComposedSkillBuilder(Protocol):
    """Port for building a composed skill from a tool sequence."""

    async def build(self, sequence: dict[str, Any]) -> dict[str, Any]: ...


class SkillStore(Protocol):
    """Port for storing skills (never overwrites existing)."""

    async def exists(self, skill_name: str) -> bool: ...

    async def save(self, skill: dict[str, Any]) -> None: ...

    async def mark_superseded(self, skill_name: str, by: str) -> None: ...


class ToolCompositionLoop:
    """Detects repeated sequences and generates composed skills."""

    MIN_OCCURRENCES = 10
    LOOKBACK_DAYS = 30

    def __init__(
        self,
        detector: ToolSequenceDetector,
        builder: ComposedSkillBuilder,
        store: SkillStore,
    ) -> None:
        self._detector = detector
        self._builder = builder
        self._store = store

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        sequences = await self._detector.find_repeated_sequences(
            context.tenant_id, self.MIN_OCCURRENCES, self.LOOKBACK_DAYS
        )
        skills_created = 0
        skipped_conflicts = 0

        for seq in sequences:
            skill = await self._builder.build(seq)
            skill_name: str = skill.get("name", "")
            if await self._store.exists(skill_name):
                skipped_conflicts += 1
                continue
            await self._store.save(skill)
            skills_created += 1

        return {
            "sequences_detected": len(sequences),
            "skills_created": skills_created,
            "skipped_conflicts": skipped_conflicts,
        }
