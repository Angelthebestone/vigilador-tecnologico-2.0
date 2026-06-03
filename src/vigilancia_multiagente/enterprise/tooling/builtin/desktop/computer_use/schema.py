"""Schema for the ``computer_use`` tool.

# Adapted from Hermes Agent — Original file: tools/computer_use/schema.py — License: MIT

Spec 021 F3a.B / FR-029. Model-agnostic: any tool-calling model can drive
this. Vision-capable models should prefer ``capture(mode='som')`` then
``click(element=N)`` — much more reliable than pixel coordinates. Pixel
coordinates remain supported for models trained on them.

Vigilador adaptation vs. upstream Hermes (macOS-first):
* Description / examples generalised away from "macOS only".
* ``modifiers`` enum reduced to the Win11 set: ``["ctrl", "shift", "alt", "win"]``.
  ``cmd``/``option``/``fn`` removed (no native Windows equivalent that doesn't
  conflict with the existing four).
* Key combo example switched to ``"ctrl+s"`` instead of ``"cmd+s"``.
"""

from __future__ import annotations

from typing import Any

COMPUTER_USE_SCHEMA: dict[str, Any] = {
    "name": "computer_use",
    "description": (
        "Drive the desktop in the background — screenshots, mouse, "
        "keyboard, scroll, drag — without stealing the user's cursor or "
        "keyboard focus. Preferred workflow: call with action='capture' "
        "(mode='som' returns numbered element overlays), then click by "
        "`element` index for reliability. Pixel coordinates are supported "
        "for models trained on them. Works on any visible window. "
        "Windows 11 host required; pyautogui + pygetwindow + mss must be "
        "installed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "capture",
                    "click",
                    "double_click",
                    "right_click",
                    "middle_click",
                    "drag",
                    "scroll",
                    "type",
                    "key",
                    "set_value",
                    "wait",
                    "list_apps",
                    "focus_app",
                ],
                "description": (
                    "Which action to perform. `capture`, `wait`, and "
                    "`list_apps` are read-only. All other actions go "
                    "through the approval gate unless the target app is "
                    "in the configured allowlist."
                ),
            },
            # capture
            "mode": {
                "type": "string",
                "enum": ["som", "vision", "ax"],
                "description": (
                    "Capture mode. `som` (default) is a screenshot with "
                    "numbered overlays on every interactable element plus "
                    "the accessibility tree — best for vision models, "
                    "lets you click by element index. `vision` is a plain "
                    "screenshot. `ax` returns the accessibility tree only."
                ),
            },
            "app": {
                "type": "string",
                "description": (
                    "Optional. Limit capture/action to a specific app by "
                    "process or window-title substring. If omitted, "
                    "operates on the foreground window or full screen."
                ),
            },
            "max_elements": {
                "type": "integer",
                "description": (
                    "Optional cap on the AX `elements` array returned by "
                    "`action='capture'`. Default 100, hard maximum 1000."
                ),
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
            },
            # targeting
            "element": {
                "type": "integer",
                "description": (
                    "The 1-based SOM index returned by the last "
                    "`capture(mode='som')` call. Strongly preferred over "
                    "raw coordinates."
                ),
            },
            "coordinate": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "description": (
                    "Pixel coordinates [x, y] in logical screen space. "
                    "Only use this if no element index is available."
                ),
            },
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "description": "Mouse button. Defaults to left.",
            },
            "modifiers": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["ctrl", "shift", "alt", "win"],
                },
                "description": "Modifier keys held during the action.",
            },
            # drag
            "from_element": {
                "type": "integer",
                "description": "Source element index (drag).",
            },
            "to_element": {
                "type": "integer",
                "description": "Target element index (drag).",
            },
            "from_coordinate": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Source [x,y] (drag; use when no element available).",
            },
            "to_coordinate": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Target [x,y] (drag; use when no element available).",
            },
            # scroll
            "direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
                "description": "Scroll direction.",
            },
            "amount": {
                "type": "integer",
                "description": "Scroll wheel ticks. Default 3.",
            },
            # set_value
            "value": {
                "type": "string",
                "description": (
                    "For action='set_value': the value to set on the element. "
                    "For combo boxes / dropdowns, pass the option's display "
                    "label (e.g. 'Blue'). For sliders and other "
                    "value-settable elements, pass the numeric or string value."
                ),
            },
            # type / key / wait
            "text": {
                "type": "string",
                "description": "Text to type (respects the current layout).",
            },
            "keys": {
                "type": "string",
                "description": (
                    "Key combo, e.g. 'ctrl+s', 'ctrl+alt+t', 'return', "
                    "'escape', 'tab'. Use '+' to combine."
                ),
            },
            "seconds": {
                "type": "number",
                "description": "Seconds to wait. Max 30.",
            },
            # focus_app
            "raise_window": {
                "type": "boolean",
                "description": (
                    "Only for action='focus_app'. If true, brings the "
                    "window to front (DISRUPTS the user). Default false "
                    "— input is routed to the app without raising."
                ),
            },
            "capture_after": {
                "type": "boolean",
                "description": (
                    "If true, take a follow-up capture after the action "
                    "and include it in the response."
                ),
            },
        },
        "required": ["action"],
    },
}


def get_computer_use_schema() -> dict[str, Any]:
    """Return the OpenAI function-calling schema."""
    return COMPUTER_USE_SCHEMA
