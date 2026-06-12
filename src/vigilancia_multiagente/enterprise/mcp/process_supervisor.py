"""MCP process supervisor — manages the (fallback) pool of external MCP processes.

Spec 021 FR-004/005/006/007/008.

Design:
* Boots one subprocess per entry in ``config/mcp/external.yaml``.
* Tracks per-MCP state: ``running | stuck | exited``.
* Restarts crashed processes with exponential backoff (1s → 2s → 4s → 8s →
  16s → 32s, max 5 retries). After 5 consecutive failures the MCP is marked
  ``stuck`` and not retried until manual intervention.
* Healthcheck stub: until the full MCP client is ported (deferred — see
  ``docs/f1-deferred-impl.md``), ``healthcheck()`` reports the **process**
  state only (alive/dead). When the client lands it will run
  ``initialize`` + ``tools/list`` and report protocol-level health.
* Native-first context (021-D5): the audit (``scripts/audit_mcp_strategy.py``)
  classifies every provider; MCP-EXTERNO is the fallback path. With the
  current audit result (0 MCP-EXTERNO), this supervisor manages **0 procesos**
  and ``start_all()`` is a no-op. The infrastructure is in place for any
  future provider that audit reclassifies to fallback.

Constitución:
* ≤400 LOC (current ~250).
* SRP: process lifecycle only — no protocol logic, no tool dispatch.
* Errores explícitos (#4): a stuck MCP is reported with a reason, not silently retried.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


_BACKOFF_SCHEDULE_S: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
_MAX_CONSECUTIVE_FAILURES = 5
_DEFAULT_HEALTHCHECK_INTERVAL_S = 60.0


@dataclass
class McpProcessSpec:
    """Static manifest of a single fallback MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    healthcheck_interval_sec: float = _DEFAULT_HEALTHCHECK_INTERVAL_S
    restart_policy: str = "on-failure"
    log_file: str | None = None


@dataclass
class McpProcessStatus:
    """Live state of a managed MCP subprocess."""

    name: str
    state: str = "stopped"  # stopped | running | stuck | exited
    pid: int | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    last_failure_at: float | None = None


class MCPProcessSupervisor:
    """Spawn/restart loop for fallback MCP servers (FR-004..008)."""

    def __init__(self, manifest_path: Path | str | None = None) -> None:
        self._manifest_path = (
            Path(manifest_path) if manifest_path else Path("config/mcp/external.yaml")
        )
        self._specs: dict[str, McpProcessSpec] = {}
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._status: dict[str, McpProcessStatus] = {}
        self._restart_tasks: dict[str, asyncio.Task[None]] = {}
        self._stop_requested = False

    # ------------------------------------------------------------------
    # Manifest loading
    # ------------------------------------------------------------------
    def _load_specs(self) -> dict[str, McpProcessSpec]:
        """Load the manifest. Missing file ⇒ empty dict (audit may show 0 fallbacks)."""
        if not self._manifest_path.exists():
            logger.info(
                "MCPProcessSupervisor: manifest not found at %s — 0 MCPs to supervise.",
                self._manifest_path,
            )
            return {}
        raw = yaml.safe_load(self._manifest_path.read_text(encoding="utf-8")) or {}
        entries = raw.get("mcps") or []
        if not isinstance(entries, list):
            raise ValueError(
                f"{self._manifest_path}: 'mcps' must be a list, got {type(entries).__name__}"
            )
        specs: dict[str, McpProcessSpec] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"{self._manifest_path}: each mcp entry must be a mapping")
            name = entry.get("name")
            command = entry.get("command")
            if not name or not command:
                raise ValueError(
                    f"{self._manifest_path}: each mcp entry needs 'name' and 'command'"
                )
            specs[name] = McpProcessSpec(
                name=name,
                command=command,
                args=list(entry.get("args") or []),
                env=dict(entry.get("env") or {}),
                healthcheck_interval_sec=float(
                    entry.get("healthcheck_interval_sec", _DEFAULT_HEALTHCHECK_INTERVAL_S)
                ),
                restart_policy=str(entry.get("restart_policy", "on-failure")),
                log_file=entry.get("log_file"),
            )
        return specs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def start_all(self) -> None:
        """Boot every MCP in the manifest. Idempotent."""
        self._stop_requested = False
        self._specs = self._load_specs()
        for name, spec in self._specs.items():
            self._status.setdefault(name, McpProcessStatus(name=name))
            await self._start_one(spec)

    async def restart(self, name: str) -> None:
        """Manually restart a single MCP (resets backoff counter)."""
        spec = self._specs.get(name)
        if spec is None:
            raise KeyError(f"MCPProcessSupervisor: unknown mcp '{name}'")
        await self._stop_one(name)
        status = self._status.setdefault(name, McpProcessStatus(name=name))
        status.consecutive_failures = 0
        status.last_error = None
        status.state = "stopped"
        await self._start_one(spec)

    def get_status(self, name: str) -> McpProcessStatus:
        """Return the live status of *name* (raises if unknown)."""
        if name not in self._status:
            raise KeyError(f"MCPProcessSupervisor: unknown mcp '{name}'")
        return self._status[name]

    def list_status(self) -> dict[str, McpProcessStatus]:
        """Return a copy of every MCP's status."""
        return dict(self._status)

    async def stop_all(self) -> None:
        """Graceful shutdown — terminate every running subprocess."""
        self._stop_requested = True
        for task in list(self._restart_tasks.values()):
            task.cancel()
        self._restart_tasks.clear()
        for name in list(self._procs.keys()):
            await self._stop_one(name)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    async def healthcheck(self, name: str) -> str:
        """Return process-level health: ``UP`` if pid alive, ``DOWN`` otherwise.

        Protocol-level healthcheck (``initialize`` + ``tools/list``) lands when
        the MCP client is ported — see ``docs/f1-deferred-impl.md``.
        """
        status = self.get_status(name)
        if status.state == "running":
            proc = self._procs.get(name)
            if proc is not None and proc.returncode is None:
                return "UP"
            return "DOWN"
        return "DOWN"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _start_one(self, spec: McpProcessSpec) -> None:
        """Spawn one subprocess. Records pid + state. Backoff on failure."""
        status = self._status.setdefault(spec.name, McpProcessStatus(name=spec.name))
        if status.state == "stuck":
            logger.warning(
                "MCPProcessSupervisor[%s]: stuck after %d failures — refusing to start.",
                spec.name,
                status.consecutive_failures,
            )
            return

        env = {**os.environ, **{k: os.path.expandvars(v) for k, v in spec.env.items()}}
        cmd = [spec.command, *spec.args]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except (OSError, ValueError) as exc:
            # Constitución #4: error transformation with explicit context.
            self._record_failure(spec, f"failed to spawn {shlex.join(cmd)}: {exc}")
            return

        self._procs[spec.name] = proc
        status.pid = proc.pid
        status.state = "running"
        status.last_error = None
        # Reset failure counter on a successful spawn so a long-lived process
        # that crashes once doesn't immediately go stuck.
        status.consecutive_failures = 0
        logger.info(
            "MCPProcessSupervisor[%s]: started pid=%s",
            spec.name,
            proc.pid,
        )

        # Background task: watch for exit and trigger backoff restart.
        self._restart_tasks[spec.name] = asyncio.create_task(self._watch_and_restart(spec, proc))

    async def _watch_and_restart(
        self, spec: McpProcessSpec, proc: asyncio.subprocess.Process
    ) -> None:
        """Wait for *proc* to exit; on unexpected exit, schedule a backoff restart."""
        try:
            await proc.wait()
        except asyncio.CancelledError:
            return
        if self._stop_requested:
            return
        status = self._status.get(spec.name)
        if status is None:
            return
        rc = proc.returncode
        status.state = "exited"
        if rc != 0:
            self._record_failure(spec, f"process exited with code {rc}")
            await self._schedule_backoff_restart(spec)

    def _record_failure(self, spec: McpProcessSpec, reason: str) -> None:
        status = self._status.setdefault(spec.name, McpProcessStatus(name=spec.name))
        status.consecutive_failures += 1
        status.last_error = reason
        status.last_failure_at = asyncio.get_event_loop().time()
        logger.warning(
            "MCPProcessSupervisor[%s]: failure #%d — %s",
            spec.name,
            status.consecutive_failures,
            reason,
        )
        if status.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
            status.state = "stuck"
            logger.error(
                "MCPProcessSupervisor[%s]: STUCK after %d failures. Manual restart() required.",
                spec.name,
                status.consecutive_failures,
            )

    async def _schedule_backoff_restart(self, spec: McpProcessSpec) -> None:
        """Wait the backoff delay, then attempt one restart."""
        status = self._status[spec.name]
        if status.state == "stuck" or self._stop_requested:
            return
        idx = min(status.consecutive_failures - 1, len(_BACKOFF_SCHEDULE_S) - 1)
        delay = _BACKOFF_SCHEDULE_S[max(idx, 0)]
        logger.info(
            "MCPProcessSupervisor[%s]: scheduling restart in %.1fs",
            spec.name,
            delay,
        )
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        if self._stop_requested or status.state == "stuck":
            return
        await self._start_one(spec)

    async def _stop_one(self, name: str) -> None:
        """Terminate a specific subprocess + cancel its watch task."""
        task = self._restart_tasks.pop(name, None)
        if task is not None:
            task.cancel()
            # Cancellation is expected here; awaiting the cancelled task
            # raises CancelledError which we suppress per documented intent.
            with contextlib.suppress(asyncio.CancelledError):
                await task
        proc = self._procs.pop(name, None)
        if proc is None:
            return
        if proc.returncode is None:
            # Process already gone is fine — that's the goal of stop_one.
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                proc.kill()
                await proc.wait()
        status = self._status.get(name)
        if status is not None:
            status.state = "stopped"
            status.pid = None
