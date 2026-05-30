"""ArtifactRegistry — registers published artifacts with metadata (FR-006, SC-004)."""

from __future__ import annotations

import json
from pathlib import Path

from vigilancia_multiagente.enterprise.artifacts.ports import ArtifactRecord, RegistryStore


class JsonlRegistryStore:
    """Persists artifact records in JSONL format (default storage)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, record: ArtifactRecord) -> None:
        """Append a record to the JSONL file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            "artifact_type": record.artifact_type,
            "artifact_path": record.artifact_path,
            "data_sources": list(record.data_sources),
            "refresh_policy": record.refresh_policy,
            "metrics": list(record.metrics),
            "created_at": record.created_at,
        })
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def list_all(self) -> list[ArtifactRecord]:
        """Read all records from the JSONL file."""
        if not self._path.exists():
            return []
        records: list[ArtifactRecord] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            records.append(ArtifactRecord(
                artifact_type=data["artifact_type"],
                artifact_path=data["artifact_path"],
                data_sources=tuple(data["data_sources"]),
                refresh_policy=data["refresh_policy"],
                metrics=tuple(data["metrics"]),
                created_at=data["created_at"],
            ))
        return records


class ArtifactRegistry:
    """Registers each published artifact with complete metadata."""

    def __init__(self, store: RegistryStore) -> None:
        self._store = store

    def register(self, record: ArtifactRecord) -> None:
        """Register an artifact record.

        Raises:
            ValueError: If any required metadata field is empty.
        """
        self._validate(record)
        self._store.save(record)

    def list_artifacts(self) -> list[ArtifactRecord]:
        """Query all registered artifacts."""
        return self._store.list_all()

    def _validate(self, record: ArtifactRecord) -> None:
        if not record.artifact_type:
            raise ValueError("artifact_type es requerido para registrar un artefacto.")
        if not record.artifact_path:
            raise ValueError("artifact_path es requerido para registrar un artefacto.")
        if not record.data_sources:
            raise ValueError("data_sources es requerido para registrar un artefacto.")
        if not record.refresh_policy:
            raise ValueError("refresh_policy es requerido para registrar un artefacto.")
        if not record.metrics:
            raise ValueError("metrics es requerido para registrar un artefacto.")
        if not record.created_at:
            raise ValueError("created_at es requerido para registrar un artefacto.")
