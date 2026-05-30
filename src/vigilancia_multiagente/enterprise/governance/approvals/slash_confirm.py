"""Generic slash-command confirmation primitive (gateway-side).

Adapted from Hermes Agent — Original file: ``tools/slash_confirm.py``
License: MIT (see ``documentation/hermes agent/hermes-agent/LICENSE``).

Spec 021 FR-025: F1 governance/approvals. Slash commands with non-destructive
but expensive side effects (e.g. cache invalidation) route through this module
to surface confirmation prompts to the user.

**Deviation from upstream**: the ``resolve_sync_compat`` helper in Hermes
depends on ``agent.async_utils.safe_schedule_threadsafe`` which is part of
the Hermes runtime, not portable. Callers that need sync-compat scheduling
should use ``asyncio.run_coroutine_threadsafe`` directly with their own
event-loop reference.

Two delivery paths:

  1. Button UI — adapters render inline buttons (Approve Once / Always /
     Cancel). The button callback calls ``resolve(session_key, confirm_id,
     choice)``.

  2. Text fallback — adapters without button UIs send a plain text prompt.
     Users reply with ``/approve``, ``/always``, or ``/cancel``; the gateway
     intercepts those replies and calls ``resolve()`` directly.

State is stored module-level (like ``approval``) so platform adapters can
resolve callbacks without needing a backreference to the gateway runner.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

# Pending confirmations keyed by gateway session_key.
_pending: dict[str, dict[str, Any]] = {}
_lock = threading.RLock()

DEFAULT_TIMEOUT_SECONDS = 300


def register(
    session_key: str,
    confirm_id: str,
    command: str,
    handler: Callable[[str], Awaitable[str | None]],
) -> None:
    """Register a pending slash-command confirmation.

    Overwrites any prior pending confirm for the same ``session_key`` — the
    user invoking a new confirmable command supersedes the stale one.
    """
    with _lock:
        _pending[session_key] = {
            "confirm_id": confirm_id,
            "command": command,
            "handler": handler,
            "created_at": time.time(),
        }


def get_pending(session_key: str) -> dict[str, Any] | None:
    """Return the pending confirm dict for a session, or None."""
    with _lock:
        entry = _pending.get(session_key)
        return dict(entry) if entry else None


def clear(session_key: str) -> None:
    """Drop the pending confirm for ``session_key`` without running it."""
    with _lock:
        _pending.pop(session_key, None)


def clear_if_stale(session_key: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bool:
    """Drop the pending confirm if older than ``timeout`` seconds.

    Returns True if an entry was dropped.
    """
    with _lock:
        entry = _pending.get(session_key)
        if not entry:
            return False
        if time.time() - float(entry.get("created_at", 0) or 0) > timeout:
            _pending.pop(session_key, None)
            return True
        return False


async def resolve(
    session_key: str,
    confirm_id: str,
    choice: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str | None:
    """Resolve a pending confirm.

    ``choice`` must be one of ``"once"``, ``"always"``, or ``"cancel"``.
    Returns the handler's output string (to be sent as a follow-up
    message), or ``None`` if the confirm was stale, already resolved, or
    the confirm_id doesn't match.
    """
    with _lock:
        entry = _pending.get(session_key)
        if not entry:
            return None
        if entry.get("confirm_id") != confirm_id:
            # Stale confirm_id — superseded by a newer prompt on the same session.
            return None
        # Pop before running the handler to prevent duplicate callbacks
        # (e.g. button double-click) from running it twice.
        _pending.pop(session_key, None)
        if time.time() - float(entry.get("created_at", 0) or 0) > timeout:
            return None
        handler = entry.get("handler")
        command = entry.get("command", "?")

    if not handler:
        return None
    # Handler errors are caught + transformed (constitucion #4: explicit
    # error transformation, not silent swallow). The user-facing message
    # is what the platform adapter will surface.
    try:
        result = await handler(choice)
    except Exception as exc:
        logger.error(
            "Slash-confirm handler for /%s raised: %s",
            command,
            exc,
            exc_info=True,
        )
        return f"Error handling confirmation: {exc}"
    return result if isinstance(result, str) else None
