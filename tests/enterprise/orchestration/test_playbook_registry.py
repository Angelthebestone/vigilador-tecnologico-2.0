"""Tests for PlaybookRegistry: load 4 playbooks, get, error on missing."""

from __future__ import annotations

from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.config_loader import ConfigLoadError
from vigilancia_multiagente.enterprise.orchestration.playbook_registry import (
    PlaybookNotFoundError,
    PlaybookRegistry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PLAYBOOKS_DIR = REPO_ROOT / "config" / "playbooks"


class TestPlaybookRegistry:
    def test_load_all_from_project(self) -> None:
        reg = PlaybookRegistry()
        reg.load_all(PLAYBOOKS_DIR)
        playbooks = reg.list_available()
        assert len(playbooks) == 7

    def test_get_existing_playbook(self) -> None:
        reg = PlaybookRegistry()
        reg.load_all(PLAYBOOKS_DIR)
        pb = reg.get("technology-watch")
        assert pb.id == "technology-watch"
        assert pb.executor_type == "branch_coordinator"
        assert pb.parallel is True
        assert len(pb.agents) == 6

    def test_get_nonexistent_raises(self) -> None:
        reg = PlaybookRegistry()
        reg.load_all(PLAYBOOKS_DIR)
        with pytest.raises(PlaybookNotFoundError, match="nonexistent"):
            reg.get("nonexistent")

    def test_load_invalid_dir_raises(self, tmp_path: Path) -> None:
        reg = PlaybookRegistry()
        with pytest.raises(ConfigLoadError, match="not found"):
            reg.load_all(tmp_path / "nope")

    def test_agents_have_skills_allowed(self) -> None:
        reg = PlaybookRegistry()
        reg.load_all(PLAYBOOKS_DIR)
        pb = reg.get("deep-research")
        researcher = pb.agents[0]
        assert "web_search" in researcher.skills_allowed

    def test_schema_validation_error(self, tmp_path: Path) -> None:
        """A YAML with missing required fields raises ConfigLoadError."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("id: x\nname: Bad\n", encoding="utf-8")
        reg = PlaybookRegistry()
        with pytest.raises(ConfigLoadError, match="schema validation failed"):
            reg.load_all(tmp_path)
