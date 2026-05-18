"""Test contract: mock server responses match expected backend response structures.

Starts mock_server.py as a subprocess, then verifies every API endpoint
returns the expected JSON keys (the "contract" the frontend depends on).
"""

from __future__ import annotations

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
STREAM_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    body: dict | None = None,
) -> httpx.Response:
    kwargs: dict = {}
    if body is not None:
        kwargs["json"] = body
    return client.request(method, path, **kwargs)


def _sub(sid: str, tpl: str) -> str:
    """Replace {sid} placeholder with actual session id."""
    return tpl.replace("{sid}", sid) if "{sid}" in tpl else tpl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_server():
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


@pytest.fixture
def session_id(client: httpx.Client) -> str:
    """Create a research session (POST /start) and return its sessionId."""
    resp = client.post("/api/v2/research/start", json={"query": "test"})
    assert resp.status_code == 200
    return resp.json()["sessionId"]


# ---------------------------------------------------------------------------
# Test: session lifecycle  (start, clarify, plan, approve)
# ---------------------------------------------------------------------------

LIFECYCLE = [
    pytest.param(
        "POST",
        "/api/v2/research/start",
        {"query": "test"},
        {"sessionId", "status", "questions"},
        id="start",
    ),
    pytest.param(
        "POST",
        "/api/v2/research/{sid}/clarify",
        {"answers": {}},
        {"sessionId", "status", "requiresApproval", "plan"},
        id="clarify",
    ),
    pytest.param(
        "GET",
        "/api/v2/research/{sid}/plan",
        None,
        {"sessionId", "plan"},
        id="plan",
    ),
    pytest.param(
        "POST",
        "/api/v2/research/{sid}/approve",
        None,
        {"sessionId", "status", "message"},
        id="approve",
    ),
]


@pytest.mark.parametrize("method,path_tpl,body,expected_keys", LIFECYCLE)
def test_research_lifecycle(
    client: httpx.Client,
    session_id: str,
    method: str,
    path_tpl: str,
    body: dict | None,
    expected_keys: set[str],
) -> None:
    path = _sub(session_id, path_tpl)
    resp = _request(client, method, path, body)
    assert resp.status_code == 200
    data = resp.json()
    missing = expected_keys - set(data.keys())
    assert not missing, f"{method} {path_tpl}: missing keys {missing}"
    if "sessionId" in expected_keys:
        assert data["sessionId"] == session_id


# ---------------------------------------------------------------------------
# Test: research outputs  (report, sources, graph, analytics, providers)
# ---------------------------------------------------------------------------

OUTPUTS = [
    pytest.param(
        "GET",
        "/api/v2/research/{sid}/report",
        {
            "sessionId",
            "markdown",
            "executiveSummary",
            "recommendations",
            "totalSourcesConsulted",
            "confidenceScore",
        },
        id="report",
    ),
    pytest.param(
        "GET",
        "/api/v2/research/{sid}/sources",
        {"sessionId", "total", "items"},
        id="sources",
    ),
    pytest.param(
        "GET",
        "/api/v2/research/{sid}/graph",
        {"sessionId", "nodes", "edges"},
        id="graph",
    ),
    pytest.param(
        "GET",
        "/api/v2/research/{sid}/graph/analytics",
        {"sessionId", "centralNodes", "clusters", "density"},
        id="graph_analytics",
    ),
    pytest.param(
        "GET",
        "/api/v2/research/{sid}/providers",
        {"sessionId", "providers"},
        id="providers",
    ),
]


@pytest.mark.parametrize("method,path_tpl,expected_keys", OUTPUTS)
def test_research_outputs(
    client: httpx.Client,
    session_id: str,
    method: str,
    path_tpl: str,
    expected_keys: set[str],
) -> None:
    path = _sub(session_id, path_tpl)
    resp = _request(client, method, path, None)
    assert resp.status_code == 200
    data = resp.json()
    missing = expected_keys - set(data.keys())
    assert not missing, f"{method} {path_tpl}: missing keys {missing}"
    if "sessionId" in expected_keys:
        assert data["sessionId"] == session_id


# ---------------------------------------------------------------------------
# Test: management operations  (ask, timeline, source_score, delete, export)
# ---------------------------------------------------------------------------

MANAGEMENT = [
    pytest.param(
        "POST",
        "/api/v2/sessions/{sid}/ask",
        {"query": "test"},
        {"answer", "sources", "requiresPermission"},
        id="session_ask",
    ),
    pytest.param(
        "DELETE",
        "/api/v2/research/{sid}",
        None,
        {"status", "sessionId"},
        id="research_delete",
    ),
    pytest.param(
        "GET",
        "/api/v2/sessions/timeline",
        None,
        {"sessions"},
        id="sessions_timeline",
    ),
]


@pytest.mark.parametrize("method,path_tpl,body,expected_keys", MANAGEMENT)
def test_management_operations(
    client: httpx.Client,
    session_id: str,
    method: str,
    path_tpl: str,
    body: dict | None,
    expected_keys: set[str],
) -> None:
    path = _sub(session_id, path_tpl)
    resp = _request(client, method, path, body)
    assert resp.status_code == 200
    data = resp.json()
    missing = expected_keys - set(data.keys())
    assert not missing, f"{method} {path_tpl}: missing keys {missing}"


def test_source_score(client: httpx.Client, session_id: str) -> None:
    """PATCH /api/v2/sources/{id}/score returns sourceId, newScore, adjustment."""
    sources_resp = client.get(f"/api/v2/research/{session_id}/sources")
    assert sources_resp.status_code == 200
    items = sources_resp.json()["items"]
    assert items, "No sources returned — cannot test score endpoint"
    source_id = items[0]["id"]

    resp = client.patch(
        f"/api/v2/sources/{source_id}/score",
        json={"delta": 1, "reason": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"sourceId", "newScore", "adjustment", "reason"}
    assert data["sourceId"] == source_id
    assert data["newScore"] == 76
    assert data["adjustment"] == 1


def test_report_export(client: httpx.Client) -> None:
    """GET /api/v2/reports/{id}/export?format=md returns content, format, reportId."""
    resp = client.get("/api/v2/reports/test-export-id/export", params={"format": "md"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"content", "format", "reportId"}
    assert data["format"] == "md"
    assert data["reportId"] == "test-export-id"
    assert isinstance(data["content"], str)
    assert len(data["content"]) > 0


# ---------------------------------------------------------------------------
# Test: SSE stream
# ---------------------------------------------------------------------------


def test_sse_stream(client: httpx.Client, session_id: str) -> None:
    """GET /api/v2/research/{id}/stream returns text/event-stream."""
    with client.stream(
        "GET",
        f"/api/v2/research/{session_id}/stream",
        timeout=STREAM_TIMEOUT,
    ) as response:
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type, (
            f"Expected text/event-stream, got {content_type}"
        )
        # Verify at least one SSE event line arrives
        for line in response.iter_lines():
            stripped = line.strip()
            if stripped:
                assert stripped.startswith(("event:", "data:")), (
                    f"Unexpected SSE line: {stripped!r}"
                )
                break
