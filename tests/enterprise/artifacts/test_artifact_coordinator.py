"""Tests for ArtifactCoordinator (T015 — FR-001, FR-010, SC-004, SC-005)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from vigilancia_multiagente.enterprise.artifacts.artifact_coordinator import ArtifactCoordinator
from vigilancia_multiagente.enterprise.artifacts.artifact_registry import (
    ArtifactRegistry,
    JsonlRegistryStore,
)
from vigilancia_multiagente.enterprise.artifacts.builder_agent import BuilderAgent
from vigilancia_multiagente.enterprise.artifacts.metric_model_agent import MetricModelAgent
from vigilancia_multiagente.enterprise.artifacts.pipeline_planner import PipelinePlanner
from vigilancia_multiagente.enterprise.artifacts.ports import BuildResult, DataSource, VerificationResult
from vigilancia_multiagente.enterprise.artifacts.publisher import Publisher
from vigilancia_multiagente.enterprise.artifacts.source_inventory_agent import SourceInventoryAgent
from vigilancia_multiagente.enterprise.artifacts.verifier import Verifier


class FakeSourceIndex:
    def __init__(self, sources: list[DataSource]) -> None:
        self._sources = sources

    def search_sources(self, query: str) -> list[DataSource]:
        return self._sources


class FakeFileSystem:
    def __init__(self) -> None:
        self.copied: list[tuple[str, str]] = []

    def file_exists(self, path: str) -> bool:
        return True

    def copy_file(self, src: str, dest: str) -> None:
        self.copied.append((src, dest))

    def list_files(self, directory: str) -> list[str]:
        return []


class FakeSandbox:
    def execute(self, code: str, artifact_type: str) -> BuildResult:
        return BuildResult(
            success=True,
            artifact_type=artifact_type,
            artifact_path=f"/sandbox/{artifact_type}/output.html",
        )


def _build_coordinator(tmp_path: Path) -> ArtifactCoordinator:
    sources = [
        DataSource(name="ventas.csv", source_type="CSV", location="/data/ventas.csv", available=True),
        DataSource(name="clientes.csv", source_type="CSV", location="/data/clientes.csv", available=True),
    ]
    fs = FakeFileSystem()
    sandbox = FakeSandbox()
    store = JsonlRegistryStore(tmp_path / "artifacts.jsonl")
    registry = ArtifactRegistry(store)

    return ArtifactCoordinator(
        inventory_agent=SourceInventoryAgent(FakeSourceIndex(sources), fs),
        metric_agent=MetricModelAgent(),
        planner=PipelinePlanner(),
        builder=BuilderAgent(sandbox),
        verifier=Verifier(sandbox),
        publisher=Publisher(fs, registry),
    )


def test_full_6_phase_flow_produces_artifact() -> None:
    """Flujo completo de 6 fases con 2 fuentes y 3 KPIs produce artefacto funcional."""
    with TemporaryDirectory() as tmp:
        coordinator = _build_coordinator(Path(tmp))
        kpis = [
            {"name": "Ventas Totales", "formula": "SUM(monto)", "source": "ventas.csv", "granularity": "mensual", "display_format": "bar_chart"},
            {"name": "Clientes Nuevos", "formula": "COUNT(id)", "source": "clientes.csv", "granularity": "semanal", "display_format": "line_chart"},
            {"name": "Ticket Promedio", "formula": "AVG(monto)", "source": "ventas.csv", "granularity": "mensual", "display_format": "gauge"},
        ]

        result = coordinator.execute(
            request="dashboard de ventas mensuales con KPIs",
            artifact_type="dashboard_html",
            destination="/output",
            requested_kpis=kpis,
        )

        assert result.success is True
        assert result.record is not None
        assert result.record.artifact_type == "dashboard_html"


def test_metadata_complete_in_registry() -> None:
    """Metadatos completos registrados (SC-004)."""
    with TemporaryDirectory() as tmp:
        coordinator = _build_coordinator(Path(tmp))
        kpis = [
            {"name": "Revenue", "formula": "SUM(revenue)", "source": "ventas.csv", "granularity": "mensual", "display_format": "bar_chart"},
        ]

        result = coordinator.execute(
            request="dashboard de revenue mensual",
            artifact_type="dashboard_html",
            destination="/output",
            requested_kpis=kpis,
        )

        assert result.record is not None
        record = result.record
        assert record.artifact_type == "dashboard_html"
        assert record.artifact_path
        assert len(record.data_sources) > 0
        assert record.refresh_policy
        assert len(record.metrics) > 0
        assert record.created_at


def test_dashboard_request_goes_to_artifact_development() -> None:
    """Solicitud de 'dashboard de ventas' va a artifact-development (FR-010, SC-005)."""
    assert ArtifactCoordinator.should_handle("Crea un dashboard de ventas mensuales") is True
    assert ArtifactCoordinator.should_handle("Necesito una gráfica de KPIs financieros") is True
    assert ArtifactCoordinator.should_handle("Quiero un reporte con métricas de marketing") is True


def test_app_request_does_not_activate_artifact_playbook() -> None:
    """Solicitud de 'herramienta interna' NO activa este playbook (SC-001, SC-005)."""
    assert ArtifactCoordinator.should_handle("Construye una herramienta interna para el equipo") is False
    assert ArtifactCoordinator.should_handle("Necesito una aplicación con CRUD de usuarios") is False
    assert ArtifactCoordinator.should_handle("Crea un sistema completo de gestión") is False
