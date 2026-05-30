"""Tests for PhaseCoordinator (T016)."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    ApprovalDeniedError,
    DirectoryNotWritableError,
    GuardrailViolationError,
    SandboxExecutionError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.phase_coordinator import (
    PhaseCoordinator,
)

from .conftest import FakeApproval, FakeAudit, FakeFileSystem, FakeLLM, FakeSandbox, FakeTemplate


def _make_coordinator(
    llm_response: str = "STACK: Python\nCONSTRAINTS: none\nTARGET_DIRECTORY: /tmp/p",
    sandbox_output: str = "OK",
    approved: bool = True,
    fs_exists: bool = True,
    max_llm_calls: int = 500,
    max_duration: int = 86400,
) -> tuple[PhaseCoordinator, FakeLLM, FakeApproval, FakeAudit]:
    llm = FakeLLM(response=llm_response)
    template = FakeTemplate()
    sandbox = FakeSandbox(output=sandbox_output)
    approval = FakeApproval(approved=approved)
    audit = FakeAudit()
    fs = FakeFileSystem(exists=fs_exists)
    coordinator = PhaseCoordinator(
        llm=llm,
        template=template,
        sandbox=sandbox,
        approval=approval,
        audit=audit,
        file_system=fs,
        max_llm_calls=max_llm_calls,
        max_duration_seconds=max_duration,
    )
    return coordinator, llm, approval, audit


@pytest.mark.asyncio
async def test_compleja_executes_7_phases_in_order() -> None:
    coordinator, llm, approval, audit = _make_coordinator()
    state = await coordinator.run("COMPLEJA", "build a tool")
    assert len(state.completed_phases) == 7
    assert state.completed_phases == [
        "constitution", "specify", "plan", "tasks", "analyze", "implement", "test"
    ]
    assert len(audit.entries) == 7


@pytest.mark.asyncio
async def test_gate_constitution_blocks_without_approval() -> None:
    coordinator, _, approval, _ = _make_coordinator(approved=False)
    with pytest.raises(ApprovalDeniedError) as exc_info:
        await coordinator.run("COMPLEJA", "build a tool")
    assert exc_info.value.phase == "constitution"


@pytest.mark.asyncio
async def test_gate_analyze_blocks_without_approval() -> None:
    """Approval passes for constitution but fails for analyze."""
    llm = FakeLLM(response="STACK: Python\nCONSTRAINTS: none\nTARGET_DIRECTORY: /tmp/p")
    template = FakeTemplate()
    sandbox = FakeSandbox(output="OK")
    audit = FakeAudit()
    fs = FakeFileSystem(exists=True)

    call_count = 0

    class ConditionalApproval:
        async def request_approval(self, phase: str, document: str) -> bool:
            nonlocal call_count
            call_count += 1
            # Approve constitution (first call), deny analyze (second call)
            return call_count == 1

    coordinator = PhaseCoordinator(
        llm=llm, template=template, sandbox=sandbox,
        approval=ConditionalApproval(),  # type: ignore[arg-type]
        audit=audit, file_system=fs,
    )
    with pytest.raises(ApprovalDeniedError) as exc_info:
        await coordinator.run("COMPLEJA", "build a tool")
    assert exc_info.value.phase == "analyze"


@pytest.mark.asyncio
async def test_sandbox_failure_reports_error_with_retries() -> None:
    coordinator, _, _, _ = _make_coordinator(sandbox_output="ERROR: segfault")
    with pytest.raises(SandboxExecutionError) as exc_info:
        await coordinator.run("MODERADA", "build a tool")
    assert exc_info.value.attempts == 2


@pytest.mark.asyncio
async def test_analyze_no_issues_continues_after_approval() -> None:
    """analyze with no inconsistencies still presents gate, then continues."""
    llm = FakeLLM(response="STATUS: sin issues")
    template = FakeTemplate()
    sandbox = FakeSandbox(output="OK")
    approval = FakeApproval(approved=True)
    audit = FakeAudit()
    fs = FakeFileSystem(exists=True)
    coordinator = PhaseCoordinator(
        llm=llm, template=template, sandbox=sandbox,
        approval=approval, audit=audit, file_system=fs,
    )
    state = await coordinator.run("COMPLEJA", "build a tool")
    # analyze gate was presented
    assert ("analyze", state.documents["analyze"]) in approval.requests
    assert "implement" in state.completed_phases


@pytest.mark.asyncio
async def test_guardrail_max_llm_calls_stops_execution() -> None:
    coordinator, _, _, _ = _make_coordinator(max_llm_calls=0)
    with pytest.raises(GuardrailViolationError) as exc_info:
        await coordinator.run("MODERADA", "build a tool")
    assert exc_info.value.guardrail == "max_total_llm_calls"
