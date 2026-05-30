"""Superseded chain: marks previous modifications as superseded when a new one arrives."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def mark_superseded(
    tenant_id: UUID, target_file: str, new_id: UUID, session: AsyncSession
) -> int:
    """Mark all 'applied' entries for the same tenant+file as superseded.

    Returns the number of rows updated.
    """
    result = await session.execute(
        text(
            "UPDATE agent_modifications "
            "SET status = 'superseded', superseded_by = :new_id "
            "WHERE tenant_id = :tenant_id "
            "AND target_file = :target_file "
            "AND status = 'applied' "
            "AND id != :new_id"
        ),
        {"tenant_id": tenant_id, "target_file": target_file, "new_id": new_id},
    )
    return result.rowcount  # type: ignore[return-value]
