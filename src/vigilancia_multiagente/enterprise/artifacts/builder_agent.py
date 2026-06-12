# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""BuilderAgent — constructs artifacts in sandbox (FR-004, FR-005, FR-009)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.artifacts.ports import (
    BuildResult,
    KPIDefinition,
    PipelinePlan,
    SandboxPort,
)

SUPPORTED_TYPES = frozenset(
    {
        "dashboard_html",
        "dashboard_streamlit",
        "dashboard_react",
        "pipeline_local",
        "notebook",
        "reporte",
        "grafica_pdf",
    }
)

MAX_RETRIES = 2


class UnsupportedArtifactTypeError(Exception):
    """Raised when the requested artifact type is not supported."""

    def __init__(self, requested: str) -> None:
        self.requested = requested
        available = ", ".join(sorted(SUPPORTED_TYPES))
        super().__init__(
            f"Tipo de artefacto '{requested}' no soportado. Tipos disponibles: {available}"
        )


class BuildFailedError(Exception):
    """Raised when artifact build fails after all retries."""

    def __init__(self, artifact_type: str, last_error: str, attempts: int) -> None:
        self.artifact_type = artifact_type
        self.last_error = last_error
        self.attempts = attempts
        super().__init__(
            f"Construcción de '{artifact_type}' falló después de {attempts} intento(s): "
            f"{last_error}"
        )


class BuilderAgent:
    """Builds artifacts in sandbox based on pipeline plan and KPIs."""

    def __init__(self, sandbox: SandboxPort) -> None:
        self._sandbox = sandbox

    def build(
        self,
        artifact_type: str,
        kpis: tuple[KPIDefinition, ...],
        plan: PipelinePlan,
    ) -> BuildResult:
        """Build an artifact in sandbox.

        Args:
            artifact_type: Type of artifact to build.
            kpis: KPI definitions to include.
            plan: Pipeline plan with data flow steps.

        Returns:
            BuildResult on success.

        Raises:
            UnsupportedArtifactTypeError: If artifact_type is not in SUPPORTED_TYPES.
            BuildFailedError: If build fails after MAX_RETRIES attempts.
        """
        if artifact_type not in SUPPORTED_TYPES:
            raise UnsupportedArtifactTypeError(artifact_type)

        code = self._generate_build_code(artifact_type, kpis, plan)

        last_error = ""
        for _attempt in range(1, MAX_RETRIES + 1):
            result = self._sandbox.execute(code, artifact_type)
            if result.success:
                return result
            last_error = result.error

        raise BuildFailedError(artifact_type, last_error, MAX_RETRIES)

    def _generate_build_code(
        self,
        artifact_type: str,
        kpis: tuple[KPIDefinition, ...],
        plan: PipelinePlan,
    ) -> str:
        kpi_names = ", ".join(k.name for k in kpis)
        steps = " -> ".join(plan.steps)
        return (
            f"# Build {artifact_type}\n"
            f"# KPIs: {kpi_names}\n"
            f"# Pipeline: {steps}\n"
            f"# Refresh: {plan.refresh_policy}\n"
        )
