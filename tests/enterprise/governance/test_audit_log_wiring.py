"""F5a.D / T136 — audit_log wiring smoke tests.

Confirms each runtime entry point delegates to AuditLog when one is
configured: ToolRegistry.execute, ComplexityClassifier.classify and
SubagentRegistry.spawn. The XiaomimimoClient wiring is exercised by
its own dedicated unit test (see test_xiaomimimo_audit.py); here we
keep the focus on the in-process, no-network integrations.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from vigilancia_multiagente.enterprise.governance.audit_log import AuditLog
from vigilancia_multiagente.enterprise.orchestration.complexity_classifier import (
    ComplexityClassifier,
)
from vigilancia_multiagente.enterprise.orchestration.subagent_registry import (
    InMemorySubagentRepo,
    SubagentRegistry,
)
from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry

_TENANT = UUID("00000000-0000-0000-0000-000000000099")


# ---------------------------------------------------------------------------
# Fakes — standalone to avoid heavy fixtures
# ---------------------------------------------------------------------------


class _FakeTool:
    name = "fake_search"
    description = "fake"
    domain = "search"
    requires_auth = False

    async def execute(self, name, args):
        return {"value": "ok"}


class _FailingTool:
    name = "boom"
    description = "fail"
    domain = "search"
    requires_auth = False

    async def execute(self, name, args):
        raise RuntimeError("boom")


class _FakeHealthRepo:
    async def read_status(self, name, tenant_id):
        return None


class _FakeEmbed:
    async def embed(self, text):
        return [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# ToolRegistry.execute → audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_registry_execute_emits_audit_event(tmp_path: Path):
    audit = AuditLog(audit_dir=tmp_path)
    registry = ToolRegistry(_FakeHealthRepo(), _FakeEmbed(), audit_log=audit)
    await registry.register(_FakeTool())

    out = await registry.execute(
        "fake_search",
        {"q": "x"},
        operation="search",
        agent_id="lead",
        session_id="sess",
    )
    assert out == {"value": "ok"}
    events = [
        json.loads(line)
        for line in (next(iter(tmp_path.glob("events_*.jsonl"))))
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(events) == 1
    assert events[0]["event"] == "tool_invocation"
    assert events[0]["tool_id"] == "fake_search"
    assert events[0]["outcome"] == "success"
    assert events[0]["agent_id"] == "lead"


@pytest.mark.asyncio
async def test_tool_registry_execute_emits_audit_on_error(tmp_path: Path):
    audit = AuditLog(audit_dir=tmp_path)
    registry = ToolRegistry(_FakeHealthRepo(), _FakeEmbed(), audit_log=audit)
    await registry.register(_FailingTool())

    with pytest.raises(RuntimeError, match="boom"):
        await registry.execute("boom", {})

    events = [
        json.loads(line)
        for line in (next(iter(tmp_path.glob("events_*.jsonl"))))
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[0]["event"] == "tool_invocation"
    assert events[0]["outcome"] == "error"
    assert events[0]["error"].startswith("RuntimeError:")


@pytest.mark.asyncio
async def test_tool_registry_execute_unknown_raises_keyerror(tmp_path: Path):
    audit = AuditLog(audit_dir=tmp_path)
    registry = ToolRegistry(_FakeHealthRepo(), _FakeEmbed(), audit_log=audit)
    with pytest.raises(KeyError):
        await registry.execute("not-registered", {})
    # No event is emitted because the lookup failed before the call.
    assert list(tmp_path.glob("events_*.jsonl")) == []


# ---------------------------------------------------------------------------
# ComplexityClassifier.classify → audit
# ---------------------------------------------------------------------------


class _StubLLM:
    async def complete(self, messages, **kwargs):
        return '{"level": "MODERATE", "reason": "two-step lookup"}'


@pytest.mark.asyncio
async def test_complexity_classifier_emits_audit_event(tmp_path: Path):
    audit = AuditLog(audit_dir=tmp_path)
    classifier = ComplexityClassifier(llm_client=_StubLLM(), audit_log=audit)
    decision = await classifier.classify("hi there", session_id="sess-c")
    assert decision.level.value == "MODERATE"

    events = [
        json.loads(line)
        for line in (next(iter(tmp_path.glob("events_*.jsonl"))))
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[0]["event"] == "complexity"
    assert events[0]["level"] == "MODERATE"
    assert events[0]["reason"] == "two-step lookup"
    assert events[0]["session_id"] == "sess-c"


# ---------------------------------------------------------------------------
# SubagentRegistry.spawn → audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subagent_spawn_emits_audit_event(tmp_path: Path):
    audit = AuditLog(audit_dir=tmp_path)
    registry = SubagentRegistry(repo=InMemorySubagentRepo(), audit_log=audit)
    record = await registry.spawn(
        tenant_id=_TENANT,
        parent_session_id=uuid4(),
        role="branch-runner",
        spawn_reason="vigilancia-tech wrap",
        parent_agent_id="coordinator",
    )
    events = [
        json.loads(line)
        for line in (next(iter(tmp_path.glob("events_*.jsonl"))))
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[0]["event"] == "subagent_spawn"
    assert events[0]["depth"] == 0
    assert events[0]["role"] == "branch-runner"
    assert events[0]["parent_agent_id"] == "coordinator"
    assert events[0]["subagent_id"] == str(record.id)
