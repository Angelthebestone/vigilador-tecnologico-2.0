"""Tests for audit_persistence module (DB-free: JSONL and rotation only)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from vigilancia_multiagente.enterprise.governance.audit_persistence import AuditPersistence
from vigilancia_multiagente.enterprise.governance.models import (
    ModificationRecord,
    ModificationStatus,
)


def _make_record(applied_at: datetime | None = None) -> ModificationRecord:
    return ModificationRecord(
        id=uuid4(),
        tenant_id=uuid4(),
        target_file="config/skills/search.yaml",
        target_kind="skills",
        diff="--- a/config/skills/search.yaml\n+++ b/config/skills/search.yaml\n@@ -1 +1 @@\n-old\n+new\n",
        diff_summary="Updated search skill",
        applied_at=applied_at or datetime.now(UTC),
        rollback_token=str(uuid4()),
        agent_id="agent-1",
        session_id=uuid4(),
        triggered_by="skill_curator",
        justification="Improved search",
        status=ModificationStatus.APPLIED,
    )


class TestPersistToJsonl:
    def test_writes_valid_json_line(self, tmp_path: Path) -> None:
        persistence = AuditPersistence(audit_dir=tmp_path)
        record = _make_record()
        persistence.persist_to_jsonl(record)

        date_str = record.applied_at.strftime("%Y-%m-%d")
        filepath = tmp_path / f"{date_str}.jsonl"
        assert filepath.exists()
        line = filepath.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["id"] == str(record.id)
        assert data["target_file"] == record.target_file
        assert data["rollback_token"] == record.rollback_token

    def test_appends_multiple_records(self, tmp_path: Path) -> None:
        persistence = AuditPersistence(audit_dir=tmp_path)
        persistence.persist_to_jsonl(_make_record())
        persistence.persist_to_jsonl(_make_record())

        files = list(tmp_path.glob("*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2


class TestRotateJsonl:
    def test_deletes_old_files(self, tmp_path: Path) -> None:
        persistence = AuditPersistence(audit_dir=tmp_path)
        old_date = (datetime.now(UTC) - timedelta(days=35)).strftime("%Y-%m-%d")
        old_file = tmp_path / f"{old_date}.jsonl"
        old_file.write_text('{"test": true}\n', encoding="utf-8")

        deleted = persistence.rotate_jsonl(max_days=30)
        assert deleted == 1
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path: Path) -> None:
        persistence = AuditPersistence(audit_dir=tmp_path)
        recent_date = datetime.now(UTC).strftime("%Y-%m-%d")
        recent_file = tmp_path / f"{recent_date}.jsonl"
        recent_file.write_text('{"test": true}\n', encoding="utf-8")

        deleted = persistence.rotate_jsonl(max_days=30)
        assert deleted == 0
        assert recent_file.exists()
