"""Repositorio de la tabla `tool_health` (T017).

SQL crudo vía `sqlalchemy.text()`, igual que el resto de repositorios del 2.0.

CQS: `upsert` es el ÚNICO escritor y está reservado al `HealthMonitor`.
El `ToolRegistry` solo usa los métodos de lectura (`read_status`, `list_all`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.infra.db.connection import Database


@dataclass(frozen=True, slots=True)
class ToolHealthRow:
    name: str
    tenant_id: UUID
    status: str
    last_check: datetime | None
    fail_count: int
    last_error: str | None
    domain: str | None
    requires_key: bool


def _row_to_dataclass(row: object) -> ToolHealthRow:
    m = row  # RowMapping
    return ToolHealthRow(
        name=str(m["name"]),  # type: ignore[index]
        tenant_id=m["tenant_id"],  # type: ignore[index]
        status=str(m["status"]),  # type: ignore[index]
        last_check=m["last_check"],  # type: ignore[index]
        fail_count=int(m["fail_count"]),  # type: ignore[index]
        last_error=m["last_error"],  # type: ignore[index]
        domain=m["domain"],  # type: ignore[index]
        requires_key=bool(m["requires_key"]),  # type: ignore[index]
    )


class ToolHealthRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def read_status(self, name: str, tenant_id: UUID) -> ToolHealthRow | None:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT name, tenant_id, status, last_check, fail_count, "
                    "last_error, domain, requires_key FROM tool_health "
                    "WHERE name = :name AND tenant_id = :tenant_id"
                ),
                {"name": name, "tenant_id": tenant_id},
            )
            row = result.mappings().one_or_none()
            return _row_to_dataclass(row) if row is not None else None

    async def list_all(self, tenant_id: UUID) -> list[ToolHealthRow]:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT name, tenant_id, status, last_check, fail_count, "
                    "last_error, domain, requires_key FROM tool_health "
                    "WHERE tenant_id = :tenant_id ORDER BY name"
                ),
                {"tenant_id": tenant_id},
            )
            return [_row_to_dataclass(row) for row in result.mappings().all()]

    async def get_statuses_batch(self, names: list[str], tenant_id: UUID) -> dict[str, str]:
        """Get status for multiple tools in a single query (FR-002)."""
        if not names:
            return {}
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT name, status FROM tool_health "
                    "WHERE tenant_id = :tenant_id AND name = ANY(:names)"
                ),
                {"tenant_id": tenant_id, "names": names},
            )
            return {str(row["name"]): str(row["status"]) for row in result.mappings().all()}

    async def upsert(self, row: ToolHealthRow) -> None:
        """Uso EXCLUSIVO del HealthMonitor (CQS write)."""
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO tool_health "
                    "(name, tenant_id, status, last_check, fail_count, last_error, "
                    " domain, requires_key) "
                    "VALUES (:name, :tenant_id, :status, :last_check, :fail_count, "
                    " :last_error, :domain, :requires_key) "
                    "ON CONFLICT (name) DO UPDATE SET "
                    "  tenant_id = EXCLUDED.tenant_id, "
                    "  status = EXCLUDED.status, "
                    "  last_check = EXCLUDED.last_check, "
                    "  fail_count = EXCLUDED.fail_count, "
                    "  last_error = EXCLUDED.last_error, "
                    "  domain = EXCLUDED.domain, "
                    "  requires_key = EXCLUDED.requires_key"
                ),
                {
                    "name": row.name,
                    "tenant_id": row.tenant_id,
                    "status": row.status,
                    "last_check": row.last_check,
                    "fail_count": row.fail_count,
                    "last_error": row.last_error,
                    "domain": row.domain,
                    "requires_key": row.requires_key,
                },
            )
            await db.commit()
