"""Frozen-snapshot memory store (Spec 021 FR-015).

# Adapted from Hermes Agent — Original file: tools/memory_tool.py — License: MIT

Persistent curated memory backed by two Markdown files:

* ``MEMORY.md`` — agent's personal notes (environment facts, conventions, …).
* ``USER.md``   — what the agent knows about the user (preferences, habits, …).

Both files live under ``~/.vigilador/memories/`` (overridable via
``VT_MEMORIES_DIR``) and are injected into the system prompt as a **frozen
snapshot** captured at ``load_from_disk()``. The snapshot never mutates
mid-session (prefix-cache invariant). Mid-session writes update the live
state and the on-disk file immediately, so the next session start picks
them up.

This port drops two Hermes features that are out of scope for the MVP:
* the ``threat_patterns`` content scanner — PI defense already lives in
  ``enterprise/governance/`` and runs at the I/O boundary;
* the drift-detection ``.bak`` rescue path — MVP uses last-write-wins
  with a file lock; concurrent multi-session writes are not a target.

Constitución:
* SRP: one class, one concern (bounded curated memory + snapshot).
* #4 explicit errors: char-limit overflow surfaces as ``ValueError``,
  not a silent truncation.
* OS portability: ``msvcrt`` on Windows, ``fcntl`` elsewhere.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Section delimiter — same as upstream so existing memory files round-trip.
ENTRY_DELIMITER = "\n§\n"

_DEFAULT_MEMORY_DIR_ENV = "VT_MEMORIES_DIR"
_DEFAULT_MEMORY_DIR = "~/.vigilador/memories"
_DEFAULT_MEMORY_LIMIT = 2200
_DEFAULT_USER_LIMIT = 1375

# Cross-platform file locks
_fcntl = None
_msvcrt = None
try:
    import fcntl as _fcntl  # type: ignore[no-redef]
except ImportError:
    import contextlib

    with contextlib.suppress(ImportError):
        import msvcrt as _msvcrt  # type: ignore[no-redef]


def get_memory_dir() -> Path:
    """Resolve the active memories directory (honors ``VT_MEMORIES_DIR``)."""
    env_dir = os.getenv(_DEFAULT_MEMORY_DIR_ENV)
    base = Path(env_dir) if env_dir else Path(_DEFAULT_MEMORY_DIR)
    return base.expanduser()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenSnapshot:
    """Immutable, session-start capture of memory state."""

    memory_block: str
    user_block: str

    def render_system_prompt_section(self) -> str:
        """Render both blocks for system-prompt injection (memory then user)."""
        parts: list[str] = []
        if self.memory_block.strip():
            parts.append(self.memory_block)
        if self.user_block.strip():
            parts.append(self.user_block)
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------


@dataclass
class MemoryStore:
    """Bounded curated memory with file persistence; one instance per agent.

    Maintains two parallel states:

    * ``_snapshot`` (frozen at ``load_from_disk()``) — used for system-prompt
      injection. Never mutated mid-session.
    * ``memory_entries`` / ``user_entries`` (live) — mutated by ``add`` /
      ``remove``, persisted to disk on each call.
    """

    memory_char_limit: int = _DEFAULT_MEMORY_LIMIT
    user_char_limit: int = _DEFAULT_USER_LIMIT
    memory_entries: list[str] = field(default_factory=list)
    user_entries: list[str] = field(default_factory=list)
    _snapshot: FrozenSnapshot = field(
        default_factory=lambda: FrozenSnapshot(memory_block="", user_block="")
    )

    # ------------------------------------------------------------------
    # Public API — load / read / write
    # ------------------------------------------------------------------

    def load_from_disk(self) -> FrozenSnapshot:
        """Read both files + capture a frozen snapshot for the system prompt."""
        mem_dir = get_memory_dir()
        mem_dir.mkdir(parents=True, exist_ok=True)

        self.memory_entries = self._read_file(mem_dir / "MEMORY.md")
        self.user_entries = self._read_file(mem_dir / "USER.md")

        # Dedup, preserving order (first occurrence wins).
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))

        self._snapshot = FrozenSnapshot(
            memory_block=self._render_block("memory", self.memory_entries),
            user_block=self._render_block("user", self.user_entries),
        )
        return self._snapshot

    def system_prompt_snapshot(self) -> FrozenSnapshot:
        """Return the snapshot captured at the most recent ``load_from_disk()``."""
        return self._snapshot

    def read(self, target: str) -> list[str]:
        """Return live entries for ``target`` ('memory' | 'user')."""
        return list(self._entries_for(target))

    def add(self, target: str, content: str) -> int:
        """Append ``content`` to ``target``; persists immediately. Returns new count.

        Raises:
            ValueError: empty content, unknown target, or single-entry
                content exceeding the per-store char limit.
        """
        content = content.strip()
        if not content:
            raise ValueError("MemoryStore.add: 'content' must be non-empty")
        target = target.lower()
        if target not in ("memory", "user"):
            raise ValueError(
                f"MemoryStore.add: unknown target '{target}' "
                "(supported: memory, user)"
            )
        limit = self._limit_for(target)
        if len(content) > limit:
            raise ValueError(
                f"MemoryStore.add: single entry too large "
                f"({len(content)} > {limit} chars). Split into multiple entries."
            )
        entries = self._entries_for(target)
        if content in entries:
            return len(entries)
        entries.append(content)
        # Evict oldest entries while over total limit.
        self._evict_to_fit(target)
        self._persist(target)
        return len(entries)

    def remove(self, target: str, substring: str) -> int:
        """Remove the first entry containing ``substring``; persists. Returns count.

        Raises:
            ValueError: empty substring, no match, or multiple matches.
        """
        substring = substring.strip()
        if not substring:
            raise ValueError("MemoryStore.remove: 'substring' must be non-empty")
        entries = self._entries_for(target)
        matches = [i for i, e in enumerate(entries) if substring in e]
        if not matches:
            raise ValueError(
                f"MemoryStore.remove: no entry in '{target}' contains "
                f"'{substring[:40]}'"
            )
        if len(matches) > 1:
            raise ValueError(
                f"MemoryStore.remove: substring '{substring[:40]}' matches "
                f"{len(matches)} entries; use a more unique fragment"
            )
        entries.pop(matches[0])
        self._persist(target)
        return len(entries)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _entries_for(self, target: str) -> list[str]:
        target = target.lower()
        if target == "user":
            return self.user_entries
        if target == "memory":
            return self.memory_entries
        raise ValueError(f"MemoryStore: unknown target '{target}'")

    def _limit_for(self, target: str) -> int:
        return self.user_char_limit if target == "user" else self.memory_char_limit

    @staticmethod
    def _path_for(target: str) -> Path:
        mem_dir = get_memory_dir()
        return mem_dir / ("USER.md" if target == "user" else "MEMORY.md")

    def _evict_to_fit(self, target: str) -> None:
        """FIFO eviction: drop the oldest entries while total > limit."""
        entries = self._entries_for(target)
        limit = self._limit_for(target)
        while entries and self._total_chars(entries) > limit:
            entries.pop(0)

    @staticmethod
    def _total_chars(entries: list[str]) -> int:
        joined = ENTRY_DELIMITER.join(entries)
        return len(joined)

    @staticmethod
    def _render_block(label: str, entries: list[str]) -> str:
        if not entries:
            return ""
        body = ENTRY_DELIMITER.join(entries)
        return f"### {label.upper()}\n{body}"

    @staticmethod
    def _read_file(path: Path) -> list[str]:
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        # Allow both the canonical delimiter AND a leading/trailing one.
        body = raw.strip()
        if body.startswith(ENTRY_DELIMITER.strip()):
            body = body[len(ENTRY_DELIMITER.strip()):]
        return [chunk.strip() for chunk in body.split(ENTRY_DELIMITER) if chunk.strip()]

    def _persist(self, target: str) -> None:
        """Atomic write under file lock."""
        path = self._path_for(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = ENTRY_DELIMITER.join(self._entries_for(target))
        with self._file_lock(path):
            self._atomic_write(path, body)

    @staticmethod
    @contextmanager
    def _file_lock(path: Path) -> Iterator[None]:
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if _fcntl is None and _msvcrt is None:
            yield
            return
        # Open in append mode so we don't truncate the lock file.
        fd = open(lock_path, "a+", encoding="utf-8")  # noqa: SIM115
        try:
            if _fcntl is not None:
                _fcntl.flock(fd, _fcntl.LOCK_EX)
            elif _msvcrt is not None:
                fd.seek(0)
                _msvcrt.locking(fd.fileno(), _msvcrt.LK_LOCK, 1)
            yield
        finally:
            if _fcntl is not None:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
            elif _msvcrt is not None:
                fd.seek(0)
                _msvcrt.locking(fd.fileno(), _msvcrt.LK_UNLCK, 1)
            fd.close()

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write ``content`` to ``path`` atomically."""
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=path.name + ".", dir=str(path.parent)
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except OSError:
            try:
                os.unlink(tmp_path)
            except OSError as cleanup_exc:
                logger.warning(
                    "MemoryStore: tempfile cleanup failed for %s: %s",
                    tmp_path, cleanup_exc,
                )
            raise
