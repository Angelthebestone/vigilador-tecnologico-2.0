"""Mode schema: dataclasses for YAML-based mode configuration (spec 011)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CompanyGeo:
    """Geographic context for a mode. country is required."""

    country: str
    department: str | None = None
    municipality: str | None = None
    timezone: str | None = None


@dataclass(frozen=True)
class SoulOverlay:
    """Personality overlay for a mode."""

    tone: str = ""
    vocabulary_emphasis: list[str] = field(default_factory=list)
    do_rules: list[str] = field(default_factory=list)
    dont_rules: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompanySubset:
    """Subset of company files relevant to a mode."""

    files: list[str] = field(default_factory=list)
    sections_filter: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillsConfig:
    """Skills configuration for a mode."""

    categories: list[str] = field(default_factory=list)
    individual: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlaybooksConfig:
    """Playbooks configuration for a mode."""

    default: str = "general"
    allowed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolsConfig:
    """Tools configuration for a mode: domains and exclusions."""

    domains: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModeSettings:
    """Optional mode-level settings."""

    language_default: str = "es"
    intensity: str = "REACTIVE"


@dataclass(frozen=True)
class ModeConfig:
    """Full configuration of a mode loaded from YAML."""

    id: str
    display_name: str
    description: str
    version: str
    status: str = "active"
    soul_overlay: SoulOverlay | None = None
    company_subset: CompanySubset | None = None
    company_geo: CompanyGeo | None = None
    skills: SkillsConfig | None = None
    playbooks: PlaybooksConfig = field(default_factory=PlaybooksConfig)
    tools: ToolsConfig | None = None
    mode_settings: ModeSettings | None = None


class ModeSchemaError(Exception):
    """Raised when a mode YAML fails schema validation."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"Mode schema error in '{path}': {detail}")


def parse_mode_yaml(path: Path) -> ModeConfig:
    """Parse a mode YAML file into a ModeConfig dataclass.

    Raises ModeSchemaError with path context on validation failure.
    """
    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)

    if not isinstance(data, dict):
        raise ModeSchemaError(path, "expected a YAML mapping at top level")

    # Required fields
    for required in ("id", "display_name", "version"):
        if required not in data:
            raise ModeSchemaError(path, f"missing required field '{required}'")

    # Parse company_geo if present
    company_geo: CompanyGeo | None = None
    if "company_geo" in data:
        geo_data = data["company_geo"]
        if not isinstance(geo_data, dict) or "country" not in geo_data:
            raise ModeSchemaError(path, "company_geo requires 'country' field")
        company_geo = CompanyGeo(
            country=geo_data["country"],
            department=geo_data.get("department"),
            municipality=geo_data.get("municipality"),
            timezone=geo_data.get("timezone"),
        )

    # Parse soul_overlay
    soul_overlay: SoulOverlay | None = None
    if "soul_overlay" in data:
        so = data["soul_overlay"]
        soul_overlay = SoulOverlay(
            tone=so.get("tone", ""),
            vocabulary_emphasis=so.get("vocabulary_emphasis", []),
            do_rules=so.get("do_rules", []),
            dont_rules=so.get("dont_rules", []),
        )

    # Parse tools
    tools: ToolsConfig | None = None
    if "tools" in data:
        t = data["tools"]
        tools = ToolsConfig(
            domains=t.get("domains", []),
            excluded=t.get("excluded", []),
        )

    # Parse playbooks
    pb_data = data.get("playbooks", {})
    playbooks = PlaybooksConfig(
        default=pb_data.get("default", "general"),
        allowed=pb_data.get("allowed", []),
    )

    # Parse skills
    skills: SkillsConfig | None = None
    if "skills" in data:
        s = data["skills"]
        skills = SkillsConfig(
            categories=s.get("categories", []),
            individual=s.get("individual", []),
            excluded=s.get("excluded", []),
        )

    # Parse company_subset
    company_subset: CompanySubset | None = None
    if "company_subset" in data:
        cs = data["company_subset"]
        company_subset = CompanySubset(
            files=cs.get("files", []),
            sections_filter=cs.get("sections_filter", []),
        )

    # Parse mode_settings
    mode_settings: ModeSettings | None = None
    if "mode_settings" in data:
        ms = data["mode_settings"]
        mode_settings = ModeSettings(
            language_default=ms.get("language_default", "es"),
            intensity=ms.get("intensity", "REACTIVE"),
        )

    return ModeConfig(
        id=data["id"],
        display_name=data["display_name"],
        description=data.get("description", ""),
        version=data["version"],
        status=data.get("status", "active"),
        soul_overlay=soul_overlay,
        company_subset=company_subset,
        company_geo=company_geo,
        skills=skills,
        playbooks=playbooks,
        tools=tools,
        mode_settings=mode_settings,
    )
