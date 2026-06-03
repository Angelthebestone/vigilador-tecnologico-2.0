"""Tests for skill_loader."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.skills_marketplace.hash_tracker import HashTracker
from vigilancia_multiagente.enterprise.skills_marketplace.skill_loader import SkillLoader
from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import SkillState
from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import SkillRegistry


class FakeEmbeddingGateway:
    async def embed(self, text: str, task_type: str = "") -> list[float]:
        return [0.1, 0.2, 0.3]

    async def embed_document(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]] * len(texts)


class FakeToolRegistry:
    def __init__(self, available: set[str] | None = None) -> None:
        self._available = available or set()

    async def is_capability_available(self, name: str) -> bool:
        return name in self._available


def _write_skill(path: Path, skill_id: str, description: str = "A skill", caps: list[str] | None = None) -> None:
    caps_line = f"required_capabilities: {caps}" if caps else ""
    content = f"""\
---
id: "{skill_id}"
description: "{description}"
source: "curated"
{caps_line}
---

## Procedure

Steps here.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.asyncio
async def test_load_curated_skills():
    with tempfile.TemporaryDirectory() as tmp:
        curated = Path(tmp) / "curated"
        curated.mkdir()
        _write_skill(curated / "s1.md", "s1")
        _write_skill(curated / "s2.md", "s2")

        tool_reg = FakeToolRegistry()
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=["curated"],
            curated_path=curated,
            learned_path=Path(tmp) / "learned",
            k_dense_vendor_path=Path(tmp) / "k_dense",
            agency_agents_vendor_path=Path(tmp) / "agency",
        )
        result = await loader.load_all()
        assert result.total_registered == 2


@pytest.mark.asyncio
async def test_capability_missing_marks_unavailable():
    with tempfile.TemporaryDirectory() as tmp:
        curated = Path(tmp) / "curated"
        curated.mkdir()
        _write_skill(curated / "s1.md", "s1", caps=["missing_cap"])

        tool_reg = FakeToolRegistry(available=set())
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=["curated"],
            curated_path=curated,
            learned_path=Path(tmp) / "learned",
            k_dense_vendor_path=Path(tmp) / "k_dense",
            agency_agents_vendor_path=Path(tmp) / "agency",
        )
        result = await loader.load_all()
        assert result.total_unavailable == 1
        cards = registry.get_cards()
        assert len(cards) == 0  # unavailable not in get_cards


@pytest.mark.asyncio
async def test_empty_capabilities_always_available():
    with tempfile.TemporaryDirectory() as tmp:
        curated = Path(tmp) / "curated"
        curated.mkdir()
        _write_skill(curated / "s1.md", "s1")

        tool_reg = FakeToolRegistry(available=set())
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=["curated"],
            curated_path=curated,
            learned_path=Path(tmp) / "learned",
            k_dense_vendor_path=Path(tmp) / "k_dense",
            agency_agents_vendor_path=Path(tmp) / "agency",
        )
        result = await loader.load_all()
        assert result.total_registered == 1
        assert result.total_unavailable == 0


@pytest.mark.asyncio
async def test_disabled_source_not_loaded():
    with tempfile.TemporaryDirectory() as tmp:
        curated = Path(tmp) / "curated"
        curated.mkdir()
        _write_skill(curated / "s1.md", "s1")

        tool_reg = FakeToolRegistry()
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=[],  # Nothing enabled
            curated_path=curated,
            learned_path=Path(tmp) / "learned",
            k_dense_vendor_path=Path(tmp) / "k_dense",
            agency_agents_vendor_path=Path(tmp) / "agency",
        )
        result = await loader.load_all()
        assert result.total_registered == 0


@pytest.mark.asyncio
async def test_all_sources_empty_no_error():
    with tempfile.TemporaryDirectory() as tmp:
        tool_reg = FakeToolRegistry()
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=["curated", "learned", "external:k-dense", "external:agency-agents"],
            curated_path=Path(tmp) / "curated",
            learned_path=Path(tmp) / "learned",
            k_dense_vendor_path=Path(tmp) / "k_dense",
            agency_agents_vendor_path=Path(tmp) / "agency",
        )
        result = await loader.load_all()
        assert result.total_registered == 0
        assert result.errors == []


@pytest.mark.asyncio
async def test_hash_change_marks_pending_revalidation():
    """K-Dense skill with stale hash → pending_revalidation (parallel to claude-local previous behavior, FR-031)."""
    with tempfile.TemporaryDirectory() as tmp:
        # K-Dense layout: <vendor>/skills/<id>/SKILL.md
        base = Path(tmp) / "k_dense_vendor"
        skill_dir = base / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_content = """\
---
name: "my-skill"
description: "A skill"
---

Body.
"""
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # Pre-populate hash tracker with a DIFFERENT hash so the loader will
        # mark the skill as PENDING_REVALIDATION on the next scan.
        tracker = HashTracker(Path(tmp) / "hashes.json")
        tracker.update("k_dense.my-skill", "old_hash_that_differs")

        tool_reg = FakeToolRegistry()
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=["external:k-dense"],
            curated_path=Path(tmp) / "curated",
            learned_path=Path(tmp) / "learned",
            k_dense_vendor_path=base,
            agency_agents_vendor_path=Path(tmp) / "agency",
            hash_tracker=tracker,
        )
        await loader.load_all()
        all_cards = list(registry._cards.values())
        assert len(all_cards) == 1
        assert all_cards[0].state == SkillState.PENDING_REVALIDATION


@pytest.mark.asyncio
async def test_load_real_kdense_marketplace():
    """Integration: load real ``_vendor/k_dense`` (D2) — expects >= 1 skill."""
    repo_root = Path(__file__).resolve().parents[3]
    vendor_path = (
        repo_root / "src" / "vigilancia_multiagente" / "enterprise"
        / "skills_marketplace" / "_vendor" / "k_dense"
    )
    if not vendor_path.is_dir():
        return  # vendor not cloned in this checkout

    tool_reg = FakeToolRegistry()
    registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
    loader = SkillLoader(
        registry=registry,
        tool_registry=tool_reg,
        sources_enabled=["external:k-dense"],
        curated_path=repo_root / "config" / "skills" / "curated",
        learned_path=repo_root / "config" / "skills" / "learned",
        k_dense_vendor_path=vendor_path,
        agency_agents_vendor_path=repo_root / "no-agency-here",
    )
    result = await loader.load_all()
    assert result.total_registered >= 1
