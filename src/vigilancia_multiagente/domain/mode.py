"""Domain model: Mode — enterprise persona with context filters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    """Immutable representation of an operational mode."""

    id: str
    name: str
    soul_overlay_path: str
    company_subset_paths: tuple[str, ...]
    skills_allowlist: frozenset[str]
    playbooks_allowed: frozenset[str]
    tools_allowlist: frozenset[str]
