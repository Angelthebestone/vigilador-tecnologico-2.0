"""``computer_use`` tool — entry point exposed via ``ToolRegistry``.

# Inspired by Hermes Agent — tools/computer_use/tool.py — License: MIT
# (Windows-first reimplementation; not a verbatim port — Hermes is macOS-only.)

Spec 021 F3a.B / FR-029 / FR-030. Wraps :class:`WindowsBackend` in the
universal :class:`ToolWrapper` Protocol so the agent calls it identically
to any other tool.

Approval / safety:
* Read-only actions (``capture``, ``wait``, ``list_apps``) bypass the gate.
* Destructive actions (``click``, ``type``, ``key``, ``set_value``, etc.)
  go through the approval callback unless the target app is in
  ``settings.computer_use_app_allowlist``.
* When no display is available (``backend.is_available()`` False),
  ``execute()`` raises a clear ``RuntimeError`` (constitución #4
  explicit error — never a silent no-op).
* A small Win11-specific block list short-circuits **before** the gate
  for combos that destabilise the host regardless of approval (Win+L
  lock screen, Ctrl+Alt+Del system menu, …).

Approval integration is currently **callback-based**: a host process
registers ``set_approval_callback(callable)`` and the callable returns
one of ``"approve_once" | "always_approve" | "deny"``. When no callback
is registered, destructive actions outside the allowlist raise
``PermissionError``. This matches the deferred state of
``enterprise/governance/approvals/approval.py`` documented in
``docs/f1g-deferred-modularization.md``; once that module lands, this
file wires through it without changing the agent-facing contract.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
)
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action classification
# ---------------------------------------------------------------------------

_SAFE_ACTIONS: frozenset[str] = frozenset({"capture", "wait", "list_apps"})

_DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset({
    "click", "double_click", "right_click", "middle_click",
    "drag", "scroll", "type", "key", "set_value", "focus_app",
})

_ALL_ACTIONS: frozenset[str] = _SAFE_ACTIONS | _DESTRUCTIVE_ACTIONS

# Windows 11 hard-blocked key combos. Refused regardless of approval — they
# either kill the agent's session or the user's host.
_BLOCKED_KEY_COMBOS: tuple[frozenset[str], ...] = (
    frozenset({"win", "l"}),                    # lock screen
    frozenset({"ctrl", "alt", "delete"}),       # secure attention sequence
    frozenset({"alt", "f4"}),                   # close active window blindly
    frozenset({"win", "r"}),                    # Run dialog
    frozenset({"win", "shift", "s"}),           # Snipping tool overlay
)

# Dangerous text patterns banned from `type`.
_BLOCKED_TYPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fqs]\b", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
)


def _canon_keys(keys: str) -> frozenset[str]:
    parts = [p.strip().lower() for p in re.split(r"\s*\+\s*", keys) if p.strip()]
    return frozenset(parts)


# ---------------------------------------------------------------------------
# Approval callback registry (process-wide, thread-safe)
# ---------------------------------------------------------------------------

_approval_lock = threading.Lock()
_approval_callback: Callable[[str, dict[str, Any]], str] | None = None
_session_approvals: set[str] = set()  # actions the user said "always" for


def set_approval_callback(
    cb: Callable[[str, dict[str, Any]], str] | None,
) -> None:
    """Register a callback the tool consults before destructive actions.

    The callback receives ``(action, args)`` and must return one of:
    ``"approve_once" | "always_approve" | "deny"``. Pass ``None`` to
    clear the registration (used by tests).
    """
    global _approval_callback
    with _approval_lock:
        _approval_callback = cb


def reset_session_approvals() -> None:
    """Clear ``always_approve`` decisions for the current session."""
    with _approval_lock:
        _session_approvals.clear()


# ---------------------------------------------------------------------------
# ComputerUseTool — ToolWrapper-compliant entry point
# ---------------------------------------------------------------------------


@dataclass
class ComputerUseTool:
    """Native desktop-control tool. ``ToolWrapper`` Protocol shape."""

    name: str = "computer_use"
    domain: str = "desktop"
    is_external_mcp: bool = False
    requires_auth: bool = False

    # Injected at construction so tests can pass a fake backend.
    backend: ComputerUseBackend | None = None
    app_allowlist: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = False  # mirrors settings.computer_use_enabled

    def __post_init__(self) -> None:
        if self.backend is None:
            from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.windows_backend import (
                WindowsBackend,
            )

            self.backend = WindowsBackend()
        # Allow env to override settings for ad-hoc local enablement.
        env_enabled = os.getenv("VT_COMPUTER_USE_ENABLED", "").lower()
        if env_enabled in ("1", "true", "yes"):
            self.enabled = True

    # --- ToolWrapper surface --------------------------------------------------

    async def healthcheck(self) -> HealthcheckResult:
        if not self.enabled:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=(
                    "computer_use is disabled (settings.computer_use_enabled=False). "
                    "Set VT_COMPUTER_USE_ENABLED=true to opt in."
                ),
            )
        if not self.backend or not self.backend.is_available():
            return HealthcheckResult(
                status="DOWN",
                error=(
                    "WindowsBackend unavailable: missing pyautogui/pygetwindow/mss "
                    "or no display. Install with `pip install ...[browser]`."
                ),
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, Any]
    ) -> dict[str, object]:
        """Universal ToolWrapper entry. ``tool_name`` must equal ``"computer_use"``."""
        if tool_name != "computer_use":
            raise ValueError(
                f"ComputerUseTool: unknown tool_name '{tool_name}' (expected 'computer_use')"
            )
        if not self.enabled:
            raise PermissionError(
                "ComputerUseTool: computer_use is disabled. Opt in via "
                "settings.computer_use_enabled or VT_COMPUTER_USE_ENABLED=true."
            )
        if self.backend is None or not self.backend.is_available():
            raise RuntimeError(
                "ComputerUseTool: no display available. WindowsBackend reports "
                "is_available()=False. Run on a host with a graphical session."
            )
        return self._dispatch(args)

    # --- Dispatch + gates -----------------------------------------------------

    def _dispatch(self, args: dict[str, Any]) -> dict[str, object]:
        action = args.get("action")
        if not isinstance(action, str) or action not in _ALL_ACTIONS:
            raise ValueError(
                f"ComputerUseTool: unknown action '{action}'. "
                f"Supported: {sorted(_ALL_ACTIONS)}"
            )

        # Hard-block: certain combos and text patterns are refused unconditionally.
        if action == "key":
            keys = args.get("keys", "")
            if isinstance(keys, str):
                combo = _canon_keys(keys)
                for blocked in _BLOCKED_KEY_COMBOS:
                    if blocked <= combo:
                        raise PermissionError(
                            f"ComputerUseTool: key combo '{keys}' is hard-blocked "
                            f"(would trigger system action)"
                        )
        if action == "type":
            text = args.get("text", "")
            if isinstance(text, str):
                for pattern in _BLOCKED_TYPE_PATTERNS:
                    if pattern.search(text):
                        raise PermissionError(
                            "ComputerUseTool: typed text matches a hard-blocked "
                            f"pattern ({pattern.pattern!r})"
                        )

        # Approval gate for destructive actions outside the allowlist.
        if action in _DESTRUCTIVE_ACTIONS and not self._is_allowlisted(args):
            decision = self._request_approval(action, args)
            if decision == "deny":
                raise PermissionError(
                    f"ComputerUseTool: action '{action}' denied by approval gate"
                )

        return self._invoke_backend(action, args)

    def _is_allowlisted(self, args: dict[str, Any]) -> bool:
        target = args.get("app")
        if not isinstance(target, str) or not target.strip():
            return False
        target_lower = target.lower()
        return any(allow.lower() in target_lower for allow in self.app_allowlist)

    def _request_approval(self, action: str, args: dict[str, Any]) -> str:
        """Consult the registered callback. Defaults to ``deny`` when none."""
        # Session-cached "always_approve" short-circuits.
        with _approval_lock:
            if action in _session_approvals:
                return "approve_once"
            cb = _approval_callback
        if cb is None:
            logger.warning(
                "ComputerUseTool: action '%s' denied — no approval callback registered",
                action,
            )
            return "deny"
        decision = cb(action, args)
        if decision == "always_approve":
            with _approval_lock:
                _session_approvals.add(action)
            return "approve_once"
        if decision in ("approve_once", "deny"):
            return decision
        logger.warning(
            "ComputerUseTool: approval callback returned unknown decision %r — denying",
            decision,
        )
        return "deny"

    # --- Backend invocation --------------------------------------------------

    def _invoke_backend(self, action: str, args: dict[str, Any]) -> dict[str, object]:
        assert self.backend is not None
        be = self.backend

        if action == "capture":
            cap = be.capture(
                mode=str(args.get("mode") or "som"),
                app=args.get("app"),
            )
            return _capture_to_dict(cap)
        if action == "wait":
            seconds = float(args.get("seconds") or 1.0)
            return _action_to_dict(be.wait(seconds))
        if action == "list_apps":
            return {"action": "list_apps", "apps": be.list_apps()}

        if action in ("click", "double_click", "right_click", "middle_click"):
            button = "left"
            click_count = 1
            if action == "double_click":
                click_count = 2
            elif action == "right_click":
                button = "right"
            elif action == "middle_click":
                button = "middle"
            x, y = _coord(args.get("coordinate"))
            res = be.click(
                element=_int_or_none(args.get("element")),
                x=x, y=y, button=button, click_count=click_count,
                modifiers=_str_list(args.get("modifiers")),
            )
            return _action_to_dict(res)

        if action == "drag":
            fx, fy = _coord(args.get("from_coordinate"))
            tx, ty = _coord(args.get("to_coordinate"))
            res = be.drag(
                from_element=_int_or_none(args.get("from_element")),
                to_element=_int_or_none(args.get("to_element")),
                from_xy=(fx, fy) if fx is not None and fy is not None else None,
                to_xy=(tx, ty) if tx is not None and ty is not None else None,
                button=str(args.get("button") or "left"),
                modifiers=_str_list(args.get("modifiers")),
            )
            return _action_to_dict(res)

        if action == "scroll":
            x, y = _coord(args.get("coordinate"))
            res = be.scroll(
                direction=str(args.get("direction") or "down"),
                amount=int(args.get("amount") or 3),
                element=_int_or_none(args.get("element")),
                x=x, y=y, modifiers=_str_list(args.get("modifiers")),
            )
            return _action_to_dict(res)

        if action == "type":
            res = be.type_text(str(args.get("text") or ""))
            return _action_to_dict(res)
        if action == "key":
            res = be.key(str(args.get("keys") or ""))
            return _action_to_dict(res)

        if action == "focus_app":
            res = be.focus_app(
                app=str(args.get("app") or ""),
                raise_window=bool(args.get("raise_window") or False),
            )
            return _action_to_dict(res)
        if action == "set_value":
            res = be.set_value(
                value=str(args.get("value") or ""),
                element=_int_or_none(args.get("element")),
            )
            return _action_to_dict(res)

        # Should be unreachable thanks to the upfront ALL_ACTIONS check.
        raise ValueError(f"ComputerUseTool: unhandled action {action!r}")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _capture_to_dict(cap: CaptureResult) -> dict[str, object]:
    return {
        "action": "capture",
        "mode": cap.mode,
        "width": cap.width,
        "height": cap.height,
        "png_b64": cap.png_b64,
        "elements": [
            {
                "index": e.index,
                "role": e.role,
                "label": e.label,
                "bounds": list(e.bounds),
                "app": e.app,
            }
            for e in cap.elements
        ],
        "app": cap.app,
        "window_title": cap.window_title,
    }


def _action_to_dict(res: ActionResult) -> dict[str, object]:
    out: dict[str, object] = {
        "action": res.action,
        "ok": res.ok,
        "message": res.message,
    }
    if res.capture is not None:
        out["capture"] = _capture_to_dict(res.capture)
    if res.meta:
        out["meta"] = res.meta
    return out


def _coord(value: object) -> tuple[int | None, int | None]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None, None
    return None, None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _str_list(value: object) -> list[str] | None:
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, str)]
    return None
