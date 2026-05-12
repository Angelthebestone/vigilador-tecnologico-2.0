"""Loader for the canonical system base artifact.

Reads and validates ``system-base.md`` from the contracts directory.
Returns a ``SystemBase`` dataclass instance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from vigilancia_multiagente.domain.system_base import SystemBase

_REQUIRED_SECTIONS: tuple[str, ...] = (
    "tool_usage_policy",
    "safety_limits",
    "error_handling",
    "output_style",
    "model_behavior",
    "embedding_config",
)

_SECTION_HEADER_MAP: dict[str, str] = {
    "tool_usage_policy": "Global Rules (Tool Usage)",
    "safety_limits": "Safety Limits",
    "error_handling": "Error Handling",
    "output_style": "Output Style",
    "model_behavior": "Model Behavior",
    "embedding_config": "Embedding Configuration (Activo)",
}


class SystemBaseLoadError(RuntimeError):
    """Raised when the system base artifact is missing, invalid, or incomplete."""


class SystemBaseLoader:
    """Loads and validates the canonical system base artifact."""

    def __init__(self, contracts_root: Path) -> None:
        self._contracts_root = contracts_root

    def resolve_path(self) -> Path:
        """Return the resolved path to the system base artifact."""
        return self._contracts_root / "system-base.md"

    def load(self) -> SystemBase:
        """Load, parse, and validate the system base artifact.

        Returns:
            A validated ``SystemBase`` instance.

        Raises:
            SystemBaseLoadError: If the file is missing, unparseable, or
                missing required sections.
        """
        path = self.resolve_path()
        if not path.exists():
            raise SystemBaseLoadError(f"System base artifact not found: {path}")

        raw = path.read_text(encoding="utf-8")
        sections = self._parse_sections(raw)
        frontmatter = self._parse_frontmatter(raw)
        version = frontmatter.get("version", "0.0.0")

        missing = [s for s in _REQUIRED_SECTIONS if s not in sections]
        if missing:
            raise SystemBaseLoadError(
                f"System base artifact missing required section(s): {', '.join(missing)}. "
                f"See {_SECTION_HEADER_MAP.get(missing[0], missing[0])} in {path.name}"
            )

        tool_policy_section = sections.get("tool_usage_policy", "")
        return SystemBase(
            version=str(version),
            global_rules=self._as_lines(tool_policy_section),
            tool_usage_policy=self._as_policy_lines(tool_policy_section),
            safety_limits=self._parse_safety_limits(sections["safety_limits"]),
            error_handling=self._as_lines(sections["error_handling"]),
            output_style=self._as_lines(sections["output_style"]),
            model_behavior=self._parse_model_behavior(sections["model_behavior"]),
            embedding_config=self._parse_embedding_config(sections["embedding_config"]),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(raw: str) -> dict[str, Any]:
        """Parse YAML frontmatter delimited by ``---``."""
        stripped = raw.strip()
        if not stripped.startswith("---"):
            return {}
        end = stripped.find("---", 3)
        if end == -1:
            return {}
        try:
            result = yaml.safe_load(stripped[3:end])
            return result if isinstance(result, dict) else {}
        except yaml.YAMLError:
            return {}

    @staticmethod
    def _parse_sections(raw: str) -> dict[str, str]:
        """Split markdown into top-level sections by ``##`` headings."""
        sections: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in raw.splitlines():
            if line.startswith("## ") and not line.startswith("###"):
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines).strip()
                slug = _heading_to_slug(line)
                current_key = slug
                current_lines = []
            elif current_key is not None:
                current_lines.append(line)

        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

        return sections

    @staticmethod
    def _as_lines(text: str) -> tuple[str, ...]:
        """Split text into non-empty lines, stripped."""
        return tuple(line.strip() for line in text.splitlines() if line.strip())

    @staticmethod
    def _as_policy_lines(text: str) -> dict[str, str]:
        """Parse enumerated rules into ``{key: value}`` dict."""
        policy: dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                raw_key = SystemBaseLoader._clean_key(key) or key.strip()
                policy[raw_key] = value.strip()
        return policy

    @staticmethod
    def _clean_key(key: str) -> str:
        """Strip markdown list markers and bold formatting from a key."""
        cleaned = key.strip()
        # Remove leading list markers: "- ", "* ", "1. ", "1) ", etc.
        import re

        cleaned = re.sub(r"^[\s*+\d.()\-]+\s*", "", cleaned)
        # Remove bold markers
        cleaned = cleaned.replace("**", "").replace("__", "")
        return cleaned.strip()

    @staticmethod
    def _parse_safety_limits(text: str) -> dict[str, int | float | str]:
        """Parse safety limit lines into a dict."""
        limits: dict[str, int | float | str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            raw_key = SystemBaseLoader._clean_key(key)
            raw_value = value.strip()
            try:
                if "." in raw_value:
                    limits[raw_key] = float(raw_value)
                else:
                    limits[raw_key] = int(raw_value)
            except ValueError:
                limits[raw_key] = raw_value
        return limits

    @staticmethod
    def _parse_model_behavior(text: str) -> dict[str, str | int | float | None]:
        """Parse model behavior lines from markdown list items."""
        behavior: dict[str, str | int | float | None] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            raw_key = SystemBaseLoader._clean_key(key)
            raw_value = value.strip().strip("`")
            if raw_value.lower() in ("none", "ninguno"):
                behavior[raw_key] = None
            elif raw_value.replace(".", "", 1).isdigit():
                behavior[raw_key] = float(raw_value) if "." in raw_value else int(raw_value)
            else:
                behavior[raw_key] = raw_value
        return behavior

    @staticmethod
    def _parse_embedding_config(text: str) -> dict[str, str | int | float]:
        """Parse embedding configuration lines."""
        config: dict[str, str | int | float] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            raw_key = SystemBaseLoader._clean_key(key)
            raw_value = value.strip().strip("`")
            parts = raw_value.split()
            raw_value = parts[0] if parts else raw_value
            try:
                if "." in raw_value:
                    config[raw_key] = float(raw_value)
                else:
                    config[raw_key] = int(raw_value)
            except ValueError:
                config[raw_key] = raw_value
        return config


def _heading_to_slug(heading: str) -> str:
    """Convert a ``## Section Title`` heading to a canonical slug key.

    Strips leading numbers (``1)``, ``2.``, etc.) and parenthetical text,
    then normalizes to snake_case.

    Canonical mappings (case-insensitive, spaces/hyphens flexible):
        - global rules / tool usage → ``tool_usage_policy``
        - safety limits → ``safety_limits``
        - error handling → ``error_handling``
        - output style → ``output_style``
        - model behavior → ``model_behavior``
        - embedding configuration → ``embedding_config``
    """
    import re

    text = heading.lstrip("#").strip().lower()
    # Strip leading number+punctuation (e.g. "1)", "2.", "3 - ")
    text = re.sub(r"^\d+[\s\).-]+\s*", "", text)
    # Remove parenthetical text
    text = re.sub(r"\(.*?\)", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    canonic: dict[str, str] = {
        "global rules": "tool_usage_policy",
        "tool usage": "tool_usage_policy",
        "safety limits": "safety_limits",
        "error handling": "error_handling",
        "output style": "output_style",
        "model behavior": "model_behavior",
        "embedding configuration": "embedding_config",
    }

    for prefix, mapped in canonic.items():
        if text.startswith(prefix):
            return mapped

    # Fallback: normalize as-is
    return text.replace(" ", "_").replace("-", "_")
