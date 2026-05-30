"""SourceInventoryAgent — inventories available data sources (FR-002, EC-01)."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.artifacts.ports import (
    DataSource,
    FileSystemPort,
    SourceIndex,
)


@dataclass(frozen=True)
class InventoryResult:
    """Result of source inventory phase."""

    sources: tuple[DataSource, ...]
    message: str


class SourceInventoryAgent:
    """Discovers and verifies available data sources for artifact generation."""

    def __init__(self, source_index: SourceIndex, file_system: FileSystemPort) -> None:
        self._index = source_index
        self._fs = file_system

    def run_inventory(self, query: str, declared_paths: list[str] | None = None) -> InventoryResult:
        """Inventory all accessible data sources for the given query.

        Args:
            query: User request describing what data they need.
            declared_paths: Optional list of file paths declared by the user.

        Returns:
            InventoryResult with discovered sources and status message.
        """
        sources: list[DataSource] = []

        # Discover from enterprise index
        indexed = self._index.search_sources(query)
        sources.extend(indexed)

        # Verify declared local files
        if declared_paths:
            for path in declared_paths:
                available = self._fs.file_exists(path)
                source_type = self._infer_type(path)
                suggestion = "" if available else self._suggest_alternative(path, sources)
                sources.append(
                    DataSource(
                        name=path.rsplit("/", 1)[-1] if "/" in path else path,
                        source_type=source_type,
                        location=path,
                        available=available,
                        suggestion=suggestion,
                    )
                )

        if not sources:
            return InventoryResult(
                sources=(),
                message=(
                    "No se encontraron fuentes de datos. "
                    "Sugerencia: indexe datos o conecte fuentes antes de continuar."
                ),
            )

        unavailable = [s for s in sources if not s.available]
        if unavailable:
            names = ", ".join(s.name for s in unavailable)
            msg = f"Inventario completado. Fuentes no disponibles: {names}. Revise sugerencias."
        else:
            msg = f"Inventario completado: {len(sources)} fuente(s) disponible(s)."

        return InventoryResult(sources=tuple(sources), message=msg)

    def _infer_type(self, path: str) -> str:
        lower = path.lower()
        if lower.endswith(".csv"):
            return "CSV"
        if lower.endswith(".json"):
            return "API"
        if lower.endswith((".db", ".sqlite")):
            return "DB"
        return "documento_indexado"

    def _suggest_alternative(self, missing_path: str, existing: list[DataSource]) -> str:
        available_sources = [s for s in existing if s.available]
        if available_sources:
            return f"Alternativa sugerida: {available_sources[0].name}"
        return "No hay alternativas disponibles. Indexe nuevos datos."
