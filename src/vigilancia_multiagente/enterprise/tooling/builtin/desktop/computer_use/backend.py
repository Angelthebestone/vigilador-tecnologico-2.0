"""Abstract backend interface for the computer-use tool.

# Adapted from Hermes Agent — Original file: tools/computer_use/backend.py — License: MIT

Spec 021 F3a.B / FR-029. Any concrete implementation (Windows pyautogui
backend, future Linux/macOS, no-op for tests) must implement the methods
declared here. All methods synchronous; async coordination is the
responsibility of the wrapper layer (``tool.py``).

Vigilador adaptation vs. upstream:
* Docstring references generalised from "macOS-only" to "any OS"; the
  port concentrates the OS-specific bits in ``windows_backend.py``.
* ``UIElement.role`` keeps the ``AXRole`` naming for cross-port
  consistency; the Win11 backend maps Win32 / UIA roles into the same
  vocabulary at capture time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UIElement:
    """One interactable element on the current screen."""

    index: int                       # 1-based SOM index
    role: str                        # accessibility role (Button, Edit, ...)
    label: str = ""                  # title / description / value snippet
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h (logical px)
    app: str = ""                    # owning process name
    pid: int = 0                     # owning process PID
    window_id: int = 0               # platform-specific window id
    attributes: dict[str, Any] = field(default_factory=dict)

    def center(self) -> tuple[int, int]:
        x, y, w, h = self.bounds
        return x + w // 2, y + h // 2


@dataclass
class CaptureResult:
    """Result of a screen capture call.

    At least one of png_b64 / elements is populated depending on capture mode:
      * ``mode="vision"`` → png_b64 only
      * ``mode="ax"``     → elements only
      * ``mode="som"``    → both (default): PNG already has numbered overlays
        drawn by the backend, and ``elements`` holds the matching index →
        element mapping.
    """

    mode: str
    width: int                      # screenshot width (logical px)
    height: int
    png_b64: str | None = None
    elements: list[UIElement] = field(default_factory=list)
    app: str = ""
    window_title: str = ""
    png_bytes_len: int = 0


@dataclass
class ActionResult:
    """Result of any action (click / type / scroll / drag / key / wait)."""

    ok: bool
    action: str
    message: str = ""
    capture: CaptureResult | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class ComputerUseBackend(ABC):
    """Lifecycle: ``start()`` before first use, ``stop()`` at shutdown."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def is_available(self) -> bool:
        """True if the backend can run on this host (display present, deps installed)."""

    # --- Capture --------------------------------------------------------------
    @abstractmethod
    def capture(self, mode: str = "som", app: str | None = None) -> CaptureResult: ...

    # --- Pointer actions -----------------------------------------------------
    @abstractmethod
    def click(
        self,
        *,
        element: int | None = None,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        click_count: int = 1,
        modifiers: list[str] | None = None,
    ) -> ActionResult: ...

    @abstractmethod
    def drag(
        self,
        *,
        from_element: int | None = None,
        to_element: int | None = None,
        from_xy: tuple[int, int] | None = None,
        to_xy: tuple[int, int] | None = None,
        button: str = "left",
        modifiers: list[str] | None = None,
    ) -> ActionResult: ...

    @abstractmethod
    def scroll(
        self,
        *,
        direction: str,
        amount: int = 3,
        element: int | None = None,
        x: int | None = None,
        y: int | None = None,
        modifiers: list[str] | None = None,
    ) -> ActionResult: ...

    # --- Keyboard ------------------------------------------------------------
    @abstractmethod
    def type_text(self, text: str) -> ActionResult: ...

    @abstractmethod
    def key(self, keys: str) -> ActionResult:
        """Send a key combo, e.g. ``"ctrl+s"``, ``"ctrl+alt+t"``, ``"return"``."""

    # --- Introspection -------------------------------------------------------
    @abstractmethod
    def list_apps(self) -> list[dict[str, Any]]:
        """Return running apps with names, PIDs, window counts."""

    @abstractmethod
    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        """Route input to ``app`` (by name). If ``raise_window`` is False,
        focus without bringing the window to front."""

    # --- Native-value mutation -----------------------------------------------
    @abstractmethod
    def set_value(self, value: str, element: int | None = None) -> ActionResult:
        """Set a native value on an element (e.g. selection on a combo box).

        ``element`` is the 1-based SOM index returned by a prior capture call.
        """

    # --- Timing --------------------------------------------------------------
    def wait(self, seconds: float) -> ActionResult:
        """Default implementation — bounded ``time.sleep``."""
        import time

        time.sleep(max(0.0, min(seconds, 30.0)))
        return ActionResult(ok=True, action="wait", message=f"waited {seconds:.2f}s")
