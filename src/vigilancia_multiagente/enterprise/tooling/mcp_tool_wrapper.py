"""Adapter that exposes a fallback MCP process as a ``ToolWrapper`` (FR-001/002).

Bridges ``MCPProcessSupervisor`` (process lifecycle) and ``ToolRegistry`` (tool
contract) so an MCP-EXTERNO provider behaves like any other tool from the
agent's POV. Universal abstraction (021-D5 / FR-054): the agent calls
``execute(tool_name, args)`` and never knows whether the backend is native
in-process or a JSON-RPC subprocess.

Constitución:
* SRP: contract bridge only — no protocol logic, no process management.
* #4 Errores explícitos: errors surface with context, never silent stubs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
    MCPProcessSupervisor,
)
from vigilancia_multiagente.enterprise.tooling.mcp_client import (
    McpClientError,
    mcp_call_tool,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class McpToolWrapper:
    """Wraps a supervisor-managed MCP server as a ``ToolWrapper`` (FR-001).

    Attributes:
        name: Provider id matching the catalog and ``external.yaml`` entry.
        domain: Catalog domain (``search``, ``web``, ``research``, ...).
        requires_auth: True when the provider needs an API key / OAuth token.
        supervisor: Backreference for healthcheck + process access.
    """

    name: str
    domain: str
    requires_auth: bool
    supervisor: MCPProcessSupervisor
    is_external_mcp: bool = True

    async def healthcheck(self) -> HealthcheckResult:
        """Report process-level health from the supervisor."""
        try:
            status = self.supervisor.get_status(self.name)
        except KeyError as exc:
            return HealthcheckResult(
                status="UNKNOWN",
                error=f"MCP '{self.name}' not registered with supervisor: {exc}",
            )
        if status.state == "running":
            return HealthcheckResult(status="UP")
        if status.state == "stuck":
            return HealthcheckResult(
                status="DOWN",
                error=(
                    f"MCP '{self.name}' is stuck after "
                    f"{status.consecutive_failures} consecutive failures. "
                    f"Last error: {status.last_error or 'unknown'}"
                ),
            )
        return HealthcheckResult(
            status="DOWN",
            error=status.last_error or f"MCP '{self.name}' state={status.state}",
        )

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Delegate to the MCP via JSON-RPC ``tools/call``."""
        proc = self.supervisor.get_process(self.name)
        if proc is None or proc.returncode is not None:
            return {
                "error": f"MCP '{self.name}' process is not running",
                "tool_name": tool_name,
            }
        try:
            result = await mcp_call_tool(proc, tool_name, args)
            return result if isinstance(result, dict) else {"result": result}
        except McpClientError as exc:
            logger.error("MCP %s.%s failed: %s", self.name, tool_name, exc)
            return {"error": str(exc), "tool_name": tool_name}
