"""Thread-safe MCP result cache with per-tool TTLs.

Reduces redundant MCP calls and API costs by caching results
keyed by ``(tool_name, normalized_query)``.

Notable exclusions (never cached):
- Tools that return dynamic/real-time data (news, etc.)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import timedelta
from threading import Lock
from typing import Any


@dataclass(slots=True)
class _CacheEntry:
    data: dict[str, Any]
    expires_at: float  # monotonic timestamp


@dataclass(slots=True)
class MCPSmartCache:
    """Thread-safe MCP cache with configurable per-tool TTLs.

    Usage:
        cache = MCPSmartCache()
        result = cache.get("tavily_search", "latest AI news")
        if result is None:
            result = await execute_tool(...)
            cache.set("tavily_search", "latest AI news", result)
    """

    _store: dict[str, _CacheEntry] = field(default_factory=dict, repr=False)
    _tool_index: dict[str, set[str]] = field(default_factory=dict, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    # Default TTLs per tool (in seconds)
    _ttls: dict[str, float] = field(
        default_factory=lambda: {
            "tavily_search": timedelta(hours=1).total_seconds(),
            "tavily_extract": timedelta(hours=24).total_seconds(),
            "web_search_exa": timedelta(hours=1).total_seconds(),
            "web_search_advanced_exa": timedelta(days=7).total_seconds(),
            "read_url": timedelta(hours=24).total_seconds(),
            "search_web": timedelta(hours=1).total_seconds(),
            "guess_datetime_url": timedelta(hours=24).total_seconds(),
            "brave_web_search": timedelta(hours=1).total_seconds(),
            "brave_news_search": timedelta(minutes=30).total_seconds(),
            "firecrawl_scrape": timedelta(days=1).total_seconds(),
            "search_google_scholar_key_words": timedelta(days=3).total_seconds(),
            "search_papers": timedelta(days=3).total_seconds(),
            "fetch": timedelta(hours=1).total_seconds(),
            "execute_code": timedelta(seconds=60).total_seconds(),
            "list_libraries": timedelta(hours=1).total_seconds(),
            "visualize": timedelta(seconds=60).total_seconds(),
            "convert_to_markdown": timedelta(hours=1).total_seconds(),
            "browser_navigate": 0.0,
            "browser_snapshot": 0.0,
            "browser_screenshot": 0.0,
            "browser_click": 0.0,
            "browser_type": 0.0,
            "browser_select_option": 0.0,
            "browser_hover": 0.0,
            "browser_tabs": 0.0,
            "browser_network_requests": 0.0,
            "browser_network_request": 0.0,
        }
    )

    @staticmethod
    def _normalize(tool: str, query: str) -> str:
        """Build a deterministic cache key from tool + query."""
        key = f"{tool}::{query.strip().lower()}"
        return hashlib.sha256(key.encode()).hexdigest()

    def get(self, tool: str, query: str) -> dict[str, Any] | None:
        """Return cached result for *(tool, query)* or ``None``.

        Also returns ``None`` if the entry has expired (lazy eviction).
        """
        key = self._normalize(tool, query)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry.data

    def set(
        self,
        tool: str,
        query: str,
        data: dict[str, Any],
        ttl_seconds: float | None = None,
    ) -> None:
        """Store *data* keyed by *(tool, query)*.

        Args:
            tool: MCP tool name (e.g. ``tavily_search``).
            query: The search query / URL used.
            data: The result payload to cache.
            ttl_seconds: Override the default TTL for *tool*.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._ttls.get(tool, 3600.0)
        key = self._normalize(tool, query)
        with self._lock:
            self._store[key] = _CacheEntry(
                data=data,
                expires_at=time.monotonic() + max(ttl, 1.0),
            )
            self._tool_index.setdefault(tool, set()).add(key)

    def invalidate(self, tool: str, query: str | None = None) -> None:
        """Remove cache entries for the given *tool*.

        If *query* is provided, only that specific entry is removed.
        Otherwise, ALL entries for that tool are removed.
        """
        with self._lock:
            if query is not None:
                key = self._normalize(tool, query)
                self._store.pop(key, None)
                if tool in self._tool_index:
                    self._tool_index[tool].discard(key)
                return
            keys = self._tool_index.pop(tool, set())
            for k in keys:
                self._store.pop(k, None)

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._store.clear()
            self._tool_index.clear()

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        with self._lock:
            # Prune expired entries
            now = time.monotonic()
            expired = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired:
                del self._store[k]
            if expired:
                expired_keys = set(expired)
                for keys in self._tool_index.values():
                    keys.difference_update(expired_keys)
            return len(self._store)
