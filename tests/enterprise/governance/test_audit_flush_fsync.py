"""T120 — Audit log fsync verification test."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vigilancia_multiagente.enterprise.governance.audit_log import AuditLog


@pytest.mark.asyncio
async def test_audit_log_calls_fsync_on_write(tmp_path: Path):
    """Verify that AuditLog._write calls os.fsync after flushing."""
    log = AuditLog(audit_dir=tmp_path)

    fsync_called = False
    original_fsync = os.fsync

    def mock_fsync(fd: int) -> None:
        nonlocal fsync_called
        fsync_called = True
        original_fsync(fd)

    with patch("vigilancia_multiagente.enterprise.governance.audit_log.os.fsync", mock_fsync):
        log.log_tool_invocation(
            tool_id="brave",
            operation="web_search",
            outcome="success",
            duration_ms=50.0,
        )

    assert fsync_called, "os.fsync should be called after writing audit entry"


@pytest.mark.asyncio
async def test_audit_log_creates_file_with_valid_json(tmp_path: Path):
    """Verify that audit log writes valid JSON lines."""
    log = AuditLog(audit_dir=tmp_path)

    log.log_tool_invocation(
        tool_id="brave",
        operation="web_search",
        outcome="success",
        duration_ms=50.0,
    )

    files = list(tmp_path.glob("events_*.jsonl"))
    assert len(files) == 1

    lines = files[0].read_text().strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["event"] == "tool_invocation"
    assert entry["tool_id"] == "brave"
