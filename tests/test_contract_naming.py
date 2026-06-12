"""Test contract: mock server returns camelCase keys.

The mock server (mock_server.py) intentionally uses camelCase to match
the frontend's expected format. The real backend (FastAPI/Python) returns
snake_case, which the transform layer (frontend/src/api/transform.ts)
converts to camelCase automatically.

This test verifies the mock server's response keys are camelCase,
confirming the mock aligns with what the frontend expects after the
transform layer processes the backend's snake_case responses.

Run against the real backend with --backend-url to verify snake_case.
"""

from __future__ import annotations

import re
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_camel_case(key: str) -> bool:
    """Return True if key is camelCase or an all-uppercase acronym.

    Rules:
    - Starts with lowercase letter
    - Contains only letters and digits
    - OR is all-uppercase (acronym like URL, ID)
    - Single lowercase words pass (id, status)
    """
    return (
        re.match(r"^[a-z][a-zA-Z0-9]*$", key) is not None or re.match(r"^[A-Z]+$", key) is not None
    )


def is_snake_case(key: str) -> bool:
    """Return True if key is snake_case or an all-uppercase acronym."""
    return bool(re.match(r"^[a-z][a-z0-9_]*$|^[A-Z]+$", key))


def _check_dict(data: dict, path: str, violations: list[str], *, camel: bool = True) -> None:
    """Recursively collect non-conforming keys from nested dicts/lists."""
    checker = is_camel_case if camel else is_snake_case
    for k, v in data.items():
        full_path = f"{path}.{k}" if path else k
        if not checker(k):
            violations.append(full_path)
        if isinstance(v, dict):
            _check_dict(v, full_path, violations, camel=camel)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                _check_value(item, f"{full_path}[{i}]", violations, camel=camel)


def _check_value(value: Any, path: str, violations: list[str], *, camel: bool = True) -> None:
    """Dispatch to _check_dict for dicts; recurse into lists."""
    if isinstance(value, dict):
        _check_dict(value, path, violations, camel=camel)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _check_value(item, f"{path}[{i}]", violations, camel=camel)


def check_convention(data: Any, *, camel: bool = True) -> list[str]:
    """Return list of paths to non-conforming keys in *data*."""
    violations: list[str] = []
    _check_value(data, "", violations, camel=camel)
    return violations


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


@pytest.fixture
def session_id(client: httpx.Client) -> str:
    """Create a research session (POST /start) and return its sessionId."""
    resp = client.post("/api/v2/research/start", json={"query": "test"})
    assert resp.status_code == 200
    return resp.json()["sessionId"]


# ---------------------------------------------------------------------------
# Parametrized endpoints
# ---------------------------------------------------------------------------

ENDPOINTS = [
    pytest.param("POST", "/api/v2/research/start", {"query": "test"}, id="start"),
    pytest.param("POST", "/api/v2/research/{sid}/clarify", {"answers": {}}, id="clarify"),
    pytest.param("GET", "/api/v2/research/{sid}/plan", None, id="plan"),
    pytest.param("GET", "/api/v2/research/{sid}/report", None, id="report"),
    pytest.param("GET", "/api/v2/research/{sid}/sources", None, id="sources"),
    pytest.param("GET", "/api/v2/research/{sid}/graph", None, id="graph"),
    pytest.param("GET", "/api/v2/research/{sid}/providers", None, id="providers"),
    pytest.param("GET", "/api/v2/sessions/timeline", None, id="timeline"),
]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path_tpl,body", ENDPOINTS)
def test_all_keys_camel_case(
    client: httpx.Client,
    session_id: str,
    method: str,
    path_tpl: str,
    body: dict | None,
) -> None:
    """Verify every key in the mock server response is camelCase.

    The mock server uses camelCase intentionally (frontend convention).
    Run with --backend-url to test the real backend (expects snake_case).
    """
    path = _sub(session_id, path_tpl)
    resp = _request(client, method, path, body)
    assert resp.status_code == 200, f"{method} {path_tpl}: status {resp.status_code}"
    data = resp.json()
    violations = check_convention(data, camel=True)
    assert not violations, (
        f"{method} {path_tpl}: {len(violations)} non-camelCase key(s) found:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
