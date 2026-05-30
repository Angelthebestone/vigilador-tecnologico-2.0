"""Repository for agent_modifications table (read operations for queries)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vigilancia_multiagente.enterprise.governance.models import (
    ModificationRecord,
    ModificationStatus,
)


class AgentModificationsRepository:
    """Read-only repository for querying agent modifications (CQS: query side)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token(self, rollback_token: str) -> ModificationRecord | None:
        """Fetch a single record by rollback token."""
        result = await self._session.execute(
            text(
                "SELECT id, tenant_id, target_file, target_kind, diff, diff_summary, "
                "applied_at, rollback_token, agent_id, session_id, triggered_by, "
                "justification, status, reverted_at, reverted_by, superseded_by "
                "FROM agent_modifications WHERE rollback_token = :token"
            ),
            {"token": rollback_token},
        )
        row = result.mappings().first()
        return _row_to_record(row) if row is not None else None

    async def list_changelog(
        self, tenant_id: UUID, since: datetime | None = None, limit: int = 50
    ) -> list[ModificationRecord]:
        """List modifications for a tenant, optionally filtered by date."""
        if since is not None:
            result = await self._session.execute(
                text(
                    "SELECT id, tenant_id, target_file, target_kind, diff, diff_summary, "
                    "applied_at, rollback_token, agent_id, session_id, triggered_by, "
                    "justification, status, reverted_at, reverted_by, superseded_by "
                    "FROM agent_modifications "
                    "WHERE tenant_id = :tenant_id AND applied_at >= :since "
                    "ORDER BY applied_at DESC LIMIT :limit"
                ),
                {"tenant_id": tenant_id, "since": since, "limit": limit},
            )
        else:
            result = await self._session.execute(
                text(
                    "SELECT id, tenant_id, target_file, target_kind, diff, diff_summary, "
                    "applied_at, rollback_token, agent_id, session_id, triggered_by, "
                    "justification, status, reverted_at, reverted_by, superseded_by "
                    "FROM agent_modifications "
                    "WHERE tenant_id = :tenant_id "
                    "ORDER BY applied_at DESC LIMIT :limit"
                ),
                {"tenant_id": tenant_id, "limit": limit},
            )
        rows = result.mappings().all()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row: object) -> ModificationRecord:
    m = row  # RowMapping
    return ModificationRecord(
        id=m["id"],  # type: ignore[index]
        tenant_id=m["tenant_id"],  # type: ignore[index]
        target_file=m["target_file"],  # type: ignore[index]
        target_kind=m["target_kind"],  # type: ignore[index]
        diff=m["diff"],  # type: ignore[index]
        diff_summary=m["diff_summary"],  # type: ignore[index]
        applied_at=m["applied_at"],  # type: ignore[index]
        rollback_token=m["rollback_token"],  # type: ignore[index]
        agent_id=m["agent_id"],  # type: ignore[index]
        session_id=m["session_id"],  # type: ignore[index]
        triggered_by=m["triggered_by"],  # type: ignore[index]
        justification=m["justification"],  # type: ignore[index]
        status=ModificationStatus(m["status"]),  # type: ignore[index]
        reverted_at=m["reverted_at"],  # type: ignore[index]
        reverted_by=m["reverted_by"],  # type: ignore[index]
        superseded_by=m["superseded_by"],  # type: ignore[index]
    )
