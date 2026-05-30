"""Port: SkillExecutor — contract for executing a skill."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from vigilancia_multiagente.domain.skill import SkillDefinition


@dataclass(frozen=True)
class SkillResult:
    """Immutable result of a skill execution."""

    success: bool
    data: dict[str, object]
    error: str | None = None


class SkillExecutor(Protocol):
    """Executes a skill with given inputs."""

    def execute(self, skill: SkillDefinition, inputs: dict[str, object]) -> SkillResult: ...
