"""Sandbox tool — native WRAP-SDK over the ``e2b`` Python SDK.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``sandbox`` / domain ``execution`` / capabilities
``[run_code, execute_command]``.

Strategy: WRAP-SDK using the ``e2b`` Python package (optional). E2B runs
short-lived isolated VMs; we expose code execution + shell commands.
Each ``execute()`` call provisions and tears down a fresh sandbox to
avoid state leakage across tenants/runs.

If ``e2b`` is not installed or ``VT_E2B_API_KEY`` is missing, healthcheck
reports UNCONFIGURED and ``execute()`` raises with the install command.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class SandboxTool:
    """Native tool for E2B-based code/command execution sandboxes."""

    name: str = "sandbox"
    domain: str = "execution"
    is_external_mcp: bool = False
    requires_auth: bool = True

    def _api_key(self) -> str | None:
        return os.getenv("VT_E2B_API_KEY") or None

    def _timeout_s(self) -> int:
        raw = os.getenv("VT_SANDBOX_TIMEOUT", "120")
        try:
            return int(raw)
        except ValueError:
            return 120

    async def healthcheck(self) -> HealthcheckResult:
        """Verify both the package is importable AND the API key is present."""
        try:
            import e2b  # noqa: F401  # presence-only import probe
        except ImportError:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=(
                    "e2b package not installed; run `pip install e2b` "
                    "to enable this tool"
                ),
            )
        if not self._api_key():
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="VT_E2B_API_KEY not set",
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``run_code`` — args: ``code`` (str, required), ``language`` (str,
          default ``python``). Returns ``{stdout, stderr, exit_code}``.
        * ``execute_command`` — args: ``command`` (str, required). Runs
          a shell command. Returns ``{stdout, stderr, exit_code}``.
        """
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError("SandboxTool: VT_E2B_API_KEY not configured")

        try:
            from e2b import Sandbox
        except ImportError as exc:
            raise RuntimeError(
                "SandboxTool: e2b package not installed; run `pip install e2b`"
            ) from exc

        if tool_name == "run_code":
            code = _required_str(args, "code", "SandboxTool")
            language = args.get("language") or "python"
            if not isinstance(language, str):
                raise ValueError("SandboxTool: 'language' must be a string")
            return await asyncio.to_thread(
                _run_code, Sandbox, api_key, code, language, self._timeout_s()
            )
        if tool_name == "execute_command":
            command = _required_str(args, "command", "SandboxTool")
            return await asyncio.to_thread(
                _run_command, Sandbox, api_key, command, self._timeout_s()
            )
        raise ValueError(
            f"SandboxTool: unknown tool_name '{tool_name}' "
            f"(supported: run_code, execute_command)"
        )


def _required_str(args: dict[str, object], key: str, tool: str) -> str:
    val = args.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"{tool}: '{key}' must be a non-empty string")
    return val


def _run_code(
    sandbox_cls: object, api_key: str, code: str, language: str, timeout_s: int
) -> dict[str, object]:
    """Synchronous helper run via asyncio.to_thread (e2b SDK is sync)."""
    sb = sandbox_cls(api_key=api_key, timeout=timeout_s)  # type: ignore[operator]
    try:
        # e2b 1.x: sb.run_code(code) returns a Result with stdout/stderr/exit_code.
        result = sb.run_code(code, language=language)
        return {
            "stdout": getattr(result, "stdout", ""),
            "stderr": getattr(result, "stderr", ""),
            "exit_code": getattr(result, "exit_code", 0),
        }
    finally:
        sb.close()  # type: ignore[attr-defined]


def _run_command(
    sandbox_cls: object, api_key: str, command: str, timeout_s: int
) -> dict[str, object]:
    sb = sandbox_cls(api_key=api_key, timeout=timeout_s)  # type: ignore[operator]
    try:
        # e2b: sb.process.start_and_wait(command) returns a Process result.
        result = sb.commands.run(command)  # type: ignore[attr-defined]
        return {
            "stdout": getattr(result, "stdout", ""),
            "stderr": getattr(result, "stderr", ""),
            "exit_code": getattr(result, "exit_code", 0),
        }
    finally:
        sb.close()  # type: ignore[attr-defined]
