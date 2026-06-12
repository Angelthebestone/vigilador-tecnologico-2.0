"""Test: verify SSE events from the mock server.

Connects to the SSE stream and validates event types, order,
and payload structure for the full research lifecycle.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
import pytest

MOCK_SERVER_PATH = Path(__file__).resolve().parent.parent / "mock_server.py"
BASE_URL = "http://localhost:8000"
MOCK_PORT = 8000
STARTUP_TIMEOUT = 30
STREAM_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Expected event sequence (core mandatory events in order)
# ---------------------------------------------------------------------------

MANDATORY_EVENTS = [
    "BranchStarted",
    "BranchCompleted",
    "AllBranchesCompleted",
    "FusionStarted",
    "FusionProgress",
    "FusionProgress",
    "GraphBuildingStarted",
    "GraphAnalyticsComputed",
    "ReportGenerated",
    "ReportVariantsGenerated",
    "EvaluationComputed",
]

BRANCH_TYPES = {"AVANCES", "COMERCIAL", "RIESGO", "PI_NORMATIVA", "COMPETITIVO", "OPORTUNIDADES"}

OPTIONAL_EVENTS = {"ReplanTriggered", "BranchFailed", "BranchRestarted"}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_server() -> Generator[str, Any, Any]:
    """Start the mock server as a subprocess; yield its base URL; tear down."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mock_server:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(MOCK_PORT),
        ],
        cwd=str(MOCK_SERVER_PATH.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server(proc)
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _wait_for_server(proc: subprocess.Popen) -> None:
    """Poll the mock server until it responds or timeout expires."""
    start = time.monotonic()
    while time.monotonic() - start < STARTUP_TIMEOUT:
        try:
            with httpx.Client(base_url=BASE_URL, timeout=2.0) as client:
                resp = client.post("/api/v2/research/start", json={"query": "test"})
                if resp.status_code == 200:
                    return
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError):
            pass
        time.sleep(0.5)
    _stdout, stderr = proc.communicate(timeout=5)
    pytest.fail(
        f"Mock server (pid={proc.pid}) not ready within {STARTUP_TIMEOUT}s. "
        f"stderr: {stderr.decode(errors='replace')[:500]}"
    )


@pytest.fixture
def client(mock_server: str) -> Generator[httpx.Client, Any, Any]:
    """Provide an httpx.Client pointed at the mock server."""
    with httpx.Client(base_url=mock_server) as _client:
        yield _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_all_sse_events(response: httpx.Response) -> list[dict[str, Any]]:
    """Parse all SSE events from an httpx streaming response.

    Uses a timeout on iter_lines to avoid hanging on long-running streams.
    """
    events: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in response.iter_lines():
        if not line:
            if current is not None:
                events.append(current)
                current = None
            continue
        if line.startswith("event: "):
            current = {"event": line[7:].strip(), "data": None}
        elif line.startswith("data: ") and current is not None:
            current["data"] = json.loads(line[6:])
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sse_events_sequence(client: httpx.Client) -> None:
    """Verify all SSE events appear in the correct order."""

    # Start research
    resp = client.post("/api/v2/research/start", json={"query": "test"})
    assert resp.status_code == 200
    sid: str = resp.json()["sessionId"]

    # Read all events from the stream
    with client.stream(
        "GET",
        f"/api/v2/research/{sid}/stream",
        timeout=STREAM_TIMEOUT,
    ) as response:
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type
        events = _read_all_sse_events(response)

    assert len(events) > 0, "No SSE events received from the stream"

    # Extract event types in order
    event_types = [e["event"] for e in events]

    # --- BranchStarted x6 ---
    branch_starts = [e for e in events if e["event"] == "BranchStarted"]
    assert len(branch_starts) == 6, f"Expected 6 BranchStarted events, got {len(branch_starts)}"
    seen_types = {e["data"]["branch"] for e in branch_starts}
    assert seen_types == BRANCH_TYPES, f"Missing branch types: {BRANCH_TYPES - seen_types}"

    # --- BranchProgress (at least one) ---
    branch_progress = [e for e in events if e["event"] == "BranchProgress"]
    assert len(branch_progress) > 0, "No BranchProgress events received"
    for bp in branch_progress:
        assert "branch" in bp["data"]
        assert "iteration" in bp["data"]
        assert "stepNumber" in bp["data"]["iteration"]
        assert "reasoning" in bp["data"]["iteration"]
        assert "result" in bp["data"]["iteration"]

    # --- BranchCompleted x6 ---
    branch_completed = [e for e in events if e["event"] == "BranchCompleted"]
    assert len(branch_completed) == 6, (
        f"Expected 6 BranchCompleted events, got {len(branch_completed)}"
    )
    completed_types = {e["data"]["branch"] for e in branch_completed}
    assert completed_types == BRANCH_TYPES

    # --- AllBranchesCompleted ---
    all_done = [e for e in events if e["event"] == "AllBranchesCompleted"]
    assert len(all_done) >= 1
    assert "sessionId" in all_done[0]["data"]

    # --- FusionStarted ---
    fusion_start = [e for e in events if e["event"] == "FusionStarted"]
    assert len(fusion_start) >= 1

    # --- FusionProgress x2 ---
    fusion_progress = [e for e in events if e["event"] == "FusionProgress"]
    assert len(fusion_progress) == 2, (
        f"Expected 2 FusionProgress events, got {len(fusion_progress)}"
    )
    assert fusion_progress[0]["data"]["progress"] == 50
    assert fusion_progress[1]["data"]["progress"] == 100

    # --- GraphBuildingStarted ---
    graph_build = [e for e in events if e["event"] == "GraphBuildingStarted"]
    assert len(graph_build) >= 1

    # --- GraphAnalyticsComputed ---
    graph_analytics = [e for e in events if e["event"] == "GraphAnalyticsComputed"]
    assert len(graph_analytics) >= 1

    # --- ReportGenerated ---
    report_gen = [e for e in events if e["event"] == "ReportGenerated"]
    assert len(report_gen) >= 1
    report = report_gen[0]["data"]["report"]
    assert "executiveSummary" in report
    assert "recommendations" in report
    assert "confidenceScore" in report
    assert "sessionId" in report

    # --- ReportVariantsGenerated ---
    variants = [e for e in events if e["event"] == "ReportVariantsGenerated"]
    assert len(variants) >= 1
    assert "types" in variants[0]["data"]

    # --- EvaluationComputed ---
    evals = [e for e in events if e["event"] == "EvaluationComputed"]
    assert len(evals) >= 1
    assert "evaluations" in evals[0]["data"]
    assert len(evals[0]["data"]["evaluations"]) == 6

    # --- Verify mandatory event order ---
    filtered = [t for t in event_types if t in set(MANDATORY_EVENTS)]
    for expected in MANDATORY_EVENTS:
        assert expected in filtered, f"Missing mandatory event: {expected}"
        assert filtered.index(expected) >= MANDATORY_EVENTS.index(expected), (
            f"{expected} out of order in {filtered}"
        )


def test_sse_event_data_types(client: httpx.Client) -> None:
    """Every SSE event must have valid JSON data with proper types."""

    resp = client.post("/api/v2/research/start", json={"query": "test"})
    assert resp.status_code == 200
    sid: str = resp.json()["sessionId"]

    with client.stream(
        "GET",
        f"/api/v2/research/{sid}/stream",
        timeout=STREAM_TIMEOUT,
    ) as response:
        assert response.status_code == 200
        events = _read_all_sse_events(response)

    for event in events:
        assert event["data"] is not None, f"Event {event['event']} has null data"
        assert isinstance(event["data"], dict), (
            f"Event {event['event']} data is not a dict: {type(event['data'])}"
        )
