"""Adapter that exposes a fallback MCP process as a ``ToolWrapper`` (FR-001/002).

Bridges ``MCPProcessSupervisor`` (process lifecycle) and ``ToolRegistry`` (tool
contract) so an MCP-EXTERNO provider behaves like any other tool from the
agent's POV. Universal abstraction (021-D5 / FR-054): the agent calls
``execute(tool_name, args)`` and never knows whether the backend is native
in-process or a JSON-RPC subprocess.

Current revision (Phase F1.A-F partial):
* ``healthcheck()`` reports the supervisor's process-level state — adequate
  for tool-gating until the protocol-level client is ported.
* ``execute()`` raises a clear ``NotImplementedError`` until the MCP client
  (Hermes ``tools/mcp_tool.py``, 3711 LOC, deferred — see
  ``docs/f1-deferred-impl.md``) is modularized into ``enterprise/tooling/mcp_client/``.
  The audit shows 0 MCP-EXTERNO providers today, so this code path is never
  exercised at runtime; the wrapper exists so any future fallback is wired
  uniformly without changing the registry.

Constitución:
* SRP: contract bridge only — no protocol logic, no process management.
* #4 Errores explícitos: ``execute()`` of an un-bridged MCP raises with
  context, never silently returns empty data.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.mcp.process_supervisor import (
    MCPProcessSupervisor,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class McpToolWrapper:
    """Wraps a supervisor-managed MCP server as a ``ToolWrapper`` (FR-001).

    Intentionally minimal: per FR-013, tools with ``is_external_mcp=True``
    delegate ``execute()`` over JSON-RPC and run no domain logic in-process.
    Until the MCP client lands, ``execute()`` raises explicitly.

    Attributes:
        name: Provider id matching the catalog and ``external.yaml`` entry.
        domain: Catalog domain (``search``, ``web``, ``research``, ...).
        requires_auth: True when the provider needs an API key / OAuth token.
        supervisor: Backreference for healthcheck.
    """

    name: str
    domain: str
    requires_auth: bool
    supervisor: MCPProcessSupervisor
    is_external_mcp: bool = True

    async def healthcheck(self) -> HealthcheckResult:
        """Report process-level health from the supervisor.

        Protocol-level health (``initialize`` + ``tools/list``) requires the
        MCP client port; until then the process state is the source of truth.
        """
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

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Delegate to the MCP via JSON-RPC ``tools/call``.

        **Not yet implemented** — pending the mcp_client port (see
        ``docs/f1-deferred-impl.md``). Constitución #4: explicit error,
        never a silent stub return.
        """
        raise NotImplementedError(
            f"McpToolWrapper.execute({self.name}.{tool_name}): the MCP client "
            "port is deferred (Hermes tools/mcp_tool.py, 3711 LOC → "
            "enterprise/tooling/mcp_client/ submodules). The current audit "
            "reports 0 MCP-EXTERNO providers, so this path is not exercised "
            "at runtime. See docs/f1-deferred-impl.md for the implementation plan. "
            f"args={args!r}"
        )
