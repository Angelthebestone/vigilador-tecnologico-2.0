"""SubagentRegistry — basic spawn / track for the F4a MVP (Spec 021 FR-051).

Tracks recursive agent spawns so observability tools can show the full
``parent → child → grandchild`` tree for a session. Spawn budget
enforcement (max depth, max total subagents) lives here too.

Out of scope for the MVP and explicitly **roadmap F4b**:
* pause / resume control
* approval gates on spawn
* hierarchical artifact propagation

Constitución:
* SRP: this class records spawn events. It does NOT execute the
  subagent — the orchestrator does and reports back.
* DIP: depends on a small repo Protocol. Tests pass an in-memory fake;
  production wires a Postgres adapter against the ``subagents`` table
  declared in ``infra/db/migrations/021_subagents.sql``.
* CQS: ``spawn`` and ``mark_*`` are commands; ``get`` / ``list_for_session``
  are queries.
* #4 explicit errors: depth overrun, status transition violations, and
  unknown ids raise typed errors with context.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from vigilancia_multiagente.enterprise.governance.audit_log import AuditLogPort

logger = logging.getLogger(__name__)


_DEFAULT_MAX_DEPTH = 5


class SubagentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _is_terminal(status: SubagentStatus) -> bool:
    return status == SubagentStatus.COMPLETED or status == SubagentStatus.FAILED


@dataclass
class SubagentRecord:
    """Mirrors one row of the ``subagents`` table."""

    id: UUID
    tenant_id: UUID
    parent_session_id: UUID
    parent_agent_id: str | None
    depth: int
    role: str
    spawn_reason: str
    status: SubagentStatus = SubagentStatus.ACTIVE
    last_progress_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class SubagentRepoPort(Protocol):
    """Persistence surface; in-memory in tests, Postgres in production."""

    async def save(self, record: SubagentRecord) -> None: ...

    async def update(self, record: SubagentRecord) -> None: ...

    async def get(self, subagent_id: UUID) -> SubagentRecord | None: ...

    async def list_for_session(
        self, tenant_id: UUID, parent_session_id: UUID
    ) -> list[SubagentRecord]: ...


class InMemorySubagentRepo:
    """Reference implementation for tests / local dev."""

    def __init__(self) -> None:
        self._records: dict[UUID, SubagentRecord] = {}

    async def save(self, record: SubagentRecord) -> None:
        self._records[record.id] = record

    async def update(self, record: SubagentRecord) -> None:
        if record.id not in self._records:
            raise KeyError(f"subagent {record.id} not in repo")
        self._records[record.id] = record

    async def get(self, subagent_id: UUID) -> SubagentRecord | None:
        return self._records.get(subagent_id)

    async def list_for_session(
        self, tenant_id: UUID, parent_session_id: UUID
    ) -> list[SubagentRecord]:
        return [
            r for r in self._records.values()
            if r.tenant_id == tenant_id
            and r.parent_session_id == parent_session_id
        ]


class SubagentDepthExceededError(RuntimeError):
    """Raised when ``spawn`` would exceed the configured max depth."""


class SubagentStatusTransitionError(RuntimeError):
    """Raised when ``mark_*`` is called on a terminal record."""


@dataclass
class SubagentRegistry:
    """Records subagent spawns + tracks their lifecycle."""

    repo: SubagentRepoPort
    max_depth: int = _DEFAULT_MAX_DEPTH
    audit_log: AuditLogPort | None = None

    async def spawn(
        self,
        *,
        tenant_id: UUID,
        parent_session_id: UUID,
        role: str,
        spawn_reason: str = "",
        parent_agent_id: str | None = None,
        parent_subagent_id: UUID | None = None,
    ) -> SubagentRecord:
        """Register a new subagent. Returns the new ``SubagentRecord``.

        ``parent_subagent_id`` is the **parent subagent** in the call tree
        (None when the parent is the top-level orchestrator). ``depth``
        derives from the parent record (or 0 when ``parent_subagent_id``
        is None).
        """
        if not role.strip():
            raise ValueError("SubagentRegistry.spawn: role required")

        depth = 0
        if parent_subagent_id is not None:
            parent = await self.repo.get(parent_subagent_id)
            if parent is None:
                raise ValueError(
                    f"SubagentRegistry.spawn: parent {parent_subagent_id} "
                    "not registered"
                )
            depth = parent.depth + 1

        if depth > self.max_depth:
            raise SubagentDepthExceededError(
                f"SubagentRegistry: depth {depth} > max_depth={self.max_depth}"
            )

        record = SubagentRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            parent_session_id=parent_session_id,
            parent_agent_id=parent_agent_id,
            depth=depth,
            role=role.strip(),
            spawn_reason=spawn_reason.strip(),
            status=SubagentStatus.ACTIVE,
            last_progress_at=datetime.now(UTC),
        )
        await self.repo.save(record)
        logger.info(
            "SubagentRegistry: spawn id=%s role=%s depth=%d tenant=%s",
            record.id, record.role, record.depth, record.tenant_id,
        )
        if self.audit_log is not None:
            self.audit_log.log_subagent_spawn(
                subagent_id=str(record.id),
                parent_session_id=str(record.parent_session_id),
                parent_agent_id=record.parent_agent_id,
                depth=record.depth,
                role=record.role,
                tenant_id=str(record.tenant_id),
            )
        return record

    async def mark_completed(self, subagent_id: UUID) -> SubagentRecord:
        return await self._set_terminal(subagent_id, SubagentStatus.COMPLETED)

    async def mark_failed(self, subagent_id: UUID) -> SubagentRecord:
        return await self._set_terminal(subagent_id, SubagentStatus.FAILED)

    async def _set_terminal(
        self, subagent_id: UUID, target: SubagentStatus
    ) -> SubagentRecord:
        record = await self.repo.get(subagent_id)
        if record is None:
            raise KeyError(f"SubagentRegistry: id {subagent_id} not found")
        if _is_terminal(record.status):
            raise SubagentStatusTransitionError(
                f"SubagentRegistry: id={subagent_id} already in terminal "
                f"status {record.status.value}"
            )
        record.status = target
        record.completed_at = datetime.now(UTC)
        record.last_progress_at = record.completed_at
        await self.repo.update(record)
        logger.info(
            "SubagentRegistry: %s id=%s role=%s",
            target.value, record.id, record.role,
        )
        return record

    async def heartbeat(self, subagent_id: UUID) -> None:
        record = await self.repo.get(subagent_id)
        if record is None:
            raise KeyError(f"SubagentRegistry: id {subagent_id} not found")
        if _is_terminal(record.status):
            return
        record.last_progress_at = datetime.now(UTC)
        await self.repo.update(record)

    async def list_for_session(
        self, tenant_id: UUID, parent_session_id: UUID
    ) -> list[SubagentRecord]:
        return await self.repo.list_for_session(tenant_id, parent_session_id)

    async def list_active(
        self, tenant_id: UUID, parent_session_id: UUID
    ) -> list[SubagentRecord]:
        rows = await self.list_for_session(tenant_id, parent_session_id)
        return [r for r in rows if r.status == SubagentStatus.ACTIVE]

    async def get(self, subagent_id: UUID) -> SubagentRecord | None:
        return await self.repo.get(subagent_id)


def filter_by_role(
    records: Iterable[SubagentRecord], role: str
) -> list[SubagentRecord]:
    """Convenience helper for callers (e.g. dashboards)."""
    return [r for r in records if r.role == role]


__all__ = [
    "InMemorySubagentRepo",
    "SubagentDepthExceededError",
    "SubagentRecord",
    "SubagentRegistry",
    "SubagentRepoPort",
    "SubagentStatus",
    "SubagentStatusTransitionError",
    "filter_by_role",
]
