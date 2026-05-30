"""Tests for skill_registry."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    SkillCard,
    SkillSource,
    SkillState,
    SkillSummary,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import SkillRegistry


class FakeEmbeddingGateway:
    """Fake embedding gateway that returns vectors based on word overlap."""

    _VOCAB = ["generar", "reporte", "mensual", "deploy", "production", "plan", "skill"]

    async def embed(self, text: str, task_type: str = "") -> list[float]:
        lower = text.lower()
        return [1.0 if word in lower else 0.0 for word in self._VOCAB]

    async def embed_document(self, text: str) -> list[float]:
        return await self.embed(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class FakeToolRegistry:
    """Fake ToolRegistry exposing is_capability_available."""

    def __init__(self, available: set[str] | None = None) -> None:
        self._available = available or set()

    async def is_capability_available(self, name: str) -> bool:
        return name in self._available


def _card(id: str, source: SkillSource = SkillSource.CURATED, **kwargs) -> SkillCard:
    return SkillCard(
        id=id,
        display_name=id,
        description=kwargs.get("description", f"Skill {id}"),
        source=source,
        mode_compatible=kwargs.get("mode_compatible", []),
        state=kwargs.get("state", SkillState.AVAILABLE),
    )


def _summary(**kwargs) -> SkillSummary:
    return SkillSummary(**kwargs)


@pytest.fixture
def registry():
    return SkillRegistry(
        embedding_gateway=FakeEmbeddingGateway(),
        tool_registry=FakeToolRegistry(available={"template_render"}),
    )


@pytest.mark.asyncio
async def test_register_multiple_skills(registry: SkillRegistry):
    for i in range(5):
        await registry.register(_card(f"skill-{i}"), _summary())
    assert len(registry.get_cards()) == 5


@pytest.mark.asyncio
async def test_duplicate_same_source_raises(registry: SkillRegistry):
    await registry.register(_card("dup"), _summary())
    with pytest.raises(ValueError, match="Duplicate"):
        await registry.register(_card("dup"), _summary())


@pytest.mark.asyncio
async def test_discover_returns_candidates(registry: SkillRegistry):
    await registry.register(_card("report", description="generar reporte mensual"), _summary())
    await registry.register(_card("deploy", description="deploy to production"), _summary())
    results = await registry.discover("generar reporte mensual")
    assert len(results) >= 1
    assert results[0].id == "report"


@pytest.mark.asyncio
async def test_mode_filter_excludes(registry: SkillRegistry):
    await registry.register(_card("cfo-only", mode_compatible=["CFO"]), _summary())
    await registry.register(_card("universal"), _summary())
    results = registry.get_cards(mode="Vigilancia Tech")
    ids = [c.id for c in results]
    assert "cfo-only" not in ids
    assert "universal" in ids


@pytest.mark.asyncio
async def test_mode_empty_is_universal(registry: SkillRegistry):
    await registry.register(_card("any-mode", mode_compatible=[]), _summary())
    results = registry.get_cards(mode="CEO")
    assert any(c.id == "any-mode" for c in results)


@pytest.mark.asyncio
async def test_unavailable_not_in_discover(registry: SkillRegistry):
    card = _card("broken", state=SkillState.UNAVAILABLE)
    await registry.register(card, _summary())
    results = await registry.discover("anything")
    assert all(c.id != "broken" for c in results)


@pytest.mark.asyncio
async def test_deduplication_curated_wins(registry: SkillRegistry):
    await registry.register(
        _card("shared", source=SkillSource.CURATED, description="curated version"), _summary()
    )
    await registry.register(
        _card("shared", source=SkillSource.EXTERNAL_CLAUDE_LOCAL, description="external version"),
        _summary(),
    )
    cards = registry.get_cards()
    shared = [c for c in cards if c.id == "shared"]
    assert len(shared) == 1
    assert shared[0].source == SkillSource.CURATED


@pytest.mark.asyncio
async def test_get_cards_does_not_load_body(registry: SkillRegistry):
    await registry.register(_card("light"), _summary(), body_path="nonexistent.md")
    cards = registry.get_cards()
    assert len(cards) == 1
    # get_cards returns SkillCard, not SkillBody — no file read


@pytest.mark.asyncio
async def test_get_summary(registry: SkillRegistry):
    await registry.register(_card("s1"), _summary(required_capabilities=["cap_a"]))
    summary = registry.get_summary("s1")
    assert summary.required_capabilities == ["cap_a"]


@pytest.mark.asyncio
async def test_get_body_loads_file(registry: SkillRegistry, tmp_path):
    body_file = tmp_path / "SKILL.md"
    body_file.write_text("# Full content", encoding="utf-8")
    await registry.register(_card("full"), _summary(), body_path=str(body_file))
    body = registry.get_body("full")
    assert "Full content" in body.full_content
