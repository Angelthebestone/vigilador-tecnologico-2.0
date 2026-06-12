"""F4a.E / T111 — SubagentRegistry tests (Spec 021 FR-051)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from vigilancia_multiagente.enterprise.orchestration.subagent_registry import (
    InMemorySubagentRepo,
    SubagentDepthExceededError,
    SubagentRegistry,
    SubagentStatus,
    SubagentStatusTransitionError,
)

_TENANT = UUID("00000000-0000-0000-0000-000000000001")
_SESSION = UUID("00000000-0000-0000-0000-000000000099")


@pytest.mark.asyncio
async def test_spawn_persists_record_with_depth_zero_when_no_parent():
    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo)
    record = await reg.spawn(
        tenant_id=_TENANT,
        parent_session_id=_SESSION,
        role="researcher",
        spawn_reason="needs deep dive",
    )
    persisted = await repo.get(record.id)
    assert persisted is not None
    assert persisted.tenant_id == _TENANT
    assert persisted.parent_session_id == _SESSION
    assert persisted.depth == 0
    assert persisted.status == SubagentStatus.ACTIVE


@pytest.mark.asyncio
async def test_spawn_links_parent_via_parent_agent_id_and_increments_depth():
    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo)
    parent = await reg.spawn(
        tenant_id=_TENANT,
        parent_session_id=_SESSION,
        role="lead",
        parent_agent_id="orchestrator",
    )
    child = await reg.spawn(
        tenant_id=_TENANT,
        parent_session_id=_SESSION,
        role="worker",
        parent_subagent_id=parent.id,
        parent_agent_id=parent.role,
    )
    assert child.depth == 1
    assert child.parent_agent_id == "lead"


@pytest.mark.asyncio
async def test_status_lifecycle_active_to_completed():
    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo)
    record = await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="r")
    assert record.status == SubagentStatus.ACTIVE
    completed = await reg.mark_completed(record.id)
    assert completed.status == SubagentStatus.COMPLETED
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_double_terminal_transition_raises():
    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo)
    record = await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="r")
    await reg.mark_completed(record.id)
    with pytest.raises(SubagentStatusTransitionError, match="terminal"):
        await reg.mark_failed(record.id)


@pytest.mark.asyncio
async def test_status_must_be_one_of_three_constants():
    """The enum is the source of truth — only ACTIVE/COMPLETED/FAILED."""
    assert {s.value for s in SubagentStatus} == {"ACTIVE", "COMPLETED", "FAILED"}


@pytest.mark.asyncio
async def test_max_depth_overrun_raises():
    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo, max_depth=2)
    a = await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="a")
    b = await reg.spawn(
        tenant_id=_TENANT,
        parent_session_id=_SESSION,
        role="b",
        parent_subagent_id=a.id,
    )
    c = await reg.spawn(
        tenant_id=_TENANT,
        parent_session_id=_SESSION,
        role="c",
        parent_subagent_id=b.id,
    )
    assert c.depth == 2
    with pytest.raises(SubagentDepthExceededError, match="depth 3"):
        await reg.spawn(
            tenant_id=_TENANT,
            parent_session_id=_SESSION,
            role="d",
            parent_subagent_id=c.id,
        )


@pytest.mark.asyncio
async def test_list_active_filters_terminal_records():
    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo)
    a = await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="a")
    b = await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="b")
    await reg.mark_completed(a.id)
    active = await reg.list_active(_TENANT, _SESSION)
    assert {r.id for r in active} == {b.id}


@pytest.mark.asyncio
async def test_spawn_rejects_empty_role():
    reg = SubagentRegistry(repo=InMemorySubagentRepo())
    with pytest.raises(ValueError, match="role required"):
        await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="   ")


@pytest.mark.asyncio
async def test_unknown_parent_subagent_id_raises():
    reg = SubagentRegistry(repo=InMemorySubagentRepo())
    with pytest.raises(ValueError, match="not registered"):
        await reg.spawn(
            tenant_id=_TENANT,
            parent_session_id=_SESSION,
            role="x",
            parent_subagent_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_heartbeat_updates_last_progress_at_only_when_active():
    import asyncio

    repo = InMemorySubagentRepo()
    reg = SubagentRegistry(repo=repo)
    record = await reg.spawn(tenant_id=_TENANT, parent_session_id=_SESSION, role="r")
    initial = record.last_progress_at
    # Pause briefly so the next ``datetime.now`` returns a strictly later
    # timestamp on hosts that resolve sub-microsecond clocks.
    await asyncio.sleep(0.001)
    await reg.heartbeat(record.id)
    refreshed = await repo.get(record.id)
    assert refreshed is not None
    assert refreshed.last_progress_at >= initial

    await reg.mark_completed(record.id)
    completed_at = (await repo.get(record.id)).last_progress_at  # type: ignore[union-attr]
    await asyncio.sleep(0.001)
    # heartbeat is a no-op on terminal records
    await reg.heartbeat(record.id)
    final = (await repo.get(record.id)).last_progress_at  # type: ignore[union-attr]
    assert final == completed_at
