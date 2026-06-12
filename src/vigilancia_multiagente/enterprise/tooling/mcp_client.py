"""MCP JSON-RPC client — sends tools/call to a managed subprocess via stdio.

Minimal implementation of the MCP protocol (JSON-RPC 2.0 over stdio) to
bridge ``MCPProcessSupervisor`` subprocesses with ``McpToolWrapper.execute()``.

Supports:
- ``initialize`` handshake
- ``tools/list`` enumeration
- ``tools/call`` execution

Constitución:
* SRP: protocol client only — no process management, no tool dispatch.
* ≤200 LOC.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MCP_TIMEOUT_S = 30.0


class McpClientError(Exception):
    """Raised when an MCP JSON-RPC call fails."""


async def mcp_initialize(proc: asyncio.subprocess.Process) -> dict[str, Any]:
    """Send ``initialize`` handshake and return server capabilities."""
    resp = await _send_request(proc, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "vigilador", "version": "3.0.0"},
    })
    await _send_notification(proc, "notifications/initialized", {})
    return resp


async def mcp_list_tools(proc: asyncio.subprocess.Process) -> list[dict[str, Any]]:
    """Return the list of tools the MCP server exposes."""
    resp = await _send_request(proc, "tools/list", {})
    return resp.get("tools", [])


async def mcp_call_tool(
    proc: asyncio.subprocess.Process,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call a tool and return the result content."""
    resp = await _send_request(proc, "tools/call", {
        "name": tool_name,
        "arguments": arguments,
    })
    return resp


async def _send_request(
    proc: asyncio.subprocess.Process,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Send a JSON-RPC request and wait for the response."""
    if proc.stdin is None or proc.stdout is None:
        raise McpClientError(f"MCP process stdin/stdout not available for {method}")

    request_id = id(params)
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }

    line = json.dumps(request) + "\n"
    proc.stdin.write(line.encode())
    await proc.stdin.drain()

    try:
        raw = await asyncio.wait_for(proc.stdout.readline(), timeout=_MCP_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        raise McpClientError(f"MCP request {method} timed out after {_MCP_TIMEOUT_S}s") from exc

    if not raw:
        raise McpClientError(f"MCP process closed stdout during {method}")

    response = json.loads(raw.decode())
    if "error" in response:
        err = response["error"]
        raise McpClientError(
            f"MCP {method} returned error {err.get('code')}: {err.get('message')}"
        )
    return response.get("result", {})


async def _send_notification(
    proc: asyncio.subprocess.Process,
    method: str,
    params: dict[str, Any],
) -> None:
    """Send a JSON-RPC notification (no response expected)."""
    if proc.stdin is None:
        return
    notification = {"jsonrpc": "2.0", "method": method, "params": params}
    line = json.dumps(notification) + "\n"
    proc.stdin.write(line.encode())
    await proc.stdin.drain()
