"""Tests for CLI audit commands (DB-free with mocked database)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from vigilancia_multiagente.cli.audit_commands import audit


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestAuditCLI:
    def test_audit_group_help(self, runner: CliRunner) -> None:
        result = runner.invoke(audit, ["--help"])
        assert result.exit_code == 0
        assert "changelog" in result.output
        assert "show" in result.output
        assert "rollback" in result.output
        assert "pending-approvals" in result.output
        assert "approve" in result.output
