"""F2.E — verify the runtime no longer touches ``.claude/skills/`` (Spec 021 D3).

Per FR-033, the four canonical sources are:
``[curated, learned, external:k-dense, external:agency-agents]``.
``external:claude-local`` is **dropped** from runtime even though the
adapter file remains in the tree as a reference.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


def test_skill_loader_module_no_longer_imports_claude_local_adapter():
    """The runtime path must not import ``ClaudeLocalAdapter`` (FR-033)."""
    from vigilancia_multiagente.enterprise.skills_marketplace import skill_loader

    src = inspect.getsource(skill_loader)
    assert "ClaudeLocalAdapter" not in src, (
        "skill_loader.py must not import ClaudeLocalAdapter at runtime "
        "(spec 021 D3 — claude-local removed from runtime)."
    )
    assert "_load_external_claude_local" not in src, (
        "_load_external_claude_local branch must be removed (FR-033)."
    )


def test_skill_loader_supports_k_dense_and_agency_agents_branches():
    from vigilancia_multiagente.enterprise.skills_marketplace import skill_loader

    src = inspect.getsource(skill_loader)
    assert "external:k-dense" in src, "skill_loader must wire external:k-dense source"
    assert "external:agency-agents" in src, (
        "skill_loader must wire external:agency-agents source"
    )


def test_settings_default_skills_sources_matches_d3():
    """``settings.skills_sources_enabled`` lists exactly the 4 canonical sources."""
    from vigilancia_multiagente.config.settings import Settings

    s = Settings()
    sources = list(s.skills_sources_enabled)
    expected = ["curated", "learned", "external:k-dense", "external:agency-agents"]
    assert sources == expected, (
        f"D3: skills_sources_enabled must be {expected}, got {sources}"
    )


@pytest.mark.asyncio
async def test_skill_loader_load_all_with_external_branches_does_not_call_claude_local(tmp_path):
    """Sanity smoke: loader runs to completion with the new sources only."""
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_loader import (
        SkillLoader,
    )
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import (
        SkillRegistry,
    )

    class _StubEmbed:
        async def embed(self, text: str, task_type: str = "") -> list[float]:
            return [0.1, 0.2, 0.3]

        async def embed_document(self, text: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        async def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3]] * len(texts)

    class _StubToolReg:
        async def is_capability_available(self, name: str) -> bool:
            return True

    # Empty curated/learned dirs + missing _vendor → loader runs cleanly.
    (tmp_path / "curated").mkdir()
    (tmp_path / "learned").mkdir()
    registry = SkillRegistry(_StubEmbed(), _StubToolReg())
    loader = SkillLoader(
        registry=registry,
        tool_registry=_StubToolReg(),
        sources_enabled=[
            "curated", "learned", "external:k-dense", "external:agency-agents",
        ],
        curated_path=tmp_path / "curated",
        learned_path=tmp_path / "learned",
        k_dense_vendor_path=tmp_path / "no-k-dense-here",
        agency_agents_vendor_path=tmp_path / "no-agency-agents-here",
    )
    result = await loader.load_all()
    assert result.errors == []
    assert result.total_registered == 0  # empty dirs


def test_runtime_does_not_open_claude_skills_dir_anywhere(tmp_path: Path):
    """No call site in skill_loader / settings opens ``.claude/skills/`` (D3)."""
    from vigilancia_multiagente.config import settings
    from vigilancia_multiagente.enterprise.skills_marketplace import skill_loader

    src_loader = inspect.getsource(skill_loader)
    src_settings = inspect.getsource(settings)
    # No live Path() construction or rglob/glob/iterdir against .claude/skills.
    for pattern in ('Path(".claude', '".claude/skills"', "'.claude/skills'"):
        assert pattern not in src_loader, (
            f"skill_loader.py contains live reference '{pattern}' (D3 violation)"
        )
        assert pattern not in src_settings, (
            f"settings.py contains live reference '{pattern}' (D3 violation)"
        )
