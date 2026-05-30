"""Tests for ModeContextFactory: frozen snapshot, allowlist intersection."""

from __future__ import annotations

import dataclasses

import pytest

from vigilancia_multiagente.domain.mode import Mode
from vigilancia_multiagente.domain.mode_context import ModeContext
from vigilancia_multiagente.enterprise.orchestration.mode_context_factory import ModeContextFactory


def _make_mode() -> Mode:
    return Mode(
        id="test",
        name="Test Mode",
        soul_overlay_path="overlay.md",
        company_subset_paths=("a.yaml",),
        skills_allowlist=frozenset(["s1", "s2", "s3"]),
        playbooks_allowed=frozenset(["pb1"]),
        tools_allowlist=frozenset(["t1", "t2", "t3"]),
    )


class TestModeContextFactory:
    def test_build_returns_mode_context(self) -> None:
        mode = _make_mode()
        ctx = ModeContextFactory.build(
            mode=mode,
            company_data={"industry": "tech"},
            skill_ids=frozenset(["s1", "s4"]),
            tool_ids=frozenset(["t1", "t5"]),
        )
        assert isinstance(ctx, ModeContext)

    def test_skills_intersected(self) -> None:
        mode = _make_mode()
        ctx = ModeContextFactory.build(
            mode=mode,
            company_data={},
            skill_ids=frozenset(["s1", "s4"]),
            tool_ids=frozenset(["t1"]),
        )
        # Only s1 is in both mode allowlist and available skill_ids
        assert ctx.skills_allowed == frozenset(["s1"])

    def test_tools_intersected(self) -> None:
        mode = _make_mode()
        ctx = ModeContextFactory.build(
            mode=mode,
            company_data={},
            skill_ids=frozenset(["s1"]),
            tool_ids=frozenset(["t2", "t5"]),
        )
        assert ctx.tools_allowed == frozenset(["t2"])

    def test_frozen_snapshot(self) -> None:
        mode = _make_mode()
        ctx = ModeContextFactory.build(
            mode=mode,
            company_data={"k": "v"},
            skill_ids=frozenset(["s1"]),
            tool_ids=frozenset(["t1"]),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.soul_overlay = "X"  # type: ignore[misc]

    def test_playbooks_passed_through(self) -> None:
        mode = _make_mode()
        ctx = ModeContextFactory.build(
            mode=mode,
            company_data={},
            skill_ids=frozenset(),
            tool_ids=frozenset(),
        )
        assert ctx.playbooks_allowed == frozenset(["pb1"])
