"""Domain models for the audit trail and rollback system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ModificationStatus(StrEnum):
    APPLIED = "applied"
    PENDING_APPROVAL = "pending_approval"
    REVERTED = "reverted"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class TriggerKind(StrEnum):
    DREAMING_LOOP = "dreaming_loop"
    SKILL_CURATOR = "skill_curator"
    CONFIG_REFRESHER = "config_refresher"
    REGULATORY_WATCH = "regulatory_watch"
    ADMIN_REPO = "admin_repo"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class ModificationRecord:
    id: UUID
    tenant_id: UUID
    target_file: str
    target_kind: str
    diff: str
    diff_summary: str | None
    applied_at: datetime
    rollback_token: str
    agent_id: str
    session_id: UUID | None
    triggered_by: str
    justification: str | None
    status: ModificationStatus
    reverted_at: datetime | None = None
    reverted_by: str | None = None
    superseded_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ModificationResult:
    success: bool
    record: ModificationRecord | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RollbackResult:
    success: bool
    previous_content: str | None
    error: str | None = None
