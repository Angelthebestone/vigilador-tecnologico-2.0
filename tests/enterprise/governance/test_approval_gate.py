"""Tests for approval_gate module."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.governance.approval_gate import (
    ModeAuditSettings,
    requires_approval,
)


class TestRequiresApproval:
    def test_policies_md_requires_approval_by_default(self) -> None:
        assert requires_approval("config/company/policies.md") is True

    def test_unlisted_file_does_not_require_approval(self) -> None:
        assert requires_approval("config/skills/search.yaml") is False

    def test_custom_mode_settings_respected(self) -> None:
        settings = ModeAuditSettings(
            approval_required_for_files=frozenset({"config/modes/stealth.yaml"})
        )
        assert requires_approval("config/modes/stealth.yaml", settings) is True
        assert requires_approval("config/company/policies.md", settings) is False
