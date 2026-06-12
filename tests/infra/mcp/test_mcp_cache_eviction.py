"""T124 — MCP cache LRU eviction and TTL tests."""

from __future__ import annotations

import time

from vigilancia_multiagente.infra.mcp.mcp_cache import MCPSmartCache


def test_cache_evicts_lru_when_over_max():
    """Entries beyond max_entries are evicted (oldest first)."""
    cache = MCPSmartCache()
    cache._max_entries = 3

    for i in range(5):
        cache.set("tool_a", f"query_{i}", {"result": i}, ttl_seconds=3600)

    assert cache.size == 3
    assert cache.get("tool_a", "query_0") is None
    assert cache.get("tool_a", "query_1") is None
    assert cache.get("tool_a", "query_2") is not None


def test_cache_get_moves_to_end_for_lru():
    """Accessing an entry moves it to the end (most recently used)."""
    cache = MCPSmartCache()
    cache._max_entries = 3

    cache.set("tool_a", "q1", {"r": 1}, ttl_seconds=3600)
    cache.set("tool_a", "q2", {"r": 2}, ttl_seconds=3600)
    cache.set("tool_a", "q3", {"r": 3}, ttl_seconds=3600)

    cache.get("tool_a", "q1")

    cache.set("tool_a", "q4", {"r": 4}, ttl_seconds=3600)

    assert cache.get("tool_a", "q1") is not None
    assert cache.get("tool_a", "q2") is None


def test_cache_expired_entry_returns_none():
    """Expired entries are lazily evicted on get()."""
    cache = MCPSmartCache()
    cache.set("tool_a", "q1", {"r": 1}, ttl_seconds=1.01)

    time.sleep(1.1)

    assert cache.get("tool_a", "q1") is None
    assert cache.size == 0


def test_cache_invalidate_by_tool():
    """invalidate(tool) removes all entries for that tool."""
    cache = MCPSmartCache()

    cache.set("tool_a", "q1", {"r": 1}, ttl_seconds=3600)
    cache.set("tool_a", "q2", {"r": 2}, ttl_seconds=3600)
    cache.set("tool_b", "q1", {"r": 3}, ttl_seconds=3600)

    cache.invalidate("tool_a")

    assert cache.get("tool_a", "q1") is None
    assert cache.get("tool_a", "q2") is None
    assert cache.get("tool_b", "q1") is not None


def test_cache_clear_empties_everything():
    """clear() removes all entries across all tools."""
    cache = MCPSmartCache()

    cache.set("tool_a", "q1", {"r": 1}, ttl_seconds=3600)
    cache.set("tool_b", "q1", {"r": 2}, ttl_seconds=3600)

    cache.clear()

    assert cache.size == 0
    assert cache.get("tool_a", "q1") is None
    assert cache.get("tool_b", "q1") is None
