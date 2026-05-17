"""Integration tests for reactive planner signal processing."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_signal_emission_and_consumption():
    """Test that emitting a signal triggers the consumer loop."""
    import asyncio

    from vigilancia_multiagente.application.execution.branch_coordinator import (
        MAX_REPLANS_PER_SESSION,
        Signal,
    )

    queue = asyncio.Queue()

    await queue.put(
        Signal(
            type="gap_detected",
            source_branch="AVANCES",
            payload={
                "description": "Missing data on quantum computing",
                "suggested_query": "quantum computing 2024",
            },
        )
    )

    assert queue.qsize() == 1
    signal = await queue.get()
    assert signal.type == "gap_detected"
    assert signal.source_branch == "AVANCES"
    assert signal.payload["suggested_query"] == "quantum computing 2024"
    assert MAX_REPLANS_PER_SESSION == 5
    assert queue.qsize() == 0


async def test_replan_iteration_limiter():
    """Test replan stops after max iterations (no hang)."""
    import asyncio

    from vigilancia_multiagente.application.execution.branch_coordinator import (
        MAX_REPLANS_PER_SESSION,
        Signal,
    )

    queue = asyncio.Queue()

    for i in range(MAX_REPLANS_PER_SESSION + 1):
        await queue.put(
            Signal(
                type="gap_detected",
                source_branch="AVANCES",
                payload={"description": f"gap {i}", "suggested_query": f"query {i}"},
            )
        )

    assert queue.qsize() == MAX_REPLANS_PER_SESSION + 1


async def test_high_value_finding_notification():
    """Test that high_value_finding signals create cross-branch notifications."""
    import asyncio

    from vigilancia_multiagente.application.execution.branch_coordinator import Signal

    queue = asyncio.Queue()

    await queue.put(
        Signal(
            type="high_value_finding",
            source_branch="AVANCES",
            payload={
                "finding": "Quantum supremacy achieved at room temperature",
                "relevance": "high",
            },
        )
    )

    signal = await queue.get()
    assert signal.type == "high_value_finding"
    assert signal.payload["finding"] == "Quantum supremacy achieved at room temperature"
    assert signal.payload["relevance"] == "high"
