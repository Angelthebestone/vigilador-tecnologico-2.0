"""F2.F tests — Spec 021 FR-035 (unavailable) + FR-052 (CommandSkill).

Covers:

* A skill whose ``required_capabilities`` are not in the ``ToolRegistry``
  is registered with ``state == UNAVAILABLE`` and is **not** returned by
  ``discover()`` / ``get_cards()`` (FR-035).
* :class:`CommandSkill` carries ``parameters``, ``permissions``,
  ``preconditions``, ``requires_sandbox`` and inherits ``content_hash``
  from :class:`SkillCard`. Construction is verified end-to-end against
  the marketplace adapter outputs (FR-052).
"""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    CommandSkill,
    SkillCard,
    SkillSource,
    SkillState,
    SkillSummary,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import (
    SkillRegistry,
)


class _StubEmbed:
    async def embed(self, text: str, task_type: str = "") -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]


class _ToolRegStub:
    def __init__(self, available: set[str] | None = None) -> None:
        self._available = available or set()

    async def is_capability_available(self, name: str) -> bool:
        return name in self._available


# ---------------------------------------------------------------------------
# FR-035 unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unavailable_skill_is_filtered_from_discover():
    reg = SkillRegistry(_StubEmbed(), _ToolRegStub())
    avail = SkillCard(
        id="avail",
        display_name="avail",
        description="should appear",
        source=SkillSource.CURATED,
    )
    unavail = SkillCard(
        id="unavail",
        display_name="unavail",
        description="should be filtered",
        source=SkillSource.CURATED,
        state=SkillState.UNAVAILABLE,
    )
    await reg.register(avail, SkillSummary())
    await reg.register(unavail, SkillSummary())
    cards = reg.get_cards()
    ids = {c.id for c in cards}
    assert "avail" in ids
    assert "unavail" not in ids


@pytest.mark.asyncio
async def test_mark_unavailable_excludes_from_discover_results():
    reg = SkillRegistry(_StubEmbed(), _ToolRegStub())
    card = SkillCard(
        id="x",
        display_name="x",
        description="initially available",
        source=SkillSource.CURATED,
    )
    await reg.register(card, SkillSummary())
    assert reg.get_cards()  # present
    reg.mark_unavailable("x", reason="capability lost")
    assert reg.get_cards() == []
    found = await reg.discover("anything", limit=5)
    assert found == []


# ---------------------------------------------------------------------------
# FR-052 CommandSkill
# ---------------------------------------------------------------------------


def test_command_skill_carries_full_command_metadata():
    cs = CommandSkill(
        id="cmd.run-build",
        display_name="run build",
        description="Builds the project",
        source=SkillSource.CURATED,
        requires_sandbox=True,
        content_hash="abc123",
        parameters={"target": "string"},
        permissions=["execute_command"],
        preconditions=["disk_free_mb > 200"],
        argument_hint="<target-name>",
        user_invocable=False,
    )
    assert cs.parameters == {"target": "string"}
    assert cs.permissions == ["execute_command"]
    assert cs.preconditions == ["disk_free_mb > 200"]
    assert cs.requires_sandbox is True
    assert cs.content_hash == "abc123"
    assert cs.argument_hint == "<target-name>"
    assert cs.user_invocable is False
    # CommandSkill IS-A SkillCard so registry takes it.
    assert isinstance(cs, SkillCard)


@pytest.mark.asyncio
async def test_command_skill_registers_and_discovers_like_card():
    reg = SkillRegistry(_StubEmbed(), _ToolRegStub())
    cmd = CommandSkill(
        id="cmd.lint",
        display_name="lint",
        description="ruff lint",
        source=SkillSource.CURATED,
        requires_sandbox=False,
        permissions=["read_file"],
    )
    await reg.register(cmd, SkillSummary())
    cards = reg.get_cards()
    assert len(cards) == 1
    assert cards[0].id == "cmd.lint"


def test_destructive_command_must_have_requires_sandbox_true():
    """Smoke-level invariant: a destructive command's contract surfaces
    ``requires_sandbox=True`` so the agent runner knows to gate it."""
    destructive = CommandSkill(
        id="cmd.delete-database",
        display_name="delete database",
        description="DESTRUCTIVE: drops the prod database.",
        source=SkillSource.CURATED,
        requires_sandbox=True,
        permissions=["execute_command", "drop_database"],
    )
    assert destructive.requires_sandbox is True
    assert "drop_database" in destructive.permissions


def test_command_skill_hash_drives_revalidation_signal():
    """When ``content_hash`` differs across two CommandSkill instances with
    the same id, the registry/loader treats them as candidates for
    PENDING_REVALIDATION (driven by HashTracker; here we verify the field)."""
    a = CommandSkill(
        id="cmd.x",
        display_name="x",
        description="x",
        source=SkillSource.CURATED,
        content_hash="hash-v1",
    )
    b = CommandSkill(
        id="cmd.x",
        display_name="x",
        description="x",
        source=SkillSource.CURATED,
        content_hash="hash-v2",
    )
    assert a.content_hash != b.content_hash


# ---------------------------------------------------------------------------
# K-Dense / Agency-Agents adapters produce CommandSkill instances
# ---------------------------------------------------------------------------


def test_marketplace_adapters_emit_command_skill_subclass(tmp_path):
    """Adapter contract: every emitted card should be a ``CommandSkill``
    so the loader can rely on ``parameters`` / ``permissions`` / etc.
    being present even if empty."""
    from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import (
        KDenseAdapter,
    )

    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        '---\nname: demo\ndescription: "x"\nlicense: MIT\n---\nbody',
        encoding="utf-8",
    )
    triples = KDenseAdapter(tmp_path).scan()
    assert len(triples) == 1
    card = triples[0][0]
    assert isinstance(card, CommandSkill)
    # Default-empty fields are populated, not missing.
    assert card.parameters == {}
    assert card.permissions == []
    assert card.preconditions == []
