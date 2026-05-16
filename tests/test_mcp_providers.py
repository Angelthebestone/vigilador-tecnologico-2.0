"""Integration tests for sandbox, markitdown, and playwright MCP providers."""

import json

import pytest
from mcp.types import CallToolRequest

from vigilancia_multiagente.infra.mcp.sandbox.server import app as sandbox_app

pytestmark = pytest.mark.asyncio


async def _call_sandbox(name: str, arguments: dict) -> dict:
    handler = sandbox_app.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call", params={"name": name, "arguments": arguments})
    result = await handler(req)
    return json.loads(result.root.content[0].text)


async def test_sandbox_execute_code():
    """Test that sandbox execute_code runs Python and returns output."""
    result = await _call_sandbox("execute_code", {
        "code": "print('hello world')",
        "timeout": 10
    })
    assert result is not None
    assert result.get("status") == "success"
    assert "hello world" in result.get("stdout", "")


async def test_sandbox_list_libraries():
    """Test that sandbox list_libraries returns available packages."""
    result = await _call_sandbox("list_libraries", {})
    assert result is not None
    assert result.get("status") == "success"
    assert "libraries" in result


async def test_sandbox_visualize():
    """Test that sandbox visualize generates a chart."""
    result = await _call_sandbox("visualize", {
        "data": {"x": [1, 2, 3], "y": [4, 5, 6], "title": "Test"},
        "plot_type": "line",
        "format": "png"
    })
    assert result is not None
    assert result.get("status") == "success"
    assert "image" in result


async def test_sandbox_timeout():
    """Test that sandbox enforces timeout."""
    result = await _call_sandbox("execute_code", {
        "code": "import time; time.sleep(10)",
        "timeout": 2
    })
    assert result is not None
    assert result.get("status") == "error"
    assert "timed out" in result.get("error", "")


async def test_markitdown_uri_validation():
    """Test markitdown wrapper rejects invalid URIs gracefully."""
    from vigilancia_multiagente.infra.mcp.markitdown_mcp import MarkitdownProvider
    provider = MarkitdownProvider()
    result = await provider.convert_to_markdown("")
    assert result.get("success") is False
    assert result.get("error")
