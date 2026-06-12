"""Tests for ModeResolver (spec 011 Phase 4)."""

from __future__ import annotations

import time

import pytest

from vigilancia_multiagente.enterprise.modes.mode_loader import ModeRegistry011
from vigilancia_multiagente.enterprise.modes.mode_resolver import (
    ModeNotAvailableError,
    ModeResolver,
)
from vigilancia_multiagente.enterprise.modes.mode_schema import (
    ModeConfig,
    PlaybooksConfig,
    ToolsConfig,
)


def _make_mode(mode_id: str) -> ModeConfig:
    return ModeConfig(
        id=mode_id,
        display_name=f"Mode {mode_id}",
        description="test",
        version="1.0.0",
        playbooks=PlaybooksConfig(default="general", allowed=["general"]),
        tools=ToolsConfig(domains=["search"], excluded=[]),
    )


def _build_registry() -> ModeRegistry011:
    reg = ModeRegistry011()
    reg.register(_make_mode("default"))
    reg.register(_make_mode("vigilancia-tech"))
    reg.register(_make_mode("ceo"))
    return reg


class TestModeResolver:
    def test_activate_existing_mode(self) -> None:
        resolver = ModeResolver(_build_registry())
        mode = resolver.activate("session-1", "vigilancia-tech")
        assert mode.id == "vigilancia-tech"

    def test_activate_nonexistent_fails_with_available(self) -> None:
        resolver = ModeResolver(_build_registry())
        with pytest.raises(ModeNotAvailableError) as exc_info:
            resolver.activate("session-1", "nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert "default" in exc_info.value.available

    def test_session_without_mode_gets_default(self) -> None:
        resolver = ModeResolver(_build_registry())
        mode = resolver.get_active("new-session")
        assert mode.id == "default"

    def test_change_mode_discards_previous(self) -> None:
        resolver = ModeResolver(_build_registry())
        resolver.activate("session-1", "vigilancia-tech")
        mode = resolver.change_mode("session-1", "ceo")
        assert mode.id == "ceo"
        assert resolver.get_active("session-1").id == "ceo"

    def test_get_active_returns_correct_mode(self) -> None:
        resolver = ModeResolver(_build_registry())
        resolver.activate("session-1", "ceo")
        assert resolver.get_active("session-1").id == "ceo"

    def test_resolution_under_500ms(self) -> None:
        resolver = ModeResolver(_build_registry())
        start = time.perf_counter()
        resolver.activate("session-1", "vigilancia-tech")
        resolver.change_mode("session-1", "ceo")
        resolver.get_active("session-1")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5
