"""Domain model: ModeContext — frozen snapshot for a session."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModeContext:
    """Immutable session snapshot: filtered context produced by a Mode.

    Spec 021 FR-019 — captured at session start, never mutated mid-session.
    A ``/mode <other>`` switch rebuilds a new ``ModeContext`` instead of
    mutating the existing one (preserves the prefix-cache invariant).
    """

    soul_overlay: str
    company_context: dict[str, object]
    skills_allowed: frozenset[str]
    playbooks_allowed: frozenset[str]
    tools_allowed: frozenset[str]
    # Spec 021 — geographic context propagated to playbooks/skills.
    company_geo: dict[str, str] = field(default_factory=dict)
