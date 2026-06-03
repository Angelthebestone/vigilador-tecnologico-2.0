# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Complexity routing for the app-development playbook."""

from __future__ import annotations

from typing import Literal

from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    AppDevError,
    RoutingRedirectError,
)

Complexity = Literal["SIMPLE", "MODERADA", "COMPLEJA"]

PHASES_MODERADA: tuple[str, ...] = (
    "constitution", "specify", "plan", "tasks", "implement"
)
PHASES_COMPLEJA: tuple[str, ...] = (
    "constitution", "specify", "plan", "tasks", "analyze", "implement", "test"
)


def resolve_phases(complexity: str) -> tuple[str, ...]:
    """Return active phases for the given complexity level.

    Raises RoutingRedirectError for SIMPLE (redirects to general).
    Raises AppDevError for invalid complexity values.
    """
    upper = complexity.upper()
    if upper == "SIMPLE":
        raise RoutingRedirectError("general")
    if upper == "MODERADA":
        return PHASES_MODERADA
    if upper == "COMPLEJA":
        return PHASES_COMPLEJA
    raise AppDevError("routing", f"invalid complexity classification: '{complexity}'")
