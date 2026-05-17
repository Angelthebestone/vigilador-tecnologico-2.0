import asyncio
import json
import os
from asyncio.subprocess import PIPE
from dataclasses import dataclass
from typing import Any

import httpx

from vigilancia_multiagente.infra.mcp.provider_registry import MCPProviderConfig, MCPTransport


@dataclass(slots=True)
class ToolExecutionResult:
    provider: str
    tool_name: str
    payload: dict[str, Any]
    attempt_count: int
    result_status: str = "SUCCESS"


class MCPExecutionClient:
    def __init__(self) -> None:
        self._http_client = httpx.AsyncClient()

    async def close(self) -> None:
        await self._http_client.aclose()

    async def execute_tool(
        self,
        provider: MCPProviderConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        # Cache-first check (lazy import avoids circular dependency)
        from vigilancia_multiagente.api.dependencies import mcp_cache as _mcp_cache

        cache_key = json.dumps(arguments, sort_keys=True, default=str)
        cached = _mcp_cache.get(tool_name, cache_key)
        if cached is not None:
            return ToolExecutionResult(
                provider=provider.name,
                tool_name=tool_name,
                payload=cached,
                attempt_count=0,
                result_status="CACHED",
            )

        if provider.transport == MCPTransport.STDIO:
            payload = await self._execute_stdio_tool(provider, tool_name, arguments)
            if payload:
                _mcp_cache.set(tool_name, cache_key, payload)
            return ToolExecutionResult(
                provider=provider.name,
                tool_name=tool_name,
                payload=payload,
                attempt_count=1,
            )

        last_error: Exception | None = None
        for attempt in range(1, provider.retry_policy.max_attempts + 1):
            try:
                payload = await self._execute_http_tool(provider, tool_name, arguments)
                if payload:
                    _mcp_cache.set(tool_name, cache_key, payload)
                return ToolExecutionResult(
                    provider=provider.name,
                    tool_name=tool_name,
                    payload=payload,
                    attempt_count=attempt,
                )
            except (httpx.HTTPError, TimeoutError) as exc:
                last_error = exc
                if attempt == provider.retry_policy.max_attempts:
                    break
                await asyncio.sleep(provider.retry_policy.backoff_ms / 1000)

        raise RuntimeError(
            f"MCP tool execution failed for {provider.name}:{tool_name}"
        ) from last_error

    async def _execute_http_tool(
        self,
        provider: MCPProviderConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        base = provider.base_url_or_command.split("?")[0].rstrip("/")
        response = await self._http_client.post(
            base + "/tools/execute",
            json={"tool": tool_name, "arguments": arguments},
            headers=provider.headers,
            timeout=provider.timeout_ms / 1000,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("MCP response must be a JSON object")
        return data

    async def _execute_stdio_tool(
        self,
        provider: MCPProviderConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        command = [provider.base_url_or_command] + list(provider.arguments)
        env = {**os.environ, **provider.environment}
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            env=env,
        )
        request = json.dumps({"tool": tool_name, "arguments": arguments}).encode("utf-8")
        stdout, stderr = await process.communicate(request)
        if process.returncode != 0:
            raise RuntimeError(
                stderr.decode("utf-8") or f"STDIO MCP command failed: {provider.name}"
            )
        payload = json.loads(stdout.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("MCP STDIO response must be a JSON object")
        return payload
