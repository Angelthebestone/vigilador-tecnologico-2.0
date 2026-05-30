"""Ports (abstractions) for the artifacts module — DIP compliance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DataSource:
    """A discovered data source."""

    name: str
    source_type: str  # CSV, API, DB, documento_indexado
    location: str
    available: bool
    suggestion: str = ""


@dataclass(frozen=True)
class KPIDefinition:
    """A modeled KPI/metric."""

    name: str
    formula: str
    source: str
    granularity: str
    display_format: str


@dataclass(frozen=True)
class PipelinePlan:
    """Technical plan for data flow from sources to visualization."""

    steps: tuple[str, ...]
    transformations: tuple[str, ...]
    refresh_policy: str


@dataclass(frozen=True)
class BuildResult:
    """Result of building an artifact in sandbox."""

    success: bool
    artifact_type: str
    artifact_path: str
    error: str = ""


@dataclass(frozen=True)
class VerificationResult:
    """Result of verifying an artifact."""

    passed: bool
    details: str


@dataclass(frozen=True)
class ArtifactRecord:
    """Metadata record for a published artifact."""

    artifact_type: str
    artifact_path: str
    data_sources: tuple[str, ...]
    refresh_policy: str
    metrics: tuple[str, ...]
    created_at: str


class SourceIndex(Protocol):
    """Port for querying indexed enterprise data sources."""

    def search_sources(self, query: str) -> list[DataSource]: ...


class FileSystemPort(Protocol):
    """Port for file system operations."""

    def file_exists(self, path: str) -> bool: ...

    def copy_file(self, src: str, dest: str) -> None: ...

    def list_files(self, directory: str) -> list[str]: ...


class SandboxPort(Protocol):
    """Port for sandbox execution."""

    def execute(self, code: str, artifact_type: str) -> BuildResult: ...


class RegistryStore(Protocol):
    """Port for persisting artifact records."""

    def save(self, record: ArtifactRecord) -> None: ...

    def list_all(self) -> list[ArtifactRecord]: ...
