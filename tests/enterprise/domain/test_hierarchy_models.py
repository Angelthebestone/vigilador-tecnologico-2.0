"""Tests for hierarchy domain models: frozen, composition, required fields."""

from __future__ import annotations

import dataclasses

import pytest

from vigilancia_multiagente.domain.capability import CapabilitySchema
from vigilancia_multiagente.domain.mode import Mode
from vigilancia_multiagente.domain.mode_context import ModeContext
from vigilancia_multiagente.domain.playbook import AgentDeclaration, PlaybookDefinition
from vigilancia_multiagente.domain.skill import SkillDefinition


class TestCapabilitySchema:
    def test_frozen(self) -> None:
        cap = CapabilitySchema(id="c1", verb="search", input_schema={}, output_schema={}, tool_id="t1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            cap.id = "c2"  # type: ignore[misc]

    def test_fields(self) -> None:
        cap = CapabilitySchema(id="c1", verb="search", input_schema={"q": "str"}, output_schema={"r": "list"}, tool_id="t1")
        assert cap.id == "c1"
        assert cap.verb == "search"
        assert cap.tool_id == "t1"


class TestSkillDefinition:
    def test_frozen(self) -> None:
        skill = SkillDefinition(id="s1", name="Web Search", domain="research", capabilities_required=("c1",), preconditions=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            skill.name = "X"  # type: ignore[misc]

    def test_fields(self) -> None:
        skill = SkillDefinition(id="s1", name="Web Search", domain="research", capabilities_required=("c1", "c2"), preconditions=("auth",))
        assert skill.capabilities_required == ("c1", "c2")
        assert skill.preconditions == ("auth",)


class TestAgentDeclaration:
    def test_frozen(self) -> None:
        agent = AgentDeclaration(id="a1", role="researcher", skills_allowed=frozenset(["s1"]))
        with pytest.raises(dataclasses.FrozenInstanceError):
            agent.role = "X"  # type: ignore[misc]


class TestPlaybookDefinition:
    def test_frozen(self) -> None:
        pb = PlaybookDefinition(
            id="pb1", name="Test", executor_type="single_agent",
            agents=(AgentDeclaration(id="a1", role="r", skills_allowed=frozenset()),),
            parallel=False,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            pb.name = "X"  # type: ignore[misc]

    def test_composition(self) -> None:
        agent = AgentDeclaration(id="a1", role="researcher", skills_allowed=frozenset(["s1", "s2"]))
        pb = PlaybookDefinition(id="pb1", name="Deep", executor_type="crewai", agents=(agent,), parallel=True)
        assert pb.agents[0].skills_allowed == frozenset(["s1", "s2"])
        assert pb.parallel is True


class TestMode:
    def test_frozen(self) -> None:
        mode = Mode(
            id="m1", name="Default", soul_overlay_path="x.md",
            company_subset_paths=("a.yaml",),
            skills_allowlist=frozenset(["s1"]),
            playbooks_allowed=frozenset(["pb1"]),
            tools_allowlist=frozenset(["t1"]),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            mode.name = "X"  # type: ignore[misc]

    def test_frozensets(self) -> None:
        mode = Mode(
            id="m1", name="Default", soul_overlay_path="x.md",
            company_subset_paths=(),
            skills_allowlist=frozenset(["s1", "s2"]),
            playbooks_allowed=frozenset(["pb1"]),
            tools_allowlist=frozenset(["t1", "t2"]),
        )
        assert "s1" in mode.skills_allowlist
        assert "t2" in mode.tools_allowlist


class TestModeContext:
    def test_frozen(self) -> None:
        ctx = ModeContext(
            soul_overlay="overlay",
            company_context={"key": "val"},
            skills_allowed=frozenset(["s1"]),
            playbooks_allowed=frozenset(["pb1"]),
            tools_allowed=frozenset(["t1"]),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.soul_overlay = "X"  # type: ignore[misc]

    def test_fields(self) -> None:
        ctx = ModeContext(
            soul_overlay="overlay",
            company_context={"industry": "tech"},
            skills_allowed=frozenset(["s1"]),
            playbooks_allowed=frozenset(["pb1"]),
            tools_allowed=frozenset(["t1"]),
        )
        assert ctx.company_context["industry"] == "tech"
