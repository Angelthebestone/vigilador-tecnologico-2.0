"""Skill schema validator — validates SKILL.md frontmatter."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of frontmatter validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    normalized: dict[str, object] = field(default_factory=dict)


def normalize_id(frontmatter: dict[str, object]) -> str:
    """Extract skill id from frontmatter, accepting 'id' or 'name'."""
    skill_id = frontmatter.get("id") or frontmatter.get("name")
    if not skill_id or not isinstance(skill_id, str):
        raise ValueError("Frontmatter must contain 'id' or 'name' as non-empty string")
    return skill_id


def validate_frontmatter(raw_yaml: dict[str, object], path: str = "<unknown>") -> ValidationResult:
    """Validate frontmatter fields. Returns ValidationResult with errors if invalid."""
    errors: list[str] = []

    # Check id or name
    skill_id = raw_yaml.get("id") or raw_yaml.get("name")
    if not skill_id or not isinstance(skill_id, str):
        errors.append(f"{path}: missing required field 'id' or 'name'")

    # Check description
    description = raw_yaml.get("description")
    if not description or not isinstance(description, str):
        errors.append(f"{path}: missing required field 'description'")

    if errors:
        return ValidationResult(valid=False, errors=errors)

    normalized: dict[str, object] = dict(raw_yaml)
    if "name" in normalized and "id" not in normalized:
        normalized["id"] = normalized["name"]

    return ValidationResult(valid=True, normalized=normalized)
