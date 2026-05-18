"""Test: complete E2E flow against the mock server.

Covers the full research lifecycle:
  start → clarify → plan → approve → SSE stream → report
  → graph → providers → ask → delete
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
STREAM_TIMEOUT = 40


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


def read_until_event(
    client: httpx.Client,
    url: str,
    target_event: str,
    timeout: int = STREAM_TIMEOUT,
) -> list[dict[str, Any]]:
    """Read SSE events until *target_event* is found or timeout."""
    events: list[dict[str, Any]] = []
    with client.stream("GET", url, timeout=timeout) as response:
        assert response.status_code == 200
        current: dict[str, Any] | None = None
        for line in response.iter_lines():
            if not line:
                if current is not None:
                    events.append(current)
                    if current["event"] == target_event:
                        break
                    current = None
                continue
            if line.startswith("event: "):
                current = {"event": line[7:].strip(), "data": None}
            elif line.startswith("data: ") and current is not None:
                current["data"] = json.loads(line[6:])
    return events


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_e2e_full_flow(client: httpx.Client) -> None:
    """Simulate the complete research lifecycle against the mock server."""

    # Step 1 — Start
    resp = client.post("/api/v2/research/start", json={"query": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "sessionId" in data
    assert "status" in data
    assert "questions" in data
    sid: str = data["sessionId"]

    # Step 2 — Clarify
    resp = client.post(f"/api/v2/research/{sid}/clarify", json={"answers": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert data["status"] == "PLANNING"
    assert data["requiresApproval"] is True
    assert "plan" in data

    # Step 3 — Get plan
    resp = client.get(f"/api/v2/research/{sid}/plan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert "plan" in data
    assert "branches" in data["plan"]
    assert len(data["plan"]["branches"]) == 6

    # Step 4 — Approve
    resp = client.post(f"/api/v2/research/{sid}/approve", json={"approved": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert data["status"] == "EXECUTING"
    assert "message" in data

    # Step 5 — SSE stream until ReportGenerated
    events = read_until_event(
        client,
        f"/api/v2/research/{sid}/stream",
        "ReportGenerated",
        timeout=STREAM_TIMEOUT,
    )
    report_events = [e for e in events if e["event"] == "ReportGenerated"]
    assert len(report_events) >= 1, "ReportGenerated event not received"

    # Step 6 — Get report
    resp = client.get(f"/api/v2/research/{sid}/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert "executiveSummary" in data
    assert "markdown" in data
    assert "recommendations" in data
    assert "totalSourcesConsulted" in data
    assert "confidenceScore" in data

    # Step 7 — Get graph
    resp = client.get(f"/api/v2/research/{sid}/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0

    # Step 8 — Get providers
    resp = client.get(f"/api/v2/research/{sid}/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert "providers" in data
    assert len(data["providers"]) > 0

    # Step 9 — Ask follow-up
    resp = client.post(
        f"/api/v2/sessions/{sid}/ask",
        json={"query": "Tell me more about the risks"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "requiresPermission" in data

    # Step 10 — Delete
    resp = client.delete(f"/api/v2/research/{sid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessionId"] == sid
    assert data["status"] == "deleted"
