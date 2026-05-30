"""ModeLoader: loads, validates, and registers modes from YAML (spec 011)."""

from __future__ import annotations

import logging
from pathlib import Path

from vigilancia_multiagente.enterprise.modes.mode_schema import (
    ModeConfig,
    ModeSchemaError,
    parse_mode_yaml,
)

logger = logging.getLogger(__name__)


class ModeLoadError(Exception):
    """Raised for mode loading failures with context."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"ModeLoadError in '{path}': {detail}")


class ModeRegistry011:
    """Registry of validated ModeConfig instances (spec 011 schema)."""

    def __init__(self) -> None:
        self._modes: dict[str, ModeConfig] = {}

    def register(self, mode: ModeConfig) -> None:
        """Register a mode. Rejects duplicates with explicit error (FR-006)."""
        if mode.id in self._modes:
            raise ModeLoadError(
                Path(f"<registry:{mode.id}>"),
                f"duplicate mode id '{mode.id}' — already registered",
            )
        self._modes[mode.id] = mode

    def get(self, mode_id: str) -> ModeConfig | None:
        """Return a ModeConfig by id, or None if not found."""
        return self._modes.get(mode_id)

    def list_available(self) -> list[ModeConfig]:
        """Return all registered (active) modes."""
        return list(self._modes.values())

    def exists(self, mode_id: str) -> bool:
        """Check if a mode id is registered."""
        return mode_id in self._modes


class ModeLoader:
    """Loads all mode YAML files, validates, and builds a ModeRegistry011."""

    def __init__(self, modes_dir: Path, playbooks_dir: Path) -> None:
        self._modes_dir = modes_dir
        self._playbooks_dir = playbooks_dir

    def load_all(self) -> ModeRegistry011:
        """Load all *.yaml from modes_dir, validate, return registry.

        - Modes with status='roadmap' are skipped (FR-023).
        - Invalid modes are logged and skipped (FR-009).
        - Duplicate ids reject the second (FR-006).
        - Playbook references are validated (FR-007).
        - company_geo without country rejects the mode (FR-008).
        """
        registry = ModeRegistry011()

        if not self._modes_dir.is_dir():
            logger.warning("Modes directory not found: %s", self._modes_dir)
            return registry

        for yaml_path in sorted(self._modes_dir.glob("*.yaml")):
            try:
                mode = parse_mode_yaml(yaml_path)
            except ModeSchemaError as exc:
                logger.error("Skipping invalid mode %s: %s", yaml_path.name, exc.detail)
                continue

            # FR-023: skip roadmap modes
            if mode.status == "roadmap":
                logger.info("Skipping roadmap mode: %s", mode.id)
                continue

            # FR-007: validate playbook references
            if not self._validate_playbook_refs(mode, yaml_path):
                continue

            # FR-006: reject duplicates
            try:
                registry.register(mode)
            except ModeLoadError as exc:
                logger.error("Skipping mode %s: %s", yaml_path.name, exc.detail)
                continue

        return registry

    def _validate_playbook_refs(self, mode: ModeConfig, yaml_path: Path) -> bool:
        """Validate that all referenced playbooks exist as files."""
        all_playbooks = list(mode.playbooks.allowed)
        if mode.playbooks.default and mode.playbooks.default not in all_playbooks:
            all_playbooks.append(mode.playbooks.default)

        for pb_name in all_playbooks:
            pb_path = self._playbooks_dir / f"{pb_name}.yaml"
            if not pb_path.exists():
                logger.error(
                    "Skipping mode '%s' (%s): playbook '%s' not found at %s",
                    mode.id,
                    yaml_path.name,
                    pb_name,
                    pb_path,
                )
                return False
        return True
