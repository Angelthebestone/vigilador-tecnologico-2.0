"""Configurable tool-output truncation limits.

Adapted from Hermes Agent — Original file: ``tools/tool_output_limits.py``
License: MIT (see ``documentation/hermes agent/hermes-agent/LICENSE``).

Spec 021 FR-025: governance F1 / tooling base. The Hermes upstream read its
config via ``hermes_cli.config.load_config()``; this port exposes the same
public API (``get_tool_output_limits``, ``get_max_*``) and keeps the
defaults identical, so behaviour is preserved. Future revisions may surface
these as VT settings — for now they stay at the Hermes defaults.

Hardcoded defaults — pre-existing values from Hermes (behaviour-preserving):

* ``MAX_BYTES = 50_000``        — terminal output cap (chars)
* ``MAX_LINES = 2000``          — read_file pagination + truncation cap
* ``MAX_LINE_LENGTH = 2000``    — per-line cap before ``... [truncated]``
"""

from __future__ import annotations

# Hardcoded defaults — these match the pre-existing values, so adopting
# this module is behaviour-preserving for callers in the 2.0 codebase.
DEFAULT_MAX_BYTES = 50_000
DEFAULT_MAX_LINES = 2000
DEFAULT_MAX_LINE_LENGTH = 2000


def _coerce_positive_int(value: object, default: int) -> int:
    """Return ``value`` as a positive int, or ``default`` on any issue.

    Defensive coercion at the API boundary is constitutionally allowed
    (#4 — error transformation with context); the caller never receives
    a non-positive int.
    """
    if not isinstance(value, (int, str, float)) or isinstance(value, bool):
        return default
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return default
    if iv <= 0:
        return default
    return iv


def get_tool_output_limits() -> dict[str, int]:
    """Return resolved tool-output limits.

    Keys: ``max_bytes``, ``max_lines``, ``max_line_length``. The current
    revision returns the Hermes defaults; a future task may surface these
    as VT settings without changing the public signature.
    """
    return {
        "max_bytes": DEFAULT_MAX_BYTES,
        "max_lines": DEFAULT_MAX_LINES,
        "max_line_length": DEFAULT_MAX_LINE_LENGTH,
    }


def get_max_bytes() -> int:
    """Shortcut for callers that only need the byte cap."""
    return get_tool_output_limits()["max_bytes"]


def get_max_lines() -> int:
    """Shortcut for callers that only need the line cap."""
    return get_tool_output_limits()["max_lines"]


def get_max_line_length() -> int:
    """Shortcut for callers that only need the per-line cap."""
    return get_tool_output_limits()["max_line_length"]
