"""Two-tier embedding cache (L1 memory LRU + L2 disk)."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class EmbeddingCachePort(Protocol):
    def get(self, content: str) -> list[float] | None: ...
    def set(self, content: str, vector: list[float]) -> None: ...
    def get_many(self, contents: list[str]) -> dict[str, list[float]]: ...
    def flush_to_disk(self) -> None: ...
    def load_from_disk(self) -> None: ...


class EmbeddingCacheError(Exception):
    """Raised when disk cache operations fail."""


class EmbeddingCache:
    """Two-tier cache for embeddings: L1 (memory LRU) + L2 (disk JSON)."""

    def __init__(
        self,
        cache_dir: str | Path,
        filename: str,
        max_memory_entries: int = 1000,
    ) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._filepath = self._cache_dir / filename
        self._max_memory_entries = max_memory_entries

        # L1: In-memory LRU cache
        self._l1_cache: OrderedDict[str, list[float]] = OrderedDict()
        # L2: Disk cache (loaded into memory on boot)
        self._l2_cache: dict[str, list[float]] = {}
        # Index: content_hash -> vector_key (for fast lookup)
        self._index: dict[str, str] = {}

    def _compute_key(self, content: str) -> str:
        """Compute SHA-256 hash of content (truncated to 4KB) for cache key."""
        truncated = content[:4096]
        return hashlib.sha256(truncated.encode("utf-8")).hexdigest()[:16]

    def get(self, content: str) -> list[float] | None:
        """Get embedding vector for content. Returns None if not found."""
        key = self._compute_key(content)

        # Check L1
        if key in self._l1_cache:
            self._l1_cache.move_to_end(key)
            return self._l1_cache[key]

        # Check L2
        if key in self._l2_cache:
            vector = self._l2_cache[key]
            self._set_l1(key, vector)
            return vector

        return None

    def set(self, content: str, vector: list[float]) -> None:
        """Set embedding vector for content."""
        key = self._compute_key(content)
        self._l2_cache[key] = vector
        self._set_l1(key, vector)

    def _set_l1(self, key: str, vector: list[float]) -> None:
        """Internal method to set L1 cache with LRU eviction."""
        if key in self._l1_cache:
            self._l1_cache.move_to_end(key)
        else:
            if len(self._l1_cache) >= self._max_memory_entries:
                self._l1_cache.popitem(last=False)
            self._l1_cache[key] = vector

    def get_many(self, contents: list[str]) -> dict[str, list[float]]:
        """Get embeddings for multiple contents. Returns dict of content -> vector."""
        results = {}
        for content in contents:
            vector = self.get(content)
            if vector is not None:
                results[content] = vector
        return results

    def load_from_disk(self) -> None:
        """Load L2 cache from disk."""
        if not self._filepath.exists():
            return

        try:
            with open(self._filepath, encoding="utf-8") as f:
                self._l2_cache = json.load(f)
            logger.info(f"Loaded {len(self._l2_cache)} embeddings from {self._filepath}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                f"Failed to load embedding cache from {self._filepath}: {e}. Starting fresh."
            )
            self._l2_cache = {}

    def flush_to_disk(self) -> None:
        """Flush L2 cache to disk atomically."""
        if not self._l2_cache:
            return

        try:
            tmp_path = self._filepath.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._l2_cache, f)
            tmp_path.replace(self._filepath)
            logger.info(f"Flushed {len(self._l2_cache)} embeddings to {self._filepath}")
        except OSError as e:
            logger.error(f"Failed to flush embedding cache to {self._filepath}: {e}")
            raise EmbeddingCacheError(f"Failed to write cache to disk: {e}") from e
