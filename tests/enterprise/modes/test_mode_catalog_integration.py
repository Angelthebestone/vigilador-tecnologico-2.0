"""Integration test: ModeLoader against real config/modes/ (spec 011 Phase 6 T029)."""

from __future__ import annotations

import time
from pathlib import Path

from vigilancia_multiagente.enterprise.modes.mode_loader import ModeLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
MODES_DIR = REPO_ROOT / "config" / "modes"
PLAYBOOKS_DIR = REPO_ROOT / "config" / "playbooks"


class TestModeCatalogIntegration:
    def test_loads_3_mvp_modes(self) -> None:
        loader = ModeLoader(MODES_DIR, PLAYBOOKS_DIR)
        registry = loader.load_all()
        available = registry.list_available()
        ids = {m.id for m in available}
        assert "default" in ids
        assert "vigilancia-tech" in ids
        assert "ceo" in ids
        assert len(available) == 3

    def test_roadmap_modes_not_in_available(self) -> None:
        loader = ModeLoader(MODES_DIR, PLAYBOOKS_DIR)
        registry = loader.load_all()
        ids = {m.id for m in registry.list_available()}
        assert "cfo" not in ids
        assert "consultor-legal" not in ids
        assert "marketing" not in ids
        assert "vendedor-b2b" not in ids
        assert "operaciones-pyme" not in ids

    def test_load_under_2_seconds(self) -> None:
        start = time.perf_counter()
        loader = ModeLoader(MODES_DIR, PLAYBOOKS_DIR)
        loader.load_all()
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0
