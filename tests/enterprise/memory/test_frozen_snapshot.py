"""Tests for ``enterprise.memory.frozen_snapshot.MemoryStore``.

Covers the FR-015 invariants:

* The snapshot captured at ``load_from_disk()`` is immutable for the
  rest of the session even if live state mutates.
* Persistence under ``~/.vigilador/memories/`` (here redirected to
  ``tmp_path`` via ``VT_MEMORIES_DIR``).
* Dedup at load time + per-store char limit enforcement.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def memory_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("VT_MEMORIES_DIR", str(tmp_path))
    return tmp_path


def test_load_from_disk_with_no_files_returns_empty_snapshot(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    snap = store.load_from_disk()
    assert snap.memory_block == ""
    assert snap.user_block == ""
    assert store.read("memory") == []
    assert store.read("user") == []


def test_load_from_disk_parses_existing_files(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import (
        ENTRY_DELIMITER,
        MemoryStore,
    )

    (memory_dir / "MEMORY.md").write_text(
        f"alpha note{ENTRY_DELIMITER}beta note{ENTRY_DELIMITER}gamma note",
        encoding="utf-8",
    )
    (memory_dir / "USER.md").write_text(
        "user prefers concise replies", encoding="utf-8"
    )
    store = MemoryStore()
    store.load_from_disk()
    assert store.read("memory") == ["alpha note", "beta note", "gamma note"]
    assert store.read("user") == ["user prefers concise replies"]


def test_snapshot_is_frozen_after_load(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    store.load_from_disk()
    snap_before = store.system_prompt_snapshot()
    store.add("memory", "new mid-session entry")
    snap_after = store.system_prompt_snapshot()
    # Frozen — same dataclass instance, same content.
    assert snap_after is snap_before
    assert "new mid-session entry" not in snap_after.memory_block
    # Live state, however, must reflect the addition.
    assert "new mid-session entry" in store.read("memory")


def test_add_persists_to_disk(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    store.load_from_disk()
    store.add("memory", "first entry")
    store.add("user", "user is on Windows 11")
    assert (memory_dir / "MEMORY.md").exists()
    assert (memory_dir / "USER.md").exists()
    assert "first entry" in (memory_dir / "MEMORY.md").read_text(encoding="utf-8")
    assert "Windows 11" in (memory_dir / "USER.md").read_text(encoding="utf-8")


def test_add_dedups_identical_content(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    store.load_from_disk()
    store.add("memory", "duplicate")
    store.add("memory", "duplicate")
    assert store.read("memory").count("duplicate") == 1


def test_remove_finds_unique_substring(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    store.load_from_disk()
    store.add("memory", "alpha entry first")
    store.add("memory", "beta entry second")
    store.remove("memory", "alpha")
    assert "alpha entry first" not in store.read("memory")
    assert "beta entry second" in store.read("memory")


def test_remove_ambiguous_substring_raises(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    store.load_from_disk()
    store.add("memory", "common word once")
    store.add("memory", "common word twice")
    with pytest.raises(ValueError, match="matches 2 entries"):
        store.remove("memory", "common")


def test_add_rejects_oversized_entry(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore(memory_char_limit=50)
    store.load_from_disk()
    with pytest.raises(ValueError, match="too large"):
        store.add("memory", "x" * 100)


def test_add_evicts_to_fit_when_total_exceeds_limit(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    # Tight limit + 3 entries that together exceed it → oldest evicted.
    store = MemoryStore(memory_char_limit=30)
    store.load_from_disk()
    store.add("memory", "AAAAAAAAAA")  # 10 chars
    store.add("memory", "BBBBBBBBBB")
    store.add("memory", "CCCCCCCCCC")
    # 30 chars + 2 delimiters (~6 chars) = ~36 > 30 → A gets evicted.
    entries = store.read("memory")
    assert "CCCCCCCCCC" in entries
    assert len(entries) <= 3


def test_unknown_target_raises(memory_dir):
    from vigilancia_multiagente.enterprise.memory.frozen_snapshot import MemoryStore

    store = MemoryStore()
    store.load_from_disk()
    with pytest.raises(ValueError, match="unknown target"):
        store.add("system", "x")
