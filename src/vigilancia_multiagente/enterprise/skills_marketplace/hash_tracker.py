"""Hash tracker — persists content hashes for change detection."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".vigilador" / "skills" / "hash_registry.json"


class HashTracker:
    """Tracks SHA-256 hashes of skill files for change detection."""

    def __init__(self, registry_path: Path = _DEFAULT_PATH) -> None:
        self._path = registry_path
        self._hashes: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load hash registry: %s", exc)
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._hashes, indent=2), encoding="utf-8")

    def has_changed(self, skill_id: str, current_hash: str) -> bool:
        """Return True if skill_id was previously tracked with a different hash."""
        previous = self._hashes.get(skill_id)
        if previous is None:
            return False  # New skill, not a change
        return previous != current_hash

    def update(self, skill_id: str, new_hash: str) -> None:
        """Update stored hash for skill_id."""
        self._hashes[skill_id] = new_hash
        self._save()

    def get(self, skill_id: str) -> str | None:
        """Get stored hash for skill_id, or None if not tracked."""
        return self._hashes.get(skill_id)
