# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""ArtifactCoordinator — orchestrates 6 sequential phases (FR-001)."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.artifacts.builder_agent import BuilderAgent
from vigilancia_multiagente.enterprise.artifacts.metric_model_agent import MetricModelAgent
from vigilancia_multiagente.enterprise.artifacts.pipeline_planner import PipelinePlanner
from vigilancia_multiagente.enterprise.artifacts.ports import ArtifactRecord
from vigilancia_multiagente.enterprise.artifacts.publisher import Publisher
from vigilancia_multiagente.enterprise.artifacts.source_inventory_agent import (
    SourceInventoryAgent,
)
from vigilancia_multiagente.enterprise.artifacts.verifier import Verifier

# Keywords that indicate artifact-development vs app-development
_ARTIFACT_KEYWORDS = frozenset(
    {
        "dashboard",
        "kpi",
        "métrica",
        "metrica",
        "grafica",
        "gráfica",
        "reporte",
        "pipeline de datos",
        "notebook",
        "visualización",
        "visualizacion",
        "indicador",
        "ventas mensuales",
        "chart",
    }
)

_APP_KEYWORDS = frozenset(
    {
        "herramienta interna",
        "aplicación",
        "aplicacion",
        "producto interno",
        "sistema completo",
        "workflow",
        "crud",
        "interfaz de usuario",
    }
)


@dataclass(frozen=True)
class CoordinatorResult:
    """Final result of the artifact development flow."""

    success: bool
    record: ArtifactRecord | None
    message: str


class ArtifactCoordinator:
    """Orchestrates the 6-phase artifact development flow sequentially.

    Phases: source_inventory -> metric_model -> pipeline_plan -> build -> verify -> publish
    """

    def __init__(
        self,
        inventory_agent: SourceInventoryAgent,
        metric_agent: MetricModelAgent,
        planner: PipelinePlanner,
        builder: BuilderAgent,
        verifier: Verifier,
        publisher: Publisher,
    ) -> None:
        self._inventory = inventory_agent
        self._metric = metric_agent
        self._planner = planner
        self._builder = builder
        self._verifier = verifier
        self._publisher = publisher

    def execute(
        self,
        request: str,
        artifact_type: str,
        destination: str,
        declared_paths: list[str] | None = None,
        requested_kpis: list[dict[str, str]] | None = None,
    ) -> CoordinatorResult:
        """Execute the full 6-phase artifact development flow.

        Args:
            request: User's natural language request.
            artifact_type: Type of artifact to build.
            destination: Target directory for publication.
            declared_paths: Optional file paths declared by user.
            requested_kpis: Optional explicit KPI definitions.

        Returns:
            CoordinatorResult with success status and artifact record.
        """
        # Phase 1: Source Inventory
        inventory = self._inventory.run_inventory(request, declared_paths)
        if not inventory.sources:
            return CoordinatorResult(success=False, record=None, message=inventory.message)

        # Phase 2: Metric Model
        model = self._metric.model_metrics(request, inventory.sources, requested_kpis)
        if not model.kpis:
            return CoordinatorResult(success=False, record=None, message=model.message)

        # Phase 3: Pipeline Plan
        plan = self._planner.plan(inventory.sources, model.kpis, model.refresh_policy)

        # Phase 4: Build
        build_result = self._builder.build(artifact_type, model.kpis, plan)

        # Phase 5: Verify
        verification = self._verifier.verify(build_result)
        if not verification.passed:
            return CoordinatorResult(
                success=False,
                record=None,
                message=f"Verificación falló: {verification.details}",
            )

        # Phase 6: Publish
        data_source_names = tuple(s.name for s in inventory.sources if s.available)
        record = self._publisher.publish(
            build_result=build_result,
            verification=verification,
            destination=destination,
            data_sources=data_source_names,
            kpis=model.kpis,
            refresh_policy=model.refresh_policy,
        )

        return CoordinatorResult(
            success=True,
            record=record,
            message=f"Artefacto '{artifact_type}' generado y publicado exitosamente.",
        )

    @staticmethod
    def should_handle(request: str) -> bool:
        """Determine if this request should be handled by artifact-development.

        Returns True for metric/visualization requests, False for full app requests.
        """
        lower = request.lower()
        artifact_score = sum(1 for kw in _ARTIFACT_KEYWORDS if kw in lower)
        app_score = sum(1 for kw in _APP_KEYWORDS if kw in lower)
        return artifact_score > app_score

    @staticmethod
    def phases() -> tuple[str, ...]:
        """Return the ordered phases of this playbook."""
        return (
            "source_inventory",
            "metric_model",
            "pipeline_plan",
            "build",
            "verify",
            "publish",
        )
