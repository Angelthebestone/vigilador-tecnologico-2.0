"""F3a.B tests — ComputerUseTool (Spec 021 FR-029/030).

Six scenarios per T085:

1. ToolWrapper protocol surface (name, domain, healthcheck, execute).
2. ``capture`` returns a screenshot result via the backend (read-only path).
3. ``click`` applies via the backend when allowlisted.
4. ``type`` applies modifiers when honored.
5. No-display host (``backend.is_available()=False``) → explicit error.
6. Action against an app outside the allowlist → approval-gate denial
   when no callback registered.

All tests use a fake backend so no real desktop is required.
"""

from __future__ import annotations

from typing import Any

import pytest

from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
)
from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.tool import (
    ComputerUseTool,
    reset_session_approvals,
    set_approval_callback,
)

# ---------------------------------------------------------------------------
# Fake backend
# ---------------------------------------------------------------------------


class _FakeBackend(ComputerUseBackend):
    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.last_call: tuple[str, dict[str, Any]] | None = None

    def start(self) -> None: ...
    def stop(self) -> None: ...

    def is_available(self) -> bool:
        return self._available

    def capture(self, mode: str = "som", app: str | None = None) -> CaptureResult:
        self.last_call = ("capture", {"mode": mode, "app": app})
        return CaptureResult(mode=mode, width=1920, height=1080, png_b64="b64")

    def click(self, **kwargs):
        self.last_call = ("click", kwargs)
        return ActionResult(ok=True, action="click", message="ok")

    def drag(self, **kwargs):
        self.last_call = ("drag", kwargs)
        return ActionResult(ok=True, action="drag", message="ok")

    def scroll(self, **kwargs):
        self.last_call = ("scroll", kwargs)
        return ActionResult(ok=True, action="scroll", message="ok")

    def type_text(self, text: str) -> ActionResult:
        self.last_call = ("type_text", {"text": text})
        return ActionResult(ok=True, action="type", message="ok")

    def key(self, keys: str) -> ActionResult:
        self.last_call = ("key", {"keys": keys})
        return ActionResult(ok=True, action="key", message="ok")

    def list_apps(self) -> list[dict[str, Any]]:
        self.last_call = ("list_apps", {})
        return [{"app": "Notepad", "windows": 1}]

    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        self.last_call = ("focus_app", {"app": app, "raise_window": raise_window})
        return ActionResult(ok=True, action="focus_app", message="ok")

    def set_value(self, value: str, element: int | None = None) -> ActionResult:
        self.last_call = ("set_value", {"value": value, "element": element})
        return ActionResult(ok=True, action="set_value", message="ok")


@pytest.fixture(autouse=True)
def _clean_callback_state():
    """Per-test reset so callbacks don't leak across tests."""
    set_approval_callback(None)
    reset_session_approvals()
    yield
    set_approval_callback(None)
    reset_session_approvals()


# ---------------------------------------------------------------------------
# 1. Protocol surface
# ---------------------------------------------------------------------------


def test_tool_wrapper_protocol_surface():
    tool = ComputerUseTool(backend=_FakeBackend(), enabled=True)
    assert tool.name == "computer_use"
    assert tool.domain == "desktop"
    assert tool.is_external_mcp is False
    assert tool.requires_auth is False
    assert callable(tool.healthcheck)
    assert callable(tool.execute)


# ---------------------------------------------------------------------------
# 2. capture (read-only — no gate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capture_returns_screenshot_payload():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True)
    result = await tool.execute("computer_use", {"action": "capture", "mode": "som"})
    assert result["mode"] == "som"
    assert result["png_b64"] == "b64"
    assert fake.last_call == ("capture", {"mode": "som", "app": None})


# ---------------------------------------------------------------------------
# 3. click on allowlisted app — bypasses gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_click_allowlisted_app_passes_gate():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True, app_allowlist=("Notepad",))
    result = await tool.execute(
        "computer_use",
        {"action": "click", "app": "Notepad", "coordinate": [100, 200]},
    )
    assert result["ok"] is True
    assert fake.last_call is not None
    assert fake.last_call[0] == "click"


# ---------------------------------------------------------------------------
# 4. modifiers + type respect the args
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_type_applies_text_after_callback_approval():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True)

    def _approve(action: str, args: dict[str, Any]) -> str:
        return "approve_once"

    set_approval_callback(_approve)
    result = await tool.execute("computer_use", {"action": "type", "text": "hello"})
    assert result["ok"] is True
    assert fake.last_call == ("type_text", {"text": "hello"})


# ---------------------------------------------------------------------------
# 5. No display → explicit error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_display_raises_explicit_error():
    fake = _FakeBackend(available=False)
    tool = ComputerUseTool(backend=fake, enabled=True)
    with pytest.raises(RuntimeError, match="no display available"):
        await tool.execute("computer_use", {"action": "capture"})


@pytest.mark.asyncio
async def test_disabled_tool_raises_explicit_error():
    """When the feature flag is off, every action denies."""
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=False)
    with pytest.raises(PermissionError, match="disabled"):
        await tool.execute("computer_use", {"action": "capture"})


# ---------------------------------------------------------------------------
# 6. Action outside allowlist + no callback → denied
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_destructive_outside_allowlist_no_callback_denies():
    fake = _FakeBackend()
    tool = ComputerUseTool(
        backend=fake,
        enabled=True,
        app_allowlist=("Notepad",),
    )
    set_approval_callback(None)  # no callback registered
    with pytest.raises(PermissionError, match="denied by approval gate"):
        await tool.execute(
            "computer_use",
            {"action": "click", "app": "ProductionDB", "coordinate": [10, 20]},
        )


@pytest.mark.asyncio
async def test_callback_deny_is_honored():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True)

    def _deny(action: str, args: dict[str, Any]) -> str:
        return "deny"

    set_approval_callback(_deny)
    with pytest.raises(PermissionError, match="denied by approval gate"):
        await tool.execute("computer_use", {"action": "click", "coordinate": [10, 20]})


# ---------------------------------------------------------------------------
# Hard-blocked combos / patterns are unconditionally refused.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_blocked_key_combo_refused_even_when_allowlisted():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True, app_allowlist=("Notepad",))
    with pytest.raises(PermissionError, match="hard-blocked"):
        await tool.execute(
            "computer_use",
            {"action": "key", "keys": "win+l", "app": "Notepad"},
        )


@pytest.mark.asyncio
async def test_hard_blocked_type_pattern_refused():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True, app_allowlist=("Notepad",))
    with pytest.raises(PermissionError, match="hard-blocked pattern"):
        await tool.execute(
            "computer_use",
            {"action": "type", "text": "rm -rf /important/data", "app": "Notepad"},
        )


# ---------------------------------------------------------------------------
# Healthcheck states
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcheck_unconfigured_when_disabled():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=False)
    h = await tool.healthcheck()
    assert h.status == "UNCONFIGURED"


@pytest.mark.asyncio
async def test_healthcheck_down_when_no_display():
    fake = _FakeBackend(available=False)
    tool = ComputerUseTool(backend=fake, enabled=True)
    h = await tool.healthcheck()
    assert h.status == "DOWN"


@pytest.mark.asyncio
async def test_healthcheck_up_when_enabled_and_available():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True)
    h = await tool.healthcheck()
    assert h.status == "UP"


# ---------------------------------------------------------------------------
# Schema sanity check
# ---------------------------------------------------------------------------


def test_schema_describes_windows_modifier_set():
    from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.schema import (
        get_computer_use_schema,
    )

    schema = get_computer_use_schema()
    mods = schema["parameters"]["properties"]["modifiers"]["items"]["enum"]
    # No macOS-only modifiers.
    assert "cmd" not in mods
    assert "option" not in mods
    # All four Win11 modifiers present.
    assert set(mods) == {"ctrl", "shift", "alt", "win"}


# ---------------------------------------------------------------------------
# Unknown action surfaces explicitly.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_action_raises_value_error():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True)
    with pytest.raises(ValueError, match="unknown action"):
        await tool.execute("computer_use", {"action": "self_destruct"})


@pytest.mark.asyncio
async def test_unknown_tool_name_raises_value_error():
    fake = _FakeBackend()
    tool = ComputerUseTool(backend=fake, enabled=True)
    with pytest.raises(ValueError, match="unknown tool_name"):
        await tool.execute("not_computer_use", {"action": "capture"})
