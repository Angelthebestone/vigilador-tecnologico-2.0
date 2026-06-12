"""PIQuarantineRepository — persistencia de cuarentena PI (FR-009..FR-012)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Registro de un input cuarentenado."""

    id: UUID
    tenant_id: UUID
    source: str
    content_excerpt: str
    detected_patterns: list[str]
    severity: str
    quarantined_at: datetime
    approved_at: datetime | None = None
    approved_by: str | None = None


# FR-012: callable para reinyección al pipeline
OnQuarantineReleased = Callable[[str, str], None]

_release_handlers: list[OnQuarantineReleased] = []


def register_on_quarantine_released(handler: OnQuarantineReleased) -> None:
    """Registra un handler para reinyección post-aprobación (FR-012)."""
    _release_handlers.append(handler)


def _notify_released(content: str, source: str) -> None:
    for handler in _release_handlers:
        handler(content, source)


class PIQuarantineRepository:
    """Repositorio de cuarentena PI con persistencia PostgreSQL."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def quarantine(
        self,
        tenant_id: UUID,
        source: str,
        content_excerpt: str,
        detected_patterns: list[str],
        severity: str,
    ) -> UUID:
        """Inserta un registro de cuarentena. Retorna el ID generado."""
        record_id = uuid4()
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO pi_quarantine "
                    "(id, tenant_id, source, content_excerpt, detected_patterns, "
                    "severity, quarantined_at) "
                    "VALUES (:id, :tenant_id, :source, :content_excerpt, "
                    ":detected_patterns, :severity, :quarantined_at)"
                ),
                {
                    "id": str(record_id),
                    "tenant_id": str(tenant_id),
                    "source": source,
                    "content_excerpt": content_excerpt[:500],
                    "detected_patterns": json.dumps(detected_patterns),
                    "severity": severity,
                    "quarantined_at": now,
                },
            )
            await session.commit()
        return record_id

    async def list_pending(self, tenant_id: UUID) -> list[QuarantineRecord]:
        """Lista registros pendientes (sin aprobar) para un tenant."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, tenant_id, source, content_excerpt, detected_patterns, "
                    "severity, quarantined_at, approved_at, approved_by "
                    "FROM pi_quarantine "
                    "WHERE tenant_id = :tenant_id AND approved_at IS NULL "
                    "ORDER BY quarantined_at DESC"
                ),
                {"tenant_id": str(tenant_id)},
            )
            return [self._row_to_record(row) for row in result.fetchall()]

    async def get_by_id(self, record_id: UUID) -> QuarantineRecord | None:
        """Obtiene un registro por ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, tenant_id, source, content_excerpt, detected_patterns, "
                    "severity, quarantined_at, approved_at, approved_by "
                    "FROM pi_quarantine WHERE id = :id"
                ),
                {"id": str(record_id)},
            )
            row = result.fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    async def approve(self, record_id: UUID, approved_by: str) -> None:
        """Aprueba un registro cuarentenado (FR-011). Notifica handlers (FR-012)."""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE pi_quarantine SET approved_at = :approved_at, "
                    "approved_by = :approved_by WHERE id = :id AND approved_at IS NULL"
                ),
                {"approved_at": now, "approved_by": approved_by, "id": str(record_id)},
            )
            if (result.rowcount or 0) == 0:  # type: ignore[union-attr]
                raise ValueError(f"Quarantine record {record_id} not found or already approved")
            # Fetch content for reinjection
            row = await session.execute(
                text("SELECT content_excerpt, source FROM pi_quarantine WHERE id = :id"),
                {"id": str(record_id)},
            )
            record = row.fetchone()
            await session.commit()
        if record:
            _notify_released(record[0], record[1])

    @staticmethod
    def _row_to_record(row: object) -> QuarantineRecord:
        r = row  # type: ignore[index,reportIndexIssue]
        patterns = r[4] if isinstance(r[4], list) else json.loads(r[4])  # type: ignore[index]
        return QuarantineRecord(
            id=UUID(str(r[0])),  # type: ignore[index]
            tenant_id=UUID(str(r[1])),  # type: ignore[index]
            source=r[2],  # type: ignore[index]
            content_excerpt=r[3],  # type: ignore[index]
            detected_patterns=patterns,
            severity=r[5],  # type: ignore[index]
            quarantined_at=r[6],  # type: ignore[index]
            approved_at=r[7],  # type: ignore[index]
            approved_by=r[8],  # type: ignore[index]
        )
