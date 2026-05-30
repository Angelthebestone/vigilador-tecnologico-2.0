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
            claude_local_path=Path(tmp) / "claude",
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
            claude_local_path=Path(tmp) / "claude",
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
            claude_local_path=Path(tmp) / "claude",
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
            claude_local_path=Path(tmp) / "claude",
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
            sources_enabled=["curated", "learned", "external:claude-local"],
            curated_path=Path(tmp) / "curated",
            learned_path=Path(tmp) / "learned",
            claude_local_path=Path(tmp) / "claude",
        )
        result = await loader.load_all()
        assert result.total_registered == 0
        assert result.errors == []


@pytest.mark.asyncio
async def test_hash_change_marks_pending_revalidation():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "skills"
        skill_dir = base / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_content = """\
---
name: "my-skill"
description: "A skill"
---

Body.
"""
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # Pre-populate hash tracker with a DIFFERENT hash
        tracker = HashTracker(Path(tmp) / "hashes.json")
        tracker.update("my-skill", "old_hash_that_differs")

        tool_reg = FakeToolRegistry()
        registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
        loader = SkillLoader(
            registry=registry,
            tool_registry=tool_reg,
            sources_enabled=["external:claude-local"],
            curated_path=Path(tmp) / "curated",
            learned_path=Path(tmp) / "learned",
            claude_local_path=base,
            hash_tracker=tracker,
        )
        await loader.load_all()
        # The skill should be pending revalidation
        all_cards = list(registry._cards.values())
        assert len(all_cards) == 1
        assert all_cards[0].state == SkillState.PENDING_REVALIDATION


@pytest.mark.asyncio
async def test_load_real_claude_skills():
    """Integration: load real .claude/skills/ — expects >= 14."""
    repo_root = Path(__file__).resolve().parents[3]
    skills_path = repo_root / ".claude" / "skills"
    if not skills_path.is_dir():
        return

    tool_reg = FakeToolRegistry()
    registry = SkillRegistry(FakeEmbeddingGateway(), tool_reg)
    loader = SkillLoader(
        registry=registry,
        tool_registry=tool_reg,
        sources_enabled=["external:claude-local"],
        curated_path=repo_root / "config" / "skills" / "curated",
        learned_path=repo_root / "config" / "skills" / "learned",
        claude_local_path=skills_path,
    )
    result = await loader.load_all()
    assert result.total_registered >= 14
