"""T046: Verify _cold/ skills are excluded when cold_skills_enabled=False."""
import tempfile
from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import KDenseAdapter
from vigilancia_multiagente.enterprise.skills_marketplace.agency_agents_adapter import AgencyAgentsAdapter


def test_k_dense_cold_excluded():
    """K-Dense skills in _cold/ are excluded by default."""
    with tempfile.TemporaryDirectory() as tmp:
        vendor = Path(tmp) / "k_dense" / "skills"
        hot_dir = vendor / "hot-skill"
        hot_dir.mkdir(parents=True)
        (hot_dir / "SKILL.md").write_text("---\nid: hot-skill\ndescription: A hot skill\n---\nBody\n")

        cold_dir = vendor / "_cold" / "cold-skill"
        cold_dir.mkdir(parents=True)
        (cold_dir / "SKILL.md").write_text("---\nid: cold-skill\ndescription: A cold skill\n---\nBody\n")

        adapter = KDenseAdapter(Path(tmp) / "k_dense", cold_skills_enabled=False)
        results = adapter.scan()
        skill_ids = [card.id for card, _, _ in results]
        assert "k_dense.hot-skill" in skill_ids
        assert "k_dense.cold-skill" not in skill_ids


def test_agency_agents_cold_excluded():
    """Agency-agents skills in _cold/ are excluded by default."""
    with tempfile.TemporaryDirectory() as tmp:
        vendor = Path(tmp) / "agency_agents"
        hot_div = vendor / "hot-division"
        hot_div.mkdir(parents=True)
        (hot_div / "agent.md").write_text("---\ndescription: Hot agent\nname: Hot Agent\n---\nBody\n")

        cold_div = vendor / "_cold" / "cold-division"
        cold_div.mkdir(parents=True)
        (cold_div / "agent.md").write_text("---\ndescription: Cold agent\nname: Cold Agent\n---\nBody\n")

        adapter = AgencyAgentsAdapter(vendor, cold_skills_enabled=False)
        results = adapter.scan()
        skill_ids = [card.id for card, _, _ in results]
        assert any("hot-division" in sid for sid in skill_ids)
        assert not any("cold-division" in sid for sid in skill_ids)
