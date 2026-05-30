"""Tests for ModeToolFilter (spec 011 Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from vigilancia_multiagente.enterprise.modes.mode_schema import ModeConfig, PlaybooksConfig, ToolsConfig
from vigilancia_multiagente.enterprise.modes.mode_tool_filter import ModeToolFilter, ToolNotAllowedError


@dataclass(frozen=True)
class FakeToolCard:
    """Fake ToolCard for testing without importing tool_registry."""

    id: str
    domains: list[str]


def _make_mode(domains: list[str], excluded: list[str] | None = None) -> ModeConfig:
    return ModeConfig(
        id="test-mode",
        display_name="Test",
        description="test",
        version="1.0.0",
        playbooks=PlaybooksConfig(default="general", allowed=["general"]),
        tools=ToolsConfig(domains=domains, excluded=excluded or []),
    )


def _make_mode_no_tools() -> ModeConfig:
    return ModeConfig(
        id="no-tools",
        display_name="No Tools",
        description="test",
        version="1.0.0",
        playbooks=PlaybooksConfig(default="general", allowed=["general"]),
    )


CARDS = [
    FakeToolCard(id="tavily", domains=["search", "web"]),
    FakeToolCard(id="openalex", domains=["research"]),
    FakeToolCard(id="sandbox", domains=["productivity"]),
    FakeToolCard(id="finance_tool", domains=["finance"]),
    FakeToolCard(id="analytics_tool", domains=["analytics"]),
]


class TestModeToolFilter:
    def test_filter_by_domains(self) -> None:
        mode = _make_mode(["search", "web"])
        f = ModeToolFilter()
        result = f.filter_tools(mode, CARDS)  # type: ignore[arg-type]
        ids = [c.id for c in result]
        assert "tavily" in ids
        assert "openalex" not in ids
        assert "sandbox" not in ids

    def test_excluded_tool_not_returned(self) -> None:
        mode = _make_mode(["search", "web"], excluded=["tavily"])
        f = ModeToolFilter()
        result = f.filter_tools(mode, CARDS)  # type: ignore[arg-type]
        ids = [c.id for c in result]
        assert "tavily" not in ids

    def test_check_excluded_tool_raises(self) -> None:
        mode = _make_mode(["search", "web"], excluded=["tavily"])
        f = ModeToolFilter()
        with pytest.raises(ToolNotAllowedError, match="tavily"):
            f.check_tool_allowed(mode, "tavily", CARDS)  # type: ignore[arg-type]

    def test_no_tools_config_returns_all(self) -> None:
        mode = _make_mode_no_tools()
        f = ModeToolFilter()
        result = f.filter_tools(mode, CARDS)  # type: ignore[arg-type]
        assert len(result) == len(CARDS)

    def test_all_scenarios_filter_correctly(self) -> None:
        """SC-003: 100% filtering scenarios pass."""
        f = ModeToolFilter()

        # search+research mode
        mode = _make_mode(["search", "research"])
        result = f.filter_tools(mode, CARDS)  # type: ignore[arg-type]
        ids = {c.id for c in result}
        assert ids == {"tavily", "openalex"}

        # productivity only
        mode2 = _make_mode(["productivity"])
        result2 = f.filter_tools(mode2, CARDS)  # type: ignore[arg-type]
        assert [c.id for c in result2] == ["sandbox"]

        # check allowed
        assert f.check_tool_allowed(mode, "tavily", CARDS) is True  # type: ignore[arg-type]

        # check not allowed
        with pytest.raises(ToolNotAllowedError):
            f.check_tool_allowed(mode, "sandbox", CARDS)  # type: ignore[arg-type]
