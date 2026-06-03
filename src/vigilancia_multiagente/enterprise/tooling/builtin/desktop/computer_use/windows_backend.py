"""Windows 11 backend for the ``computer_use`` tool.

Spec 021 F3a.B / FR-029. Implements :class:`ComputerUseBackend` using
three optional Python deps:

* ``pyautogui`` — mouse, keyboard, screen size.
* ``pygetwindow`` — enumerate / focus windows.
* ``mss``       — fast screen capture (single-shot, no clipboard side-effect).

All three are declared in ``pyproject.toml`` under the optional
``[browser]`` group already (cohabits with playwright); installing them
is opt-in. ``is_available()`` returns False when any of them is missing
or the host has no display, so the gate path raises a clear error before
``execute()`` runs (constitución #4).

This file does NOT import the deps at module load — they are imported
inside the methods that need them so ``healthcheck`` can answer
without paying the import cost.
"""

from __future__ import annotations

import logging
from typing import Any

from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
    UIElement,
)

logger = logging.getLogger(__name__)


class WindowsBackend(ComputerUseBackend):
    """``pyautogui`` + ``pygetwindow`` + ``mss`` backend (Windows-first)."""

    def __init__(self) -> None:
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def is_available(self) -> bool:
        """Importability + display check."""
        try:
            import mss  # noqa: F401
            import pyautogui
            import pygetwindow  # noqa: F401
        except ImportError:
            return False
        # Headless detection: pyautogui.size() raises on hosts without display.
        try:
            import pyautogui

            pyautogui.size()
        except Exception:
            return False
        return True

    # --- Capture --------------------------------------------------------------

    def capture(self, mode: str = "som", app: str | None = None) -> CaptureResult:
        self._require_deps()
        import base64
        import io

        import mss
        import mss.tools
        import pyautogui

        if mode not in ("som", "vision", "ax"):
            raise ValueError(
                f"WindowsBackend.capture: unknown mode '{mode}' "
                "(supported: som, vision, ax)"
            )

        width, height = pyautogui.size()
        png_b64: str | None = None
        png_bytes_len = 0

        if mode in ("som", "vision"):
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[1])  # primary monitor
                png_bytes = mss.tools.to_png(shot.rgb, shot.size)
                png_bytes_len = len(png_bytes)
                buf = io.BytesIO(png_bytes)
                png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                width, height = shot.size

        # Element enumeration — Win11 doesn't have a clean AX tree without
        # pywinauto/uia. For the MVP we enumerate visible top-level windows
        # via pygetwindow as coarse-grained "elements". Vision callers can
        # still drive by pixel coordinates; SOM overlay is the next step.
        elements: list[UIElement] = []
        if mode in ("som", "ax"):
            elements = self._enumerate_windows_as_elements(filter_app=app)

        return CaptureResult(
            mode=mode,
            width=width,
            height=height,
            png_b64=png_b64,
            elements=elements,
            app=app or "",
            window_title=elements[0].label if elements else "",
            png_bytes_len=png_bytes_len,
        )

    def _enumerate_windows_as_elements(
        self, filter_app: str | None
    ) -> list[UIElement]:
        import pygetwindow

        out: list[UIElement] = []
        for idx, win in enumerate(pygetwindow.getAllWindows(), start=1):
            title = (getattr(win, "title", "") or "").strip()
            if not title:
                continue
            if filter_app and filter_app.lower() not in title.lower():
                continue
            try:
                bounds = (int(win.left), int(win.top), int(win.width), int(win.height))
            except (AttributeError, TypeError, ValueError):
                bounds = (0, 0, 0, 0)
            out.append(
                UIElement(
                    index=idx,
                    role="Window",
                    label=title,
                    bounds=bounds,
                    app=title.split(" - ")[-1] if " - " in title else title,
                )
            )
        return out

    # --- Pointer actions -----------------------------------------------------

    def click(
        self,
        *,
        element: int | None = None,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        click_count: int = 1,
        modifiers: list[str] | None = None,
    ) -> ActionResult:
        self._require_deps()
        import pyautogui

        target_xy = self._resolve_xy(element, x, y)
        if target_xy is None:
            return ActionResult(
                ok=False, action="click",
                message="missing element or [x,y] coordinate",
            )
        with self._held(modifiers):
            pyautogui.click(target_xy[0], target_xy[1], clicks=click_count, button=button)
        return ActionResult(
            ok=True, action="click",
            message=f"{button}-click x{click_count} at {target_xy}",
        )

    def drag(
        self,
        *,
        from_element: int | None = None,
        to_element: int | None = None,
        from_xy: tuple[int, int] | None = None,
        to_xy: tuple[int, int] | None = None,
        button: str = "left",
        modifiers: list[str] | None = None,
    ) -> ActionResult:
        self._require_deps()
        import pyautogui

        src = self._resolve_xy(from_element, *(from_xy or (None, None)))
        dst = self._resolve_xy(to_element, *(to_xy or (None, None)))
        if src is None or dst is None:
            return ActionResult(
                ok=False, action="drag",
                message="drag requires both source and destination",
            )
        with self._held(modifiers):
            pyautogui.moveTo(*src)
            pyautogui.dragTo(dst[0], dst[1], button=button)
        return ActionResult(
            ok=True, action="drag", message=f"drag {src} -> {dst}",
        )

    def scroll(
        self,
        *,
        direction: str,
        amount: int = 3,
        element: int | None = None,
        x: int | None = None,
        y: int | None = None,
        modifiers: list[str] | None = None,
    ) -> ActionResult:
        self._require_deps()
        import pyautogui

        if direction not in ("up", "down", "left", "right"):
            raise ValueError(f"scroll: invalid direction {direction!r}")
        target = self._resolve_xy(element, x, y)
        if target is not None:
            pyautogui.moveTo(*target)
        amt = max(1, amount)
        with self._held(modifiers):
            if direction == "up":
                pyautogui.scroll(amt)
            elif direction == "down":
                pyautogui.scroll(-amt)
            elif direction == "left":
                pyautogui.hscroll(-amt)  # type: ignore[attr-defined]
            else:
                pyautogui.hscroll(amt)  # type: ignore[attr-defined]
        return ActionResult(
            ok=True, action="scroll",
            message=f"scroll {direction} x{amt}",
        )

    # --- Keyboard ------------------------------------------------------------

    def type_text(self, text: str) -> ActionResult:
        self._require_deps()
        import pyautogui

        pyautogui.typewrite(text, interval=0.0)
        return ActionResult(
            ok=True, action="type",
            message=f"typed {len(text)} chars",
        )

    def key(self, keys: str) -> ActionResult:
        self._require_deps()
        import pyautogui

        parts = [p.strip() for p in keys.split("+") if p.strip()]
        if not parts:
            raise ValueError("key: empty key combo")
        if len(parts) == 1:
            pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)
        return ActionResult(ok=True, action="key", message=f"key '{keys}'")

    # --- Introspection -------------------------------------------------------

    def list_apps(self) -> list[dict[str, Any]]:
        self._require_deps()
        import pygetwindow

        seen: dict[str, dict[str, Any]] = {}
        for win in pygetwindow.getAllWindows():
            title = (getattr(win, "title", "") or "").strip()
            if not title:
                continue
            app = title.split(" - ")[-1] if " - " in title else title
            entry = seen.setdefault(app, {"app": app, "windows": 0})
            entry["windows"] += 1
        return list(seen.values())

    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        self._require_deps()
        import pygetwindow

        matches = [
            w for w in pygetwindow.getAllWindows()
            if app.lower() in (getattr(w, "title", "") or "").lower()
        ]
        if not matches:
            return ActionResult(ok=False, action="focus_app", message=f"no window for '{app}'")
        target = matches[0]
        try:
            if raise_window:
                target.activate()
            else:
                # pygetwindow doesn't have a "focus without raise" — closest
                # we can do is restore (no-op if already restored).
                target.restore() if getattr(target, "isMinimized", False) else None
        except Exception as exc:
            return ActionResult(
                ok=False, action="focus_app",
                message=f"focus failed: {exc}",
            )
        return ActionResult(ok=True, action="focus_app", message=f"focused '{app}'")

    # --- Native-value mutation -----------------------------------------------

    def set_value(self, value: str, element: int | None = None) -> ActionResult:
        # Win11 set_value over UIA requires pywinauto. Out of MVP scope —
        # constitución #4: explicit not-implemented, not a silent no-op.
        return ActionResult(
            ok=False, action="set_value",
            message=(
                "set_value is not implemented in the Win11 backend yet "
                "(needs pywinauto / UIA). Use click + type as a workaround."
            ),
            meta={"element": element, "value": value},
        )

    # --- Helpers -------------------------------------------------------------

    def _require_deps(self) -> None:
        if not self.is_available():
            raise RuntimeError(
                "WindowsBackend: required dependencies missing. Install "
                "with `pip install vigilador-tecnologico[browser]` "
                "(pyautogui + pygetwindow + mss)."
            )

    def _resolve_xy(
        self, element: int | None, x: int | None, y: int | None
    ) -> tuple[int, int] | None:
        if element is not None:
            # Element-based clicks need a prior capture; here we treat the
            # element index as a hint that the caller already centred on a
            # known window. A future revision wires this through the SOM
            # cache. For MVP: prefer explicit x/y when both are missing.
            return None
        if x is None or y is None:
            return None
        return int(x), int(y)

    def _held(self, modifiers: list[str] | None):
        """Context manager that holds modifier keys for the duration."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            if not modifiers:
                yield
                return
            import pyautogui

            for mod in modifiers:
                pyautogui.keyDown(mod)
            try:
                yield
            finally:
                for mod in reversed(modifiers):
                    pyautogui.keyUp(mod)

        return _ctx()
