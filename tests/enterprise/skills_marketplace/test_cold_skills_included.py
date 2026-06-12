"""T047: Verify _cold/ skills are included when cold_skills_enabled=True."""

import tempfile
from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.agency_agents_adapter import (
    AgencyAgentsAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import KDenseAdapter


def test_k_dense_cold_included():
    """K-Dense skills in _cold/ are included when enabled."""
    with tempfile.TemporaryDirectory() as tmp:
        vendor = Path(tmp) / "k_dense" / "skills"
        cold_dir = vendor / "_cold" / "cold-skill"
        cold_dir.mkdir(parents=True)
        (cold_dir / "SKILL.md").write_text(
            "---\nid: cold-skill\ndescription: A cold skill\n---\nBody\n"
        )

        adapter = KDenseAdapter(Path(tmp) / "k_dense", cold_skills_enabled=True)
        results = adapter.scan()
        skill_ids = [card.id for card, _, _ in results]
        assert "k_dense.cold-skill" in skill_ids


def test_agency_agents_cold_included():
    """Agency-agents skills in _cold/ are included when enabled."""
    with tempfile.TemporaryDirectory() as tmp:
        vendor = Path(tmp) / "agency_agents"
        cold_div = vendor / "_cold" / "cold-division"
        cold_div.mkdir(parents=True)
        (cold_div / "agent.md").write_text(
            "---\ndescription: Cold agent\nname: Cold Agent\n---\nBody\n"
        )

        adapter = AgencyAgentsAdapter(vendor, cold_skills_enabled=True)
        results = adapter.scan()
        skill_ids = [card.id for card, _, _ in results]
        assert any("cold-division" in sid for sid in skill_ids)
