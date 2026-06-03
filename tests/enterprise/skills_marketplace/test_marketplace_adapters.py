"""Tests for K-Dense + Agency-Agents adapters (Spec 021 D2 / FR-031/032).

Each adapter is exercised against a synthetic vendor directory under
``tmp_path`` so the live ``_vendor/`` clone is not a test dependency.
"""

from __future__ import annotations

from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.agency_agents_adapter import (
    AgencyAgentsAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import (
    KDenseAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import SkillSource

# ---------------------------------------------------------------------------
# K-Dense
# ---------------------------------------------------------------------------


def _write_kdense_skill(root: Path, skill_id: str, frontmatter: str, body: str = "") -> Path:
    skill_dir = root / "skills" / skill_id
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return skill_file


def test_k_dense_adapter_scans_well_formed_skill(tmp_path):
    _write_kdense_skill(
        tmp_path,
        "adaptyv",
        'name: adaptyv\nauthor: "K-Dense, Inc."\n'
        'description: "How to use the Adaptyv API"\nlicense: MIT\n'
        'compatibility: "Python 3.10+"\nmetadata:\n  version: "1.2"\n',
        "# Adaptyv\nbody content here.",
    )
    adapter = KDenseAdapter(tmp_path)
    triples = adapter.scan()
    assert len(triples) == 1
    card, summary, body = triples[0]
    assert card.id == "k_dense.adaptyv"
    assert card.source == SkillSource.EXTERNAL_K_DENSE
    assert "k-dense" in card.tags
    assert "v1.2" in card.tags
    assert card.content_hash  # 16-char prefix
    assert summary.audit_level == "standard"
    assert "body content here." in body


def test_k_dense_adapter_skips_invalid_yaml(tmp_path):
    _write_kdense_skill(
        tmp_path,
        "broken",
        "name: broken\ndescription: : : : invalid",  # malformed YAML
    )
    triples = KDenseAdapter(tmp_path).scan()
    assert triples == []


def test_k_dense_adapter_skips_skills_without_frontmatter(tmp_path):
    skill_dir = tmp_path / "skills" / "no_meta"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# just a body", encoding="utf-8")
    assert KDenseAdapter(tmp_path).scan() == []


def test_k_dense_adapter_emits_unique_ids_per_skill(tmp_path):
    _write_kdense_skill(tmp_path, "alpha", 'name: alpha\ndescription: "x"\nlicense: MIT\n')
    _write_kdense_skill(tmp_path, "beta", 'name: beta\ndescription: "y"\nlicense: MIT\n')
    triples = KDenseAdapter(tmp_path).scan()
    ids = [t[0].id for t in triples]
    assert sorted(ids) == ["k_dense.alpha", "k_dense.beta"]


# ---------------------------------------------------------------------------
# Agency-Agents
# ---------------------------------------------------------------------------


def _write_agent(root: Path, division: str, agent: str, frontmatter: str, body: str = "") -> Path:
    div_dir = root / division
    div_dir.mkdir(parents=True, exist_ok=True)
    agent_file = div_dir / f"{agent}.md"
    agent_file.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return agent_file


def test_agency_adapter_emits_division_tagged_skill(tmp_path):
    _write_agent(
        tmp_path,
        "engineering",
        "ai-data-remediation",
        'name: AI Data Remediation Engineer\n'
        'description: "Specialist in self-healing data pipelines"\n'
        'color: green\nemoji: 🧬\nvibe: "Surgical precision"',
        "# Body\nlong agent prompt.",
    )
    adapter = AgencyAgentsAdapter(tmp_path)
    triples = adapter.scan()
    assert len(triples) == 1
    card, summary, _ = triples[0]
    assert card.id == "agency_agents.engineering.ai-data-remediation"
    assert card.display_name == "AI Data Remediation Engineer"
    assert card.source == SkillSource.EXTERNAL_AGENCY_AGENTS
    assert "engineering" in card.tags
    assert "color:green" in card.tags
    assert "emoji:🧬" in card.tags
    # All agency-agents are high-audit per FR-032 mapping.
    assert summary.audit_level == "alto"
    assert summary.examples == ["Surgical precision"]


def test_agency_adapter_skips_well_known_meta_dirs(tmp_path):
    # .github, examples, scripts, integrations must be skipped.
    _write_agent(tmp_path, ".github", "config", 'name: x\ndescription: "y"')
    _write_agent(tmp_path, "examples", "demo", 'name: x\ndescription: "y"')
    _write_agent(tmp_path, "engineering", "real_agent",
                 'name: real_agent\ndescription: "y"\ncolor: blue')
    triples = AgencyAgentsAdapter(tmp_path).scan()
    assert len(triples) == 1
    assert triples[0][0].id.startswith("agency_agents.engineering.")


def test_agency_adapter_handles_multiple_divisions(tmp_path):
    _write_agent(tmp_path, "engineering", "a", 'name: a\ndescription: "x"')
    _write_agent(tmp_path, "design", "b", 'name: b\ndescription: "y"')
    _write_agent(tmp_path, "marketing", "c", 'name: c\ndescription: "z"')
    triples = AgencyAgentsAdapter(tmp_path).scan()
    divisions = {tag for t in triples for tag in t[0].tags
                 if tag in ("engineering", "design", "marketing")}
    assert divisions == {"engineering", "design", "marketing"}


def test_agency_adapter_returns_empty_for_missing_dir(tmp_path):
    """A missing vendor path is logged + empty list (no crash)."""
    triples = AgencyAgentsAdapter(tmp_path / "nope").scan()
    assert triples == []


# ---------------------------------------------------------------------------
# Cross-adapter: ensure ids never collide across both sources
# ---------------------------------------------------------------------------


def test_no_id_collisions_across_marketplaces(tmp_path):
    """A K-Dense skill with id 'engineering' must not collide with an agency-agent."""
    kdense_root = tmp_path / "kdense"
    agency_root = tmp_path / "agency"
    _write_kdense_skill(kdense_root, "engineering", 'name: engineering\ndescription: "x"')
    _write_agent(agency_root, "engineering", "engineering",
                 'name: engineering\ndescription: "y"')
    kd = KDenseAdapter(kdense_root).scan()
    ag = AgencyAgentsAdapter(agency_root).scan()
    all_ids = [t[0].id for t in kd + ag]
    assert len(all_ids) == len(set(all_ids))
    # Distinct prefixes guarantee separation.
    assert any(i.startswith("k_dense.") for i in all_ids)
    assert any(i.startswith("agency_agents.") for i in all_ids)
