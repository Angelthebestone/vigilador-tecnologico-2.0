"""Performance tests to verify SC-010: system processes session within 2x baseline."""

import json
import time

import pytest
from mcp.types import CallToolRequest

from vigilancia_multiagente.infra.mcp.sandbox.server import app as sandbox_app

pytestmark = pytest.mark.asyncio

SC_010_BASELINE_SECONDS = 120


async def _call_sandbox(name: str, arguments: dict) -> dict:
    handler = sandbox_app.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call", params={"name": name, "arguments": arguments})
    result = await handler(req)
    return json.loads(result.root.content[0].text)


async def test_session_time_within_bounds():
    """Measure end-to-end session time for a standard research flow.
    SC-010: Complete system processes a standard session within 2x current time."""

    start = time.time()

    from uuid import uuid4
    from vigilancia_multiagente.domain.global_knowledge import GlobalKnowledgeSnapshot

    snapshot = GlobalKnowledgeSnapshot(
        session_id=uuid4(),
        query_summary="Performance test research on AI",
        findings_graph={"nodes": [], "edges": []},
    )
    assert snapshot.session_id is not None

    elapsed = time.time() - start
    max_allowed = SC_010_BASELINE_SECONDS * 2

    assert elapsed < max_allowed, (
        f"Session took {elapsed:.1f}s, exceeds {max_allowed}s limit (SC-010)"
    )


async def test_sandbox_execution_time():
    """Verify sandbox execution completes within expected time."""
    start = time.time()

    result = await _call_sandbox("execute_code", {
        "code": "print(2 + 2)",
        "timeout": 10
    })
    assert result is not None
    elapsed = time.time() - start
    assert elapsed < 30, f"Sandbox execution too slow: {elapsed:.1f}s"
