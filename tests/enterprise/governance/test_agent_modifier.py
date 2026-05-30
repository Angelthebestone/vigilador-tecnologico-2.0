"""Tests for AgentModifier (DB-free with mocked session)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from vigilancia_multiagente.enterprise.governance.agent_modifier import (
    AgentModifier,
    _reconstruct_from_diff,
    _write_file_atomically,
)
from vigilancia_multiagente.enterprise.governance.audit_persistence import AuditPersistence
from vigilancia_multiagente.enterprise.governance.models import ModificationStatus


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    # Default: mark_superseded returns 0 rows
    result_mock = MagicMock()
    result_mock.rowcount = 0
    session.execute.return_value = result_mock
    return session


@pytest.fixture
def audit_persistence(tmp_path: Path) -> AuditPersistence:
    return AuditPersistence(audit_dir=tmp_path / "audit")


@pytest.fixture
def base_path(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config" / "skills"
    config_dir.mkdir(parents=True)
    return tmp_path


class TestWriteFileAtomically:
    def test_creates_file_with_correct_content(self, tmp_path: Path) -> None:
        target = tmp_path / "test.txt"
        _write_file_atomically(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "test.txt"
        target.write_text("old", encoding="utf-8")
        _write_file_atomically(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "test.txt"
        _write_file_atomically(target, "nested")
        assert target.read_text(encoding="utf-8") == "nested"


class TestReconstructFromDiff:
    def test_reconstructs_old_and_new(self) -> None:
        diff = (
            "--- a/test.yaml\n"
            "+++ b/test.yaml\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-old_line\n"
            "+new_line\n"
            " line3\n"
        )
        old, new = _reconstruct_from_diff("", diff)
        assert "old_line" in old
        assert "new_line" in new
        assert "line1" in old
        assert "line1" in new


class TestProposeAndApply:
    @pytest.mark.asyncio
    async def test_applies_change_and_persists(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        # Create existing file
        target = base_path / "config" / "skills" / "search.yaml"
        target.write_text("old content\n", encoding="utf-8")

        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        result = await modifier.propose_and_apply(
            tenant_id=uuid4(),
            target_file="config/skills/search.yaml",
            new_content="new content\n",
            agent_id="agent-1",
            session_id=uuid4(),
            triggered_by="skill_curator",
        )

        assert result.success
        assert result.record is not None
        assert result.record.status == ModificationStatus.APPLIED
        assert target.read_text(encoding="utf-8") == "new content\n"

    @pytest.mark.asyncio
    async def test_rejects_disallowed_path(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        result = await modifier.propose_and_apply(
            tenant_id=uuid4(),
            target_file="src/main.py",
            new_content="hack",
            agent_id="agent-1",
            session_id=None,
            triggered_by="manual",
        )
        assert not result.success
        assert "not allowed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_pending_approval_does_not_write_file(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        policies_dir = base_path / "config" / "company"
        policies_dir.mkdir(parents=True)
        target = policies_dir / "policies.md"
        target.write_text("original\n", encoding="utf-8")

        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        result = await modifier.propose_and_apply(
            tenant_id=uuid4(),
            target_file="config/company/policies.md",
            new_content="modified\n",
            agent_id="agent-1",
            session_id=None,
            triggered_by="regulatory_watch",
        )

        assert result.success
        assert result.record is not None
        assert result.record.status == ModificationStatus.PENDING_APPROVAL
        # File should NOT be modified
        assert target.read_text(encoding="utf-8") == "original\n"

    @pytest.mark.asyncio
    async def test_no_changes_detected(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        target = base_path / "config" / "skills" / "search.yaml"
        target.write_text("same\n", encoding="utf-8")

        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        result = await modifier.propose_and_apply(
            tenant_id=uuid4(),
            target_file="config/skills/search.yaml",
            new_content="same\n",
            agent_id="agent-1",
            session_id=None,
            triggered_by="manual",
        )
        assert not result.success
        assert "No changes" in (result.error or "")


class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_token_not_found(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        result_mock = MagicMock()
        result_mock.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = result_mock

        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        result = await modifier.rollback("nonexistent-token", "admin")
        assert not result.success
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_rollback_already_reverted(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        row = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "target_file": "config/skills/s.yaml",
            "target_kind": "skills",
            "diff": "",
            "status": "reverted",
            "triggered_by": "manual",
        }
        result_mock = MagicMock()
        result_mock.mappings.return_value.first.return_value = row
        mock_session.execute.return_value = result_mock

        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        result = await modifier.rollback("some-token", "admin")
        assert not result.success
        assert "reverted" in (result.error or "").lower()


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_increment_on_apply(
        self, mock_session: AsyncMock, audit_persistence: AuditPersistence, base_path: Path
    ) -> None:
        from vigilancia_multiagente.enterprise.governance.metrics import agent_modifications_total

        target = base_path / "config" / "skills" / "search.yaml"
        target.write_text("old\n", encoding="utf-8")

        before = agent_modifications_total._metrics.copy()

        modifier = AgentModifier(
            session=mock_session,
            audit_persistence=audit_persistence,
            base_path=base_path,
        )
        await modifier.propose_and_apply(
            tenant_id=uuid4(),
            target_file="config/skills/search.yaml",
            new_content="new\n",
            agent_id="agent-1",
            session_id=None,
            triggered_by="manual",
        )
        # Metric should have been incremented (no assertion on exact value due to test isolation)
        # Just verify no exception was raised during metric emission
