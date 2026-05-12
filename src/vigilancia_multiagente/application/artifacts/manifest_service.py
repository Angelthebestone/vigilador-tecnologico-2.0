import json
from pathlib import Path
from typing import Any

from vigilancia_multiagente.domain.models import BranchType


class SessionArtifactService:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path("sessions")

    def ensure_session_tree(self, session_id: str) -> Path:
        base = self._root / session_id
        paths = (
            base / "prompts",
            base / "iterations",
            base / "raw",
            base / "findings",
            base / "semantic",
            base / "report",
            base / "graph",
            base / "metrics",
            base / "traces",
        )
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        return base

    def branch_path(self, session_id: str, branch_type: BranchType, section: str) -> Path:
        base = self.ensure_session_tree(session_id)
        branch_dir = base / section / branch_type.value.lower()
        branch_dir.mkdir(parents=True, exist_ok=True)
        return branch_dir

    def write_json(self, path: Path, payload: dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

