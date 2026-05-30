"""Audit persistence: DB insert and JSONL file writing with rotation."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vigilancia_multiagente.enterprise.governance.models import ModificationRecord

DEFAULT_AUDIT_DIR = Path.home() / ".vigilador" / "audit" / "agent_mods"
MAX_RETENTION_DAYS = 30


class AuditPersistence:
    def __init__(self, audit_dir: Path | None = None) -> None:
        self._audit_dir = audit_dir or DEFAULT_AUDIT_DIR

    async def persist_to_db(self, record: ModificationRecord, session: AsyncSession) -> None:
        """Insert a modification record into the agent_modifications table."""
        await session.execute(
            text(
                "INSERT INTO agent_modifications "
                "(id, tenant_id, target_file, target_kind, diff, diff_summary, "
                "applied_at, rollback_token, agent_id, session_id, triggered_by, "
                "justification, status, reverted_at, reverted_by, superseded_by) "
                "VALUES (:id, :tenant_id, :target_file, :target_kind, :diff, :diff_summary, "
                ":applied_at, :rollback_token, :agent_id, :session_id, :triggered_by, "
                ":justification, :status, :reverted_at, :reverted_by, :superseded_by)"
            ),
            {
                "id": record.id,
                "tenant_id": record.tenant_id,
                "target_file": record.target_file,
                "target_kind": record.target_kind,
                "diff": record.diff,
                "diff_summary": record.diff_summary,
                "applied_at": record.applied_at,
                "rollback_token": record.rollback_token,
                "agent_id": record.agent_id,
                "session_id": record.session_id,
                "triggered_by": record.triggered_by,
                "justification": record.justification,
                "status": record.status.value,
                "reverted_at": record.reverted_at,
                "reverted_by": record.reverted_by,
                "superseded_by": record.superseded_by,
            },
        )

    def persist_to_jsonl(self, record: ModificationRecord) -> None:
        """Append a record as a JSON line to the daily JSONL file."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        date_str = record.applied_at.strftime("%Y-%m-%d")
        filepath = self._audit_dir / f"{date_str}.jsonl"
        line = json.dumps(
            {
                "id": str(record.id),
                "tenant_id": str(record.tenant_id),
                "target_file": record.target_file,
                "triggered_by": record.triggered_by,
                "diff": record.diff,
                "diff_summary": record.diff_summary,
                "applied_at": record.applied_at.isoformat(),
                "rollback_token": record.rollback_token,
            },
            ensure_ascii=False,
        )
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def rotate_jsonl(self, max_days: int = MAX_RETENTION_DAYS) -> int:
        """Delete JSONL files older than max_days. Returns count of deleted files."""
        if not self._audit_dir.exists():
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=max_days)
        deleted = 0
        for filepath in self._audit_dir.glob("*.jsonl"):
            try:
                date_str = filepath.stem  # YYYY-MM-DD
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                if file_date < cutoff:
                    os.remove(filepath)
                    deleted += 1
            except ValueError:
                continue
        return deleted
