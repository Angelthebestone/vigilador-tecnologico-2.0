"""Loop 1 — Skill learning: detect successful demonstrations and generate skills."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class DemonstrationDetector(Protocol):
    """Port for detecting successful tool demonstrations."""

    async def find_demonstrations(self, tenant_id: str) -> list[dict[str, Any]]: ...


class SkillGenerator(Protocol):
    """Port for generating a skill from a demonstration."""

    async def generate_skill(self, demonstration: dict[str, Any]) -> dict[str, Any]: ...


class SkillRegistrar(Protocol):
    """Port for registering generated skills via AgentModifier."""

    async def register(self, skill: dict[str, Any]) -> None: ...


class SkillLearningLoop:
    """Detects demonstrations and generates new skills."""

    def __init__(
        self,
        detector: DemonstrationDetector,
        generator: SkillGenerator,
        registrar: SkillRegistrar,
    ) -> None:
        self._detector = detector
        self._generator = generator
        self._registrar = registrar

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        demonstrations = await self._detector.find_demonstrations(context.tenant_id)
        skills_created = 0
        for demo in demonstrations:
            skill = await self._generator.generate_skill(demo)
            await self._registrar.register(skill)
            skills_created += 1
        return {"demonstrations_found": len(demonstrations), "skills_created": skills_created}
