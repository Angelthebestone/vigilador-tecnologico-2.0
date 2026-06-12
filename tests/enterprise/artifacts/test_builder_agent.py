"""Tests for BuilderAgent (T009 — FR-004, FR-005, FR-009, EC-03, EC-04)."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.artifacts.builder_agent import (
    BuilderAgent,
    BuildFailedError,
    UnsupportedArtifactTypeError,
)
from vigilancia_multiagente.enterprise.artifacts.ports import (
    BuildResult,
    KPIDefinition,
    PipelinePlan,
)


class FakeSandbox:
    """Fake SandboxPort for testing."""

    def __init__(self, results: list[BuildResult] | None = None) -> None:
        self._results = results or []
        self._call_count = 0

    def execute(self, code: str, artifact_type: str) -> BuildResult:
        if self._call_count < len(self._results):
            result = self._results[self._call_count]
            self._call_count += 1
            return result
        return BuildResult(
            success=True,
            artifact_type=artifact_type,
            artifact_path=f"/sandbox/{artifact_type}/output",
        )


def _kpis() -> tuple[KPIDefinition, ...]:
    return (
        KPIDefinition(
            name="Ventas",
            formula="SUM(monto)",
            source="ventas.csv",
            granularity="mensual",
            display_format="bar_chart",
        ),
    )


def _plan() -> PipelinePlan:
    return PipelinePlan(
        steps=("extract:ventas.csv:CSV", "transform:Ventas", "load:visualization"),
        transformations=("compute:Ventas:SUM(monto)",),
        refresh_policy="diario",
    )


def test_dashboard_built_in_sandbox() -> None:
    """Dashboard construido en sandbox correctamente."""
    sandbox = FakeSandbox()
    agent = BuilderAgent(sandbox)

    result = agent.build("dashboard_html", _kpis(), _plan())

    assert result.success is True
    assert result.artifact_type == "dashboard_html"
    assert result.artifact_path


def test_pipeline_generated() -> None:
    """Pipeline generado correctamente."""
    sandbox = FakeSandbox()
    agent = BuilderAgent(sandbox)

    result = agent.build("pipeline_local", _kpis(), _plan())

    assert result.success is True
    assert result.artifact_type == "pipeline_local"


def test_unsupported_type_informs_available() -> None:
    """Tipo no soportado informa tipos disponibles (EC-04)."""
    sandbox = FakeSandbox()
    agent = BuilderAgent(sandbox)

    with pytest.raises(UnsupportedArtifactTypeError) as exc_info:
        agent.build("powerpoint", _kpis(), _plan())

    assert "powerpoint" in str(exc_info.value)
    assert "dashboard_html" in str(exc_info.value)


def test_build_error_retries_max_2() -> None:
    """Error de construcción reintenta max 2 veces (EC-03)."""
    failures = [
        BuildResult(
            success=False, artifact_type="dashboard_html", artifact_path="", error="dep missing"
        ),
        BuildResult(
            success=False, artifact_type="dashboard_html", artifact_path="", error="dep missing v2"
        ),
    ]
    sandbox = FakeSandbox(results=failures)
    agent = BuilderAgent(sandbox)

    with pytest.raises(BuildFailedError) as exc_info:
        agent.build("dashboard_html", _kpis(), _plan())

    assert exc_info.value.attempts == 2
    assert "dep missing" in str(exc_info.value)
