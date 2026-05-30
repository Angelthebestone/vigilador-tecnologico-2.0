"""Approval gate: determines if a file modification requires human approval."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_APPROVAL_REQUIRED: frozenset[str] = frozenset({"config/company/policies.md"})


@dataclass(frozen=True, slots=True)
class ModeAuditSettings:
    """Settings for approval requirements per mode."""

    approval_required_for_files: frozenset[str] = field(
        default_factory=lambda: DEFAULT_APPROVAL_REQUIRED
    )


def requires_approval(target_file: str, mode_settings: ModeAuditSettings | None = None) -> bool:
    """Check if a target file requires human approval before applying changes."""
    required_files = (
        mode_settings.approval_required_for_files
        if mode_settings is not None
        else DEFAULT_APPROVAL_REQUIRED
    )
    return target_file in required_files
