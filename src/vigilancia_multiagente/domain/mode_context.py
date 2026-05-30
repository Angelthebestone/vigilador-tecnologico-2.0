"""Domain model: ModeContext — frozen snapshot for a session."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModeContext:
    """Immutable session snapshot: filtered context produced by a Mode."""

    soul_overlay: str
    company_context: dict[str, object]
    skills_allowed: frozenset[str]
    playbooks_allowed: frozenset[str]
    tools_allowed: frozenset[str]
