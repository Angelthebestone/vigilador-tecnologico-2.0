"""Tests for geo_context.py (spec 011 Phase 7)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.modes.geo_context import build_geo_context
from vigilancia_multiagente.enterprise.modes.mode_schema import CompanyGeo


class TestBuildGeoContext:
    def test_full_three_levels(self) -> None:
        geo = CompanyGeo(
            country="Colombia",
            department="Santander",
            municipality="Barrancabermeja",
            timezone="America/Bogota",
        )
        result = build_geo_context(geo)
        assert "Colombia" in result
        assert "Santander" in result
        assert "Barrancabermeja" in result
        assert "America/Bogota" in result

    def test_country_only_national_level(self) -> None:
        geo = CompanyGeo(country="Colombia")
        result = build_geo_context(geo)
        assert "Colombia" in result
        assert "Departamento" not in result
        assert "Municipio" not in result

    def test_no_department_no_municipality_no_assumption(self) -> None:
        geo = CompanyGeo(country="Ecuador")
        result = build_geo_context(geo)
        assert "Ecuador" in result
        assert "Departamento" not in result
        assert "Municipio" not in result

    def test_context_is_verifiable_string(self) -> None:
        geo = CompanyGeo(
            country="Colombia",
            department="Antioquia",
            municipality="Medellín",
        )
        result = build_geo_context(geo)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Contexto geográfico" in result
