# Adapted from Hermes Agent -- original: tools/file_state.py -- License: MIT
"""Lightweight file state tracking for the file_system tool.

Tracks SHA-256 hashes of files that have been read or written,
enabling staleness detection for downstream consumers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class FileRecord:
    """Snapshot of a file's state at a point in time."""

    path: str
    sha256: str
    size: int


class FileStateTracker:
    """Tracks known file hashes for staleness detection."""

    _records: dict[str, FileRecord] = field(default_factory=dict)  # type: ignore[assignment]

    def __init__(self) -> None:
        self._records: dict[str, FileRecord] = {}

    def record(self, resolved_path: Path) -> FileRecord:
        """Record the current state of a file. Returns the FileRecord."""
        content = resolved_path.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        rec = FileRecord(
            path=str(resolved_path),
            sha256=sha,
            size=len(content),
        )
        self._records[str(resolved_path)] = rec
        return rec

    def is_stale(self, resolved_path: Path) -> bool | None:
        """Check if a file has changed since last recorded state.

        Returns True if changed, False if unchanged, None if never recorded.
        """
        key = str(resolved_path)
        prev = self._records.get(key)
        if prev is None:
            return None
        if not resolved_path.exists():
            return True
        content = resolved_path.read_bytes()
        current_sha = hashlib.sha256(content).hexdigest()
        return current_sha != prev.sha256

    def known_files(self) -> list[str]:
        """Return list of tracked file paths."""
        return list(self._records.keys())

    def clear(self) -> None:
        """Clear all tracked state."""
        self._records.clear()
