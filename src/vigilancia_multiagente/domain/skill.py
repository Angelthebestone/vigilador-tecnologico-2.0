"""Domain model: SkillDefinition — atomic reusable recipe."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    """Immutable representation of a Skill: a reusable recipe invoking capabilities."""

    id: str
    name: str
    domain: str
    capabilities_required: tuple[str, ...]
    preconditions: tuple[str, ...]
