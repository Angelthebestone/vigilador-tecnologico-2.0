"""Publisher — copies verified artifact to destination and registers it (FR-009)."""

from __future__ import annotations

from datetime import UTC, datetime

from vigilancia_multiagente.enterprise.artifacts.artifact_registry import ArtifactRegistry
from vigilancia_multiagente.enterprise.artifacts.ports import (
    ArtifactRecord,
    BuildResult,
    FileSystemPort,
    KPIDefinition,
    VerificationResult,
)


class PublishError(Exception):
    """Raised when publication fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Publicación falló: {reason}")


class Publisher:
    """Publishes verified artifacts to destination directory and registers metadata."""

    def __init__(
        self,
        file_system: FileSystemPort,
        registry: ArtifactRegistry,
    ) -> None:
        self._fs = file_system
        self._registry = registry

    def publish(
        self,
        build_result: BuildResult,
        verification: VerificationResult,
        destination: str,
        data_sources: tuple[str, ...],
        kpis: tuple[KPIDefinition, ...],
        refresh_policy: str,
    ) -> ArtifactRecord:
        """Publish a verified artifact to the destination.

        Args:
            build_result: Successful build result.
            verification: Must be passed=True.
            destination: Target directory path.
            data_sources: Names of data sources used.
            kpis: KPI definitions included.
            refresh_policy: Declared refresh policy.

        Returns:
            The registered ArtifactRecord.

        Raises:
            PublishError: If verification failed or copy fails.
        """
        if not verification.passed:
            raise PublishError(
                f"No se puede publicar sin verificación exitosa: {verification.details}"
            )

        dest_path = f"{destination}/{build_result.artifact_path.rsplit('/', 1)[-1]}"
        self._fs.copy_file(build_result.artifact_path, dest_path)

        record = ArtifactRecord(
            artifact_type=build_result.artifact_type,
            artifact_path=dest_path,
            data_sources=data_sources,
            refresh_policy=refresh_policy,
            metrics=tuple(k.name for k in kpis),
            created_at=datetime.now(UTC).isoformat(),
        )

        self._registry.register(record)
        return record
