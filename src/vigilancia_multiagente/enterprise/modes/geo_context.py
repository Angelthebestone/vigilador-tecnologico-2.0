"""Geo context builder: generates injectable geographic context (spec 011, FR-019)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.modes.mode_schema import CompanyGeo


def build_geo_context(company_geo: CompanyGeo) -> str:
    """Build a geographic context string from CompanyGeo.

    Injects ALWAYS (KISS), with specificity order: municipality > department > country.
    FR-019: no heuristic detection of whether the query involves regulation.
    FR-020: if no department/municipality, limits to national level.
    """
    parts: list[str] = []

    parts.append(f"País: {company_geo.country}")

    if company_geo.department:
        parts.append(f"Departamento/Región: {company_geo.department}")

    if company_geo.municipality:
        parts.append(f"Municipio/Ciudad: {company_geo.municipality}")

    if company_geo.timezone:
        parts.append(f"Zona horaria: {company_geo.timezone}")

    header = "Contexto geográfico empresarial"
    return f"[{header}] {' | '.join(parts)}"
