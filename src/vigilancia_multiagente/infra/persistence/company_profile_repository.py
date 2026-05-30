"""Repositorio de la tabla `company_profile` (T019).

SQL crudo vía `sqlalchemy.text()`. Single-tenant en MVP: una fila por
`tenant_id` (UNIQUE), upsert sobre ese conflicto.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.infra.db.connection import Database


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    tenant_id: UUID
    name: str
    sector: str | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    timezone: str | None = None


def _row_to_dataclass(row: object) -> CompanyProfile:
    m = row  # RowMapping
    return CompanyProfile(
        tenant_id=m["tenant_id"],  # type: ignore[index]
        name=str(m["name"]),  # type: ignore[index]
        sector=m["sector"],  # type: ignore[index]
        country=m["country"],  # type: ignore[index]
        department=m["department"],  # type: ignore[index]
        municipality=m["municipality"],  # type: ignore[index]
        timezone=m["timezone"],  # type: ignore[index]
    )


class CompanyProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, tenant_id: UUID) -> CompanyProfile | None:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT tenant_id, name, sector, country, department, "
                    "municipality, timezone FROM company_profile "
                    "WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_id},
            )
            row = result.mappings().one_or_none()
            return _row_to_dataclass(row) if row is not None else None

    async def upsert(self, profile: CompanyProfile) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO company_profile "
                    "(tenant_id, name, sector, country, department, municipality, "
                    " timezone, updated_at) "
                    "VALUES (:tenant_id, :name, :sector, :country, :department, "
                    " :municipality, :timezone, NOW()) "
                    "ON CONFLICT (tenant_id) DO UPDATE SET "
                    "  name = EXCLUDED.name, "
                    "  sector = EXCLUDED.sector, "
                    "  country = EXCLUDED.country, "
                    "  department = EXCLUDED.department, "
                    "  municipality = EXCLUDED.municipality, "
                    "  timezone = EXCLUDED.timezone, "
                    "  updated_at = NOW()"
                ),
                {
                    "tenant_id": profile.tenant_id,
                    "name": profile.name,
                    "sector": profile.sector,
                    "country": profile.country,
                    "department": profile.department,
                    "municipality": profile.municipality,
                    "timezone": profile.timezone,
                },
            )
            await db.commit()
