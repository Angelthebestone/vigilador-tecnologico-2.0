"""Tests for ``SkillCatalog`` + integration into ``SkillLoader``.

Covers:

* Taxonomy load, validation, and category lookup precedence
  (recategorize > mapping > default).
* Alias / disabled filtering at load time.
* Sub-category tag injection.
* Real-tree integration: load `config/skills/{taxonomy,catalog}.yaml`
  and verify K-Dense & agency-agents skills receive the expected
  canonical categories.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.skills_marketplace.skill_catalog import (
    SkillCatalog,
    SkillCatalogError,
    SkillCatalogPort,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


@pytest.fixture
def minimal_taxonomy(tmp_path):
    tax = tmp_path / "taxonomy.yaml"
    _write_yaml(
        tax,
        """
        version: "1.0"
        categories:
          - id: research
            label: "Research"
            sub_categories:
              - id: bio
                label: "Bio"
          - id: engineering
            label: "Engineering"
          - id: specialized
            label: "Specialized"
        mapping:
          k_dense: research
          engineering: engineering
        default_category: specialized
        """,
    )
    return tax


@pytest.fixture
def overrides_yaml(tmp_path):
    cat = tmp_path / "catalog.yaml"
    _write_yaml(
        cat,
        """
        version: "1.0"
        aliases:
          k_dense.alias-of-bio: k_dense.adaptyv
        disabled:
          - k_dense.disabled-skill
        recategorize:
          k_dense.tensorflow: engineering
        sub_category:
          k_dense.adaptyv: bio
        """,
    )
    return cat


# ---------------------------------------------------------------------------
# Taxonomy load + validation
# ---------------------------------------------------------------------------


def test_load_minimal_taxonomy_succeeds(minimal_taxonomy):
    catalog = SkillCatalog(taxonomy_path=minimal_taxonomy)
    assert catalog.category_ids() == ["research", "engineering", "specialized"]
    cats = catalog.categories()
    assert cats[0].label == "Research"
    assert cats[0].sub_categories[0].id == "bio"


def test_taxonomy_with_unknown_mapping_target_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    _write_yaml(
        bad,
        """
        categories:
          - id: research
            label: "R"
        mapping:
          k_dense: nonexistent_category
        """,
    )
    with pytest.raises(SkillCatalogError, match="not a declared category"):
        SkillCatalog(taxonomy_path=bad)


def test_taxonomy_invalid_yaml_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("categories: [unclosed", encoding="utf-8")
    with pytest.raises(SkillCatalogError, match="invalid"):
        SkillCatalog(taxonomy_path=bad)


def test_missing_taxonomy_file_raises(tmp_path):
    with pytest.raises(SkillCatalogError, match="not found"):
        SkillCatalog(taxonomy_path=tmp_path / "absent.yaml")


# ---------------------------------------------------------------------------
# category_for / sub_category_for / is_active resolution
# ---------------------------------------------------------------------------


def test_category_for_uses_mapping(minimal_taxonomy):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy)
    assert cat.category_for("k_dense.adaptyv", "k_dense") == "research"
    assert cat.category_for("agency_agents.engineering.x", "engineering") == "engineering"


def test_category_for_falls_back_to_default(minimal_taxonomy):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy)
    assert cat.category_for("anything", "no-such-hint") == "specialized"


def test_recategorize_overrides_mapping(minimal_taxonomy, overrides_yaml):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy, catalog_path=overrides_yaml)
    # Without override: would have been "research" via the k_dense mapping.
    assert cat.category_for("k_dense.tensorflow", "k_dense") == "engineering"
    # Other entries still use mapping default.
    assert cat.category_for("k_dense.adaptyv", "k_dense") == "research"


def test_sub_category_for_returns_override(minimal_taxonomy, overrides_yaml):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy, catalog_path=overrides_yaml)
    assert cat.sub_category_for("k_dense.adaptyv") == "bio"
    assert cat.sub_category_for("k_dense.tensorflow") is None


def test_alias_makes_skill_inactive(minimal_taxonomy, overrides_yaml):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy, catalog_path=overrides_yaml)
    # alias key is inactive (loader will skip it).
    assert cat.is_active("k_dense.alias-of-bio") is False
    # canonical_for resolves the alias.
    assert cat.canonical_for("k_dense.alias-of-bio") == "k_dense.adaptyv"
    # The canonical itself remains active.
    assert cat.is_active("k_dense.adaptyv") is True


def test_disabled_makes_skill_inactive(minimal_taxonomy, overrides_yaml):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy, catalog_path=overrides_yaml)
    assert cat.is_active("k_dense.disabled-skill") is False


def test_alias_chain_raises(tmp_path, minimal_taxonomy):
    chain = tmp_path / "chain.yaml"
    _write_yaml(
        chain,
        """
        aliases:
          a: b
          b: c
        """,
    )
    with pytest.raises(SkillCatalogError, match="alias chain"):
        SkillCatalog(taxonomy_path=minimal_taxonomy, catalog_path=chain)


def test_skill_catalog_satisfies_port_protocol(minimal_taxonomy):
    cat = SkillCatalog(taxonomy_path=minimal_taxonomy)
    assert isinstance(cat, SkillCatalogPort)


# ---------------------------------------------------------------------------
# SkillLoader integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loader_skips_alias_and_tags_canonical_category(
    tmp_path, minimal_taxonomy, overrides_yaml
):
    """Real adapter scan + catalog filter + tag injection."""
    from vigilancia_multiagente.enterprise.skills_marketplace.hash_tracker import (
        HashTracker,
    )
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_loader import (
        SkillLoader,
    )
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import (
        SkillRegistry,
    )

    class _Embed:
        async def embed(self, text, task_type=""):
            return [0.1, 0.2, 0.3]

    class _ToolReg:
        async def is_capability_available(self, name):
            return True

    # Seed a fake K-Dense vendor with two skills: one normal, one disabled.
    kdense = tmp_path / "kdense"
    (kdense / "skills" / "adaptyv").mkdir(parents=True)
    (kdense / "skills" / "adaptyv" / "SKILL.md").write_text(
        "---\nname: adaptyv\ndescription: bio tool\nlicense: MIT\n---\nbody",
        encoding="utf-8",
    )
    (kdense / "skills" / "disabled-skill").mkdir(parents=True)
    (kdense / "skills" / "disabled-skill" / "SKILL.md").write_text(
        "---\nname: disabled-skill\ndescription: x\nlicense: MIT\n---\nbody",
        encoding="utf-8",
    )

    catalog = SkillCatalog(taxonomy_path=minimal_taxonomy, catalog_path=overrides_yaml)
    registry = SkillRegistry(_Embed(), _ToolReg())
    loader = SkillLoader(
        registry=registry,
        tool_registry=_ToolReg(),
        sources_enabled=["external:k-dense"],
        curated_path=tmp_path / "no-curated",
        learned_path=tmp_path / "no-learned",
        k_dense_vendor_path=kdense,
        agency_agents_vendor_path=tmp_path / "no-agency",
        catalog=catalog,
        hash_tracker=HashTracker(tmp_path / "hashes.json"),
    )
    result = await loader.load_all()
    assert result.total_registered == 1
    assert result.total_skipped_by_catalog == 1
    cards = registry.get_cards()
    assert len(cards) == 1
    card = cards[0]
    assert card.id == "k_dense.adaptyv"
    # First tag must be the canonical category.
    assert card.tags[0] == "research"
    # Sub-category tag in slot 1 (since override declares one).
    assert card.tags[1] == "sub:bio"


@pytest.mark.asyncio
async def test_loader_without_catalog_keeps_legacy_tags(tmp_path):
    """When ``catalog`` is None, no taxonomy mutation happens."""
    from vigilancia_multiagente.enterprise.skills_marketplace.hash_tracker import (
        HashTracker,
    )
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_loader import (
        SkillLoader,
    )
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import (
        SkillRegistry,
    )

    class _Embed:
        async def embed(self, text, task_type=""):
            return [0.1, 0.2, 0.3]

    class _ToolReg:
        async def is_capability_available(self, name):
            return True

    kdense = tmp_path / "kdense"
    (kdense / "skills" / "adaptyv").mkdir(parents=True)
    (kdense / "skills" / "adaptyv" / "SKILL.md").write_text(
        "---\nname: adaptyv\ndescription: x\nlicense: MIT\n---\nbody",
        encoding="utf-8",
    )

    registry = SkillRegistry(_Embed(), _ToolReg())
    loader = SkillLoader(
        registry=registry,
        tool_registry=_ToolReg(),
        sources_enabled=["external:k-dense"],
        curated_path=tmp_path / "no",
        learned_path=tmp_path / "no",
        k_dense_vendor_path=kdense,
        agency_agents_vendor_path=tmp_path / "no",
        catalog=None,
        hash_tracker=HashTracker(tmp_path / "hashes.json"),
    )
    result = await loader.load_all()
    assert result.total_registered == 1
    assert result.total_skipped_by_catalog == 0
    card = registry.get_cards()[0]
    # Legacy tags from the adapter, no canonical category prepended.
    assert "research" not in card.tags
    assert "k-dense" in card.tags  # adapter's default tag


# ---------------------------------------------------------------------------
# Real-tree integration: load the actual config/skills/taxonomy.yaml
# ---------------------------------------------------------------------------


def test_real_taxonomy_loads_cleanly():
    repo = Path(__file__).resolve().parents[3]
    tax = repo / "config" / "skills" / "taxonomy.yaml"
    cat = repo / "config" / "skills" / "catalog.yaml"
    if not tax.is_file():
        pytest.skip("taxonomy.yaml not present in this checkout")
    catalog = SkillCatalog(
        taxonomy_path=tax,
        catalog_path=cat if cat.is_file() else None,
    )
    cats = catalog.category_ids()
    assert "research" in cats
    assert "engineering" in cats
    # All catalog.recategorize targets must reference declared categories;
    # construction would have raised otherwise. We assert at least one
    # known override resolves correctly.
    assert catalog.category_for("k_dense.tensorflow", "k_dense") in {"ai-ml", "research"}
