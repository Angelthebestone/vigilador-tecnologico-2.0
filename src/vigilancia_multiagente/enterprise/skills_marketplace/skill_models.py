"""Skill marketplace data models — enums and dataclasses for skill registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SkillSource(StrEnum):
    CURATED = "curated"
    LEARNED = "learned"
    EXTERNAL_CLAUDE_LOCAL = "external:claude-local"


class SkillState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PENDING_REVALIDATION = "pending_revalidation"


@dataclass
class SkillCard:
    """Minimal metadata for a registered skill (level 1 — progressive loading)."""

    id: str
    display_name: str
    description: str
    tags: list[str] = field(default_factory=list)
    source: SkillSource = SkillSource.CURATED
    mode_compatible: list[str] = field(default_factory=list)
    state: SkillState = SkillState.AVAILABLE
    content_hash: str = ""
    requires_sandbox: bool = False
    path: str = ""


@dataclass
class SkillSummary:
    """Intermediate detail (level 2 — progressive loading)."""

    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    required_company_files: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    audit_level: str = "standard"


@dataclass
class SkillBody:
    """Full content (level 3 — loaded on demand)."""

    full_content: str = ""
    procedure_sections: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)


@dataclass
class CommandSkill(SkillCard):
    """Skill from .claude/skills with command-specific attributes."""

    argument_hint: str = ""
    user_invocable: bool = True
