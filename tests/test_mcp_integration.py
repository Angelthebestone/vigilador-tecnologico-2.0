from pathlib import Path

import pytest

from vigilancia_multiagente.api.security.startup_guard import validate_external_url, validate_stdio_command
from vigilancia_multiagente.infra.mcp.execution_client import MCPExecutionClient
from vigilancia_multiagente.infra.mcp.provider_registry import MCPAuthMode, MCPProviderConfig, MCPProviderRegistry, MCPTransport, RetryPolicy


def test_provider_registry_loads_manifest_and_indexes_tools():
    registry = MCPProviderRegistry()
    registry.load_manifest(Path("specs/002-vigilancia-multiagente/contracts/mcp-providers.json"))

    assert registry.get("tavily").transport == MCPTransport.HTTP
    assert registry.provider_names_for_tools(("tavily_search", "web_search_exa")) == ("tavily", "exa")


def test_security_guards_reject_invalid_mcp_targets():
    with pytest.raises(RuntimeError):
        validate_external_url("file:///etc/passwd")
    with pytest.raises(RuntimeError):
        validate_stdio_command("python tool.py && rm -rf /")


@pytest.mark.asyncio
async def test_execution_client_uses_http_retry_and_stdio_paths(monkeypatch):
    client = MCPExecutionClient()
    http_provider = MCPProviderConfig(
        name="web",
        transport=MCPTransport.HTTP,
        base_url_or_command="https://example.com",
        auth_mode=MCPAuthMode.API_KEY,
        timeout_ms=1000,
        retry_policy=RetryPolicy(max_attempts=2, backoff_ms=0),
    )
    stdio_provider = MCPProviderConfig(
        name="local",
        transport=MCPTransport.STDIO,
        base_url_or_command="python -c \"import sys, json; print(json.dumps({'ok': True}))\"",
        auth_mode=MCPAuthMode.NONE,
        timeout_ms=1000,
        retry_policy=RetryPolicy(max_attempts=1, backoff_ms=0),
    )

    async def fake_http(provider, tool_name, arguments):
        return {"provider": provider.name, "tool": tool_name, "arguments": arguments}

    async def fake_stdio(provider, tool_name, arguments):
        return {"provider": provider.name, "tool": tool_name, "arguments": arguments}

    monkeypatch.setattr(client, "_execute_http_tool", fake_http)
    monkeypatch.setattr(client, "_execute_stdio_tool", fake_stdio)

    http_result = await client.execute_tool(http_provider, "web-search", {"query": "ai"})
    stdio_result = await client.execute_tool(stdio_provider, "local-search", {"query": "ai"})

    assert http_result.payload["provider"] == "web"
    assert stdio_result.payload["provider"] == "local"
    await client.close()

