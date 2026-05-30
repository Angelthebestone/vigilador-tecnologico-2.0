"""Approval queue: query interface for pending modifications awaiting human approval.

This module is provided by spec 016 and consumed by spec 013.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vigilancia_multiagente.enterprise.governance.models import (
    ModificationRecord,
    ModificationStatus,
)


async def list_pending_approvals(
    tenant_id: UUID, session: AsyncSession
) -> list[ModificationRecord]:
    """Return all pending_approval records for a tenant, ordered by applied_at DESC."""
    result = await session.execute(
        text(
            "SELECT id, tenant_id, target_file, target_kind, diff, diff_summary, "
            "applied_at, rollback_token, agent_id, session_id, triggered_by, "
            "justification, status, reverted_at, reverted_by, superseded_by "
            "FROM agent_modifications "
            "WHERE tenant_id = :tenant_id AND status = 'pending_approval' "
            "ORDER BY applied_at DESC"
        ),
        {"tenant_id": tenant_id},
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
