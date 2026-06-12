"""F5a.D / T134 — AuditLog JSONL tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.governance.audit_log import (
    AuditLog,
    AuditLogError,
)


@pytest.fixture
def audit(tmp_path: Path) -> AuditLog:
    return AuditLog(audit_dir=tmp_path)


def test_log_tool_invocation_writes_jsonl_line(audit: AuditLog, tmp_path: Path) -> None:
    audit.log_tool_invocation(
        tool_id="tavily_search",
        operation="search",
        outcome="success",
        duration_ms=132.5,
        agent_id="agent-1",
        session_id="sess-1",
        metadata={"results_count": 5},
    )
    files = list(tmp_path.glob("events_*.jsonl"))
    assert len(files) == 1
    line = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert line["event"] == "tool_invocation"
    assert line["tool_id"] == "tavily_search"
    assert line["outcome"] == "success"
    assert line["duration_ms"] == 132.5
    assert line["metadata"] == {"results_count": 5}
    assert "timestamp" in line


def test_log_llm_call_records_model_tokens_latency(audit: AuditLog) -> None:
    audit.log_llm_call(
        model="gpt-4o-mini",
        prompt_tokens=120,
        completion_tokens=45,
        latency_ms=910.0,
        agent_id="planner",
        session_id="sess-2",
        prompt_excerpt="Summarize the article …",
    )
    line = audit.read_today()[-1]
    assert line["event"] == "llm_call"
    assert line["model"] == "gpt-4o-mini"
    assert line["prompt_tokens"] == 120
    assert line["completion_tokens"] == 45
    assert line["total_tokens"] == 165
    assert line["latency_ms"] == 910.0
    assert line["prompt_excerpt"].startswith("Summarize")


def test_log_complexity_decision_includes_input_output_reason(audit: AuditLog) -> None:
    audit.log_complexity_decision(
        query_excerpt="quick weather lookup",
        level="SIMPLE",
        reason="single-fact lookup",
        latency_ms=480.0,
        session_id="sess-3",
    )
    line = audit.read_today()[-1]
    assert line["event"] == "complexity"
    assert line["level"] == "SIMPLE"
    assert line["reason"] == "single-fact lookup"
    assert line["query_excerpt"] == "quick weather lookup"


def test_log_subagent_spawn_records_parent_and_depth(audit: AuditLog) -> None:
    audit.log_subagent_spawn(
        subagent_id="sub-42",
        parent_session_id="sess-4",
        parent_agent_id="planner",
        depth=2,
        role="branch-runner",
        tenant_id="tnt-1",
    )
    line = audit.read_today()[-1]
    assert line["event"] == "subagent_spawn"
    assert line["depth"] == 2
    assert line["parent_agent_id"] == "planner"
    assert line["role"] == "branch-runner"


def test_daily_rotation_uses_dated_file(audit: AuditLog, tmp_path: Path) -> None:
    """Two events on the same UTC day land in a single dated file."""
    audit.log_tool_invocation(tool_id="x", operation="op", outcome="success", duration_ms=1.0)
    audit.log_tool_invocation(tool_id="y", operation="op", outcome="success", duration_ms=2.0)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    path = tmp_path / f"events_{today}.jsonl"
    assert path.exists()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_audit_log_raises_on_unwritable_dir(monkeypatch, tmp_path: Path) -> None:
    audit = AuditLog(audit_dir=tmp_path / "nope")

    def boom(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "mkdir", boom)
    with pytest.raises(AuditLogError, match="Cannot create audit directory"):
        audit.log_tool_invocation(tool_id="x", operation="op", outcome="success", duration_ms=1.0)
