"""Tests for SourceInventoryAgent (T004 — FR-002, EC-01, SC-002)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.artifacts.ports import (
    DataSource,
)
from vigilancia_multiagente.enterprise.artifacts.source_inventory_agent import (
    SourceInventoryAgent,
)


class FakeSourceIndex:
    """Fake SourceIndex for testing."""

    def __init__(self, sources: list[DataSource] | None = None) -> None:
        self._sources = sources or []

    def search_sources(self, query: str) -> list[DataSource]:
        return self._sources


class FakeFileSystem:
    """Fake FileSystemPort for testing."""

    def __init__(self, existing_files: set[str] | None = None) -> None:
        self._existing = existing_files or set()

    def file_exists(self, path: str) -> bool:
        return path in self._existing

    def copy_file(self, src: str, dest: str) -> None:
        pass

    def list_files(self, directory: str) -> list[str]:
        return [f for f in self._existing if f.startswith(directory)]


def _make_agent(
    indexed: list[DataSource] | None = None,
    existing_files: set[str] | None = None,
) -> SourceInventoryAgent:
    return SourceInventoryAgent(
        source_index=FakeSourceIndex(indexed),
        file_system=FakeFileSystem(existing_files),
    )


def test_inventory_with_three_available_sources() -> None:
    """Inventario con 3 fuentes disponibles retorna nombre/tipo/ubicacion/disponibilidad."""
    indexed = [
        DataSource(
            name="ventas.csv", source_type="CSV", location="/data/ventas.csv", available=True
        ),
        DataSource(
            name="api_crm", source_type="API", location="https://crm.api/v1", available=True
        ),
        DataSource(
            name="db_clientes", source_type="DB", location="postgres://db/clientes", available=True
        ),
    ]
    agent = _make_agent(indexed=indexed)
    result = agent.run_inventory("dashboard de ventas")

    assert len(result.sources) == 3
    for s in result.sources:
        assert s.name
        assert s.source_type
        assert s.location
        assert s.available is True
    assert "3 fuente(s) disponible(s)" in result.message


def test_unavailable_source_marked_with_suggestion() -> None:
    """Fuente eliminada marcada como no disponible con sugerencia de alternativas (EC-01)."""
    indexed = [
        DataSource(
            name="backup.csv", source_type="CSV", location="/data/backup.csv", available=True
        ),
    ]
    agent = _make_agent(indexed=indexed, existing_files=set())
    result = agent.run_inventory("ventas", declared_paths=["/data/deleted.csv"])

    unavailable = [s for s in result.sources if not s.available]
    assert len(unavailable) == 1
    assert unavailable[0].name == "deleted.csv"
    assert "Alternativa sugerida" in unavailable[0].suggestion


def test_zero_sources_reports_suggestion() -> None:
    """Cero fuentes encontradas reporta al usuario sugiriendo indexar datos."""
    agent = _make_agent(indexed=[], existing_files=set())
    result = agent.run_inventory("dashboard de ventas")

    assert len(result.sources) == 0
    assert "indexe datos" in result.message.lower() or "indexe" in result.message.lower()


def test_indexed_sources_discovered_correctly() -> None:
    """Fuentes del índice empresarial descubiertas correctamente (FR-002, SC-002)."""
    indexed = [
        DataSource(
            name="doc_financiero",
            source_type="documento_indexado",
            location="idx://fin/001",
            available=True,
        ),
        DataSource(
            name="reporte_q1",
            source_type="documento_indexado",
            location="idx://rep/q1",
            available=True,
        ),
    ]
    agent = _make_agent(indexed=indexed)
    result = agent.run_inventory("métricas financieras")

    assert len(result.sources) == 2
    assert all(s.source_type == "documento_indexado" for s in result.sources)
    assert all(s.available for s in result.sources)
