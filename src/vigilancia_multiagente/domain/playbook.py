"""Domain model: PlaybookDefinition and AgentDeclaration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AgentDeclaration:
    """Declares an agent within a playbook with its allowed skills."""

    id: str
    role: str
    skills_allowed: frozenset[str]


@dataclass(frozen=True)
class PlaybookDefinition:
    """Immutable declarative playbook: which agents, what coordination."""

    id: str
    name: str
    executor_type: Literal["branch_coordinator", "crewai", "single_agent"]
    agents: tuple[AgentDeclaration, ...]
    parallel: bool
