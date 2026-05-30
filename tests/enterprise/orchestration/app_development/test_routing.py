"""Tests for complexity routing (T014)."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.orchestration.app_development.complexity_router import (
    PHASES_COMPLEJA,
    PHASES_MODERADA,
    resolve_phases,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    AppDevError,
    RoutingRedirectError,
)


def test_simple_redirects_to_general() -> None:
    with pytest.raises(RoutingRedirectError) as exc_info:
        resolve_phases("SIMPLE")
    assert exc_info.value.target_playbook == "general"


def test_moderada_activates_5_phases() -> None:
    phases = resolve_phases("MODERADA")
    assert phases == PHASES_MODERADA
    assert len(phases) == 5
    assert "analyze" not in phases
    assert "test" not in phases


def test_compleja_activates_7_phases() -> None:
    phases = resolve_phases("COMPLEJA")
    assert phases == PHASES_COMPLEJA
    assert len(phases) == 7


def test_invalid_classification_returns_error() -> None:
    with pytest.raises(AppDevError) as exc_info:
        resolve_phases("INVALID")
    assert "invalid complexity classification" in str(exc_info.value)
