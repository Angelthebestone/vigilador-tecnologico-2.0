"""Tests for ModeLoader (spec 011 Phase 3)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.modes.mode_loader import ModeLoader


def _create_mode_yaml(modes_dir: Path, filename: str, content: str) -> None:
    (modes_dir / filename).write_text(content, encoding="utf-8")


def _create_playbook(playbooks_dir: Path, name: str) -> None:
    (playbooks_dir / f"{name}.yaml").write_text(f"id: {name}\nname: {name}\n", encoding="utf-8")


VALID_MODE = """\
id: {id}
display_name: "Mode {id}"
description: "desc"
version: "1.0.0"
status: active
playbooks:
  default: general
  allowed: [general]
tools:
  domains: [search]
"""

ROADMAP_MODE = """\
id: future
display_name: "Future"
description: "roadmap"
version: "1.0.0"
status: roadmap
playbooks:
  default: general
  allowed: [general]
"""


class TestModeLoader:
    def test_loads_valid_modes(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        _create_playbook(pb_dir, "general")

        for name in ("alpha", "beta", "gamma"):
            _create_mode_yaml(modes_dir, f"{name}.yaml", VALID_MODE.format(id=name))

        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        assert len(registry.list_available()) == 3

    def test_roadmap_not_in_registry(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        _create_playbook(pb_dir, "general")

        _create_mode_yaml(modes_dir, "active.yaml", VALID_MODE.format(id="active"))
        _create_mode_yaml(modes_dir, "future.yaml", ROADMAP_MODE)

        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        assert len(registry.list_available()) == 1
        assert registry.get("future") is None

    def test_duplicate_id_rejects_second(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        _create_playbook(pb_dir, "general")

        _create_mode_yaml(modes_dir, "a_first.yaml", VALID_MODE.format(id="dup"))
        _create_mode_yaml(modes_dir, "b_second.yaml", VALID_MODE.format(id="dup"))

        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        # First one registered, second skipped
        assert len(registry.list_available()) == 1

    def test_missing_playbook_rejects_mode(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        # No playbook created

        _create_mode_yaml(modes_dir, "bad.yaml", VALID_MODE.format(id="bad"))

        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        assert len(registry.list_available()) == 0

    def test_company_geo_without_country_rejects(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        _create_playbook(pb_dir, "general")

        bad_yaml = """\
id: bad-geo
display_name: "Bad"
description: "bad geo"
version: "1.0.0"
company_geo:
  department: Santander
playbooks:
  default: general
  allowed: [general]
"""
        _create_mode_yaml(modes_dir, "bad.yaml", bad_yaml)
        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        assert len(registry.list_available()) == 0

    def test_isolated_failure_does_not_affect_others(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        _create_playbook(pb_dir, "general")

        _create_mode_yaml(modes_dir, "good.yaml", VALID_MODE.format(id="good"))
        _create_mode_yaml(modes_dir, "invalid.yaml", "not: valid\n")

        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        assert registry.exists("good")

    def test_load_under_2_seconds(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        _create_playbook(pb_dir, "general")

        for i in range(3):
            _create_mode_yaml(modes_dir, f"mode{i}.yaml", VALID_MODE.format(id=f"mode{i}"))

        start = time.perf_counter()
        loader = ModeLoader(modes_dir, pb_dir)
        loader.load_all()
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0

    def test_empty_directory_returns_empty_registry(self, tmp_path: Path) -> None:
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()

        loader = ModeLoader(modes_dir, pb_dir)
        registry = loader.load_all()
        assert len(registry.list_available()) == 0
