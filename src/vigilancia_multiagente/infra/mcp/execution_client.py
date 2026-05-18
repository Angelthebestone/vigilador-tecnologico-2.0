import asyncio
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
        """Ejecuta una tool en un servidor MCP STDIO vía el cliente oficial.

        Usa el protocolo MCP real (handshake JSON-RPC + ``call_tool``) del
        SDK, no un protocolo ad-hoc: por eso es compatible con cualquier
        servidor MCP estándar (arxiv, fetch, brave, sandbox, etc.). La
        respuesta MCP llega como ``content`` (lista de bloques); el texto se
        parsea a dict si es JSON, o se envuelve en ``{"text": ...}``.
        """
        params = StdioServerParameters(
            command=provider.base_url_or_command,
            args=list(provider.arguments),
            env={**os.environ, **provider.environment},
        )
        timeout_s = provider.timeout_ms / 1000

        async def _call() -> Any:
            async with (
                stdio_client(params) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                return await session.call_tool(
                    tool_name,
                    arguments,
                    read_timeout_seconds=timedelta(seconds=timeout_s),
                )

        # Cota dura sobre todo el ciclo (handshake + llamada + cierre del
        # subproceso). En Windows el teardown de stdio_client puede colgarse
        # si el server tardó; wait_for garantiza que no bloquee el backend.
        result = await asyncio.wait_for(_call(), timeout=timeout_s + 15)
        return _payload_from_call_result(result)


def _payload_from_call_result(result: Any) -> dict[str, Any]:
    """Normaliza un ``CallToolResult`` del SDK MCP a ``dict``.

    Los servidores devuelven bloques de contenido; el caso normal es un
    único ``TextContent``. Si su texto es un objeto JSON se devuelve tal
    cual (contrato que el resto del sistema espera); si es texto plano se
    envuelve en ``{"text": ...}``; sin contenido, se reporta el estado.
    """
    content = getattr(result, "content", None) or []
    text_parts = [
        block.text
        for block in content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    if not text_parts:
        is_error = bool(getattr(result, "isError", False))
        return {"status": "error" if is_error else "success", "content": []}

    joined = "\n".join(text_parts).strip()
    try:
        parsed = json.loads(joined)
    except (ValueError, TypeError):
        return {"status": "success", "text": joined}
    return parsed if isinstance(parsed, dict) else {"status": "success", "data": parsed}
