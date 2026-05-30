"""PlaybookRegistry: loads PlaybookDefinitions from YAML (read-only, CQS).

Validates ONLY the YAML schema (fields, types). Does NOT validate existence
of executor implementations or referenced skills at load time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from vigilancia_multiagente.domain.playbook import AgentDeclaration, PlaybookDefinition
from vigilancia_multiagente.enterprise.config_loader import ConfigLoadError, load_yaml_config


class _AgentYaml(BaseModel):
    """Pydantic schema for an agent declaration inside a playbook YAML."""

    id: str
    role: str
    skills_allowed: list[str]


class _PlaybookYaml(BaseModel):
    """Pydantic schema for a playbook YAML file."""

    id: str
    name: str
    executor_type: Literal["branch_coordinator", "crewai", "single_agent"]
    agents: list[_AgentYaml]
    parallel: bool


class PlaybookNotFoundError(Exception):
    """Raised when a requested playbook id is not registered."""

    def __init__(self, playbook_id: str, available: list[str]) -> None:
        self.playbook_id = playbook_id
        self.available = available
        super().__init__(
            f"Playbook '{playbook_id}' not found. Available: {available}"
        )


class PlaybookRegistry:
    """Read-only registry of PlaybookDefinitions loaded from YAML files."""

    def __init__(self) -> None:
        self._playbooks: dict[str, PlaybookDefinition] = {}

    def load_all(self, config_dir: Path) -> None:
        """Load all .yaml files from config_dir into the registry."""
        if not config_dir.is_dir():
            raise ConfigLoadError(config_dir, "playbooks config directory not found")

        for yaml_path in sorted(config_dir.glob("*.yaml")):
            parsed = load_yaml_config(yaml_path, _PlaybookYaml)
            agents = tuple(
                AgentDeclaration(
                    id=a.id,
                    role=a.role,
                    skills_allowed=frozenset(a.skills_allowed),
                )
                for a in parsed.agents
            )
            playbook = PlaybookDefinition(
                id=parsed.id,
                name=parsed.name,
                executor_type=parsed.executor_type,
                agents=agents,
                parallel=parsed.parallel,
            )
            self._playbooks[playbook.id] = playbook

    def get(self, playbook_id: str) -> PlaybookDefinition:
        """Return a PlaybookDefinition by id or raise PlaybookNotFoundError."""
        if playbook_id not in self._playbooks:
            raise PlaybookNotFoundError(playbook_id, list(self._playbooks.keys()))
        return self._playbooks[playbook_id]

    def list_available(self) -> list[PlaybookDefinition]:
        """Return all loaded playbooks."""
        return list(self._playbooks.values())
