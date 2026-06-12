"""End-to-end test for the app-development pipeline (T029)."""

from __future__ import annotations

import pytest

from vigilancia_multiagente.enterprise.orchestration.app_development.errors import (
    DirectoryNotWritableError,
)
from vigilancia_multiagente.enterprise.orchestration.app_development.phase_coordinator import (
    PhaseCoordinator,
)

from .conftest import FakeApproval, FakeAudit, FakeFileSystem, FakeLLM, FakeSandbox, FakeTemplate


@pytest.mark.asyncio
async def test_e2e_compleja_full_flow() -> None:
    """Full COMPLEJA flow: 7 phases, audit trail, copy to destination."""
    llm = FakeLLM(response="STACK: Python\nCONSTRAINTS: none\nTARGET_DIRECTORY: /tmp/proj")
    template = FakeTemplate()
    sandbox = FakeSandbox(output="OK - all tests passed")
    approval = FakeApproval(approved=True)
    audit = FakeAudit()
    fs = FakeFileSystem(exists=True)

    coordinator = PhaseCoordinator(
        llm=llm,
        template=template,
        sandbox=sandbox,
        approval=approval,
        audit=audit,
        file_system=fs,
    )
    state = await coordinator.run("COMPLEJA", "script Python que procese CSV")

    # 7 phases completed
    assert len(state.completed_phases) == 7

    # Audit trail has entry per phase
    assert len(audit.entries) == 7
    for entry in audit.entries:
        assert entry["triggered_by"] == "app_development_phase"

    # Gates were presented for constitution and analyze
    gate_phases = [phase for phase, _ in approval.requests]
    assert "constitution" in gate_phases
    assert "analyze" in gate_phases

    # Copy final
    await coordinator.copy_final(state, "/tmp/proj")
    assert len(fs.written) > 0

    # Zero host execution (sandbox only)
    assert len(sandbox.executions) > 0


@pytest.mark.asyncio
async def test_e2e_copy_final_fails_if_dir_missing() -> None:
    """EC-03: directory not writable raises error."""
    llm = FakeLLM(response="STACK: Python\nCONSTRAINTS: none\nTARGET_DIRECTORY: /tmp/proj")
    template = FakeTemplate()
    sandbox = FakeSandbox(output="OK")
    approval = FakeApproval(approved=True)
    audit = FakeAudit()
    fs = FakeFileSystem(exists=False)

    coordinator = PhaseCoordinator(
        llm=llm,
        template=template,
        sandbox=sandbox,
        approval=approval,
        audit=audit,
        file_system=fs,
    )
    state = await coordinator.run("MODERADA", "build tool")
    with pytest.raises(DirectoryNotWritableError):
        await coordinator.copy_final(state, "/nonexistent")
