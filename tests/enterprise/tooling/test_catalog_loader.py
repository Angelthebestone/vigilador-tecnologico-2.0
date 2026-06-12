"""Tests unitarios DB-free para CatalogLoader (T006)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vigilancia_multiagente.enterprise.tooling.catalog_loader import (
    CatalogEntry,
    CatalogLoader,
    CatalogValidationError,
)


@pytest.fixture()
def catalog_path(tmp_path: Path) -> Path:
    return tmp_path / "catalog.yaml"


def _write_catalog(path: Path, tools: list[dict]) -> None:
    path.write_text(yaml.dump({"tools": tools}, default_flow_style=False), encoding="utf-8")


def _minimal_entry(**overrides) -> dict:
    base = {
        "id": "test_tool",
        "domain": "research",
        "source": "nuevo",
        "strategy": "NUEVO",
        "runtime": "python_internal",
        "status": "active",
        "owner": "team",
        "license": "MIT",
        "capabilities": ["search"],
        "requires_key": False,
        "env_var": "",
        "healthcheck": "internal",
        "update_policy": "manual",
        "loc_count": 100,
        "loc_validated": True,
        "language": "python",
        "mvp": True,
    }
    base.update(overrides)
    return base


class TestCatalogLoaderLoad:
    def test_loads_valid_catalog(self, catalog_path: Path) -> None:
        tools = [_minimal_entry(id=f"tool_{i}") for i in range(5)]
        _write_catalog(catalog_path, tools)

        loader = CatalogLoader()
        entries = loader.load(catalog_path)

        assert len(entries) == 5
        assert all(isinstance(e, CatalogEntry) for e in entries)

    def test_fails_on_missing_required_field(self, catalog_path: Path) -> None:
        entry = _minimal_entry()
        del entry["domain"]
        _write_catalog(catalog_path, [entry])

        loader = CatalogLoader()
        with pytest.raises(CatalogValidationError) as exc_info:
            loader.load(catalog_path)
        assert "missing required field 'domain'" in str(exc_info.value)

    def test_fails_on_invalid_strategy(self, catalog_path: Path) -> None:
        entry = _minimal_entry(strategy="INVALID")
        _write_catalog(catalog_path, [entry])

        loader = CatalogLoader()
        with pytest.raises(CatalogValidationError) as exc_info:
            loader.load(catalog_path)
        assert "invalid strategy" in str(exc_info.value)

    def test_mvp_only_filter(self, catalog_path: Path) -> None:
        tools = [
            _minimal_entry(id="mvp_tool", mvp=True),
            _minimal_entry(id="roadmap_tool", mvp=False),
        ]
        _write_catalog(catalog_path, tools)

        loader = CatalogLoader()
        mvp_entries = loader.load_mvp_only(catalog_path)

        assert len(mvp_entries) == 1
        assert mvp_entries[0].id == "mvp_tool"

    def test_loc_validated_false_logs_warning(
        self, catalog_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        entry = _minimal_entry(loc_validated=False)
        _write_catalog(catalog_path, [entry])

        loader = CatalogLoader()
        import logging

        with caplog.at_level(logging.WARNING):
            entries = loader.load(catalog_path)

        assert len(entries) == 1
        assert "loc_validated=false" in caplog.text
