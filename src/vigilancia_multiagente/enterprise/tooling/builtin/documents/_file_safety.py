# Adapted from Hermes Agent -- original: agent/file_safety.py -- License: MIT
"""Path safety validation for file_system tool.

Provides root-jail enforcement and path traversal prevention,
compatible with Windows and POSIX.
"""

from __future__ import annotations

import os
from pathlib import Path


class PathTraversalError(Exception):
    """Raised when a path escapes the allowed root jail."""

    def __init__(self, requested: str, root: str) -> None:
        self.requested = requested
        self.root = root
        super().__init__(
            f"Path traversal denied: '{requested}' resolves outside "
            f"root jail '{root}'"
        )


def resolve_safe_path(root: Path, requested: str) -> Path:
    """Resolve *requested* relative to *root*, rejecting traversal.

    Raises PathTraversalError if the resolved path escapes *root*.
    Returns the resolved absolute Path on success.
    """
    if not requested:
        raise PathTraversalError(requested, str(root))

    root_resolved = root.resolve()

    # Build candidate: if requested is absolute, still jail it under root
    candidate = Path(requested)
    if candidate.is_absolute():
        # Strip drive on Windows to avoid escaping root via absolute path
        rel_parts = candidate.parts[1:]  # drop root/drive
        candidate = root_resolved.joinpath(*rel_parts) if rel_parts else root_resolved
    else:
        candidate = root_resolved / candidate

    resolved = candidate.resolve()

    # Ensure resolved path is within root (or IS root)
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        raise PathTraversalError(requested, str(root_resolved)) from None

    return resolved


def validate_filename(name: str) -> None:
    """Reject filenames with dangerous characters (null bytes, path seps)."""
    if not name:
        raise ValueError("Filename must not be empty")
    if "\x00" in name:
        raise ValueError(f"Filename contains null byte: {name!r}")
    if os.sep in name or (os.altsep and os.altsep in name):
        raise ValueError(
            f"Filename contains path separator: {name!r}"
        )
