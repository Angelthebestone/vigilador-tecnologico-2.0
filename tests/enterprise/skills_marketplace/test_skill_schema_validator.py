"""Tests for skill_schema_validator."""

from vigilancia_multiagente.enterprise.skills_marketplace.skill_schema_validator import (
    normalize_id,
    validate_frontmatter,
)
import pytest


def test_valid_frontmatter_all_fields():
    raw = {"id": "my-skill", "description": "Does stuff", "source": "curated", "tags": ["a"]}
    result = validate_frontmatter(raw)
    assert result.valid is True
    assert result.errors == []


def test_valid_frontmatter_only_required():
    raw = {"name": "my-skill", "description": "Does stuff"}
    result = validate_frontmatter(raw)
    assert result.valid is True


def test_missing_id_and_name_fails():
    raw = {"description": "Does stuff"}
    result = validate_frontmatter(raw, path="test.md")
    assert result.valid is False
    assert any("id" in e or "name" in e for e in result.errors)


def test_invalid_yaml_type_fails():
    raw = {"id": "", "description": ""}
    result = validate_frontmatter(raw, path="bad.md")
    assert result.valid is False


def test_name_normalized_to_id():
    raw = {"name": "speckit-plan", "description": "Plans things"}
    result = validate_frontmatter(raw)
    assert result.valid is True
    assert result.normalized["id"] == "speckit-plan"


def test_normalize_id_with_name():
    assert normalize_id({"name": "foo"}) == "foo"


def test_normalize_id_missing_raises():
    with pytest.raises(ValueError, match="id"):
        normalize_id({})
