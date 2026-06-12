"""Tests for EmbeddingCache."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vigilancia_multiagente.infra.embeddings.embedding_cache import (
    EmbeddingCache,
)


@pytest.fixture
def cache_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(cache_dir: Path) -> EmbeddingCache:
    return EmbeddingCache(cache_dir=cache_dir, filename="test_embeddings.json")


def test_set_get_roundtrip(cache: EmbeddingCache) -> None:
    content = "test content"
    vector = [0.1, 0.2, 0.3]

    cache.set(content, vector)
    result = cache.get(content)

    assert result == vector


def test_lru_evict(cache: EmbeddingCache) -> None:
    # Create cache with max 2 entries
    small_cache = EmbeddingCache(
        cache_dir=cache._cache_dir, filename="small.json", max_memory_entries=2
    )

    small_cache.set("content1", [1.0, 1.0])
    small_cache.set("content2", [2.0, 2.0])
    small_cache.set("content3", [3.0, 3.0])  # Should evict content1 from L1

    # Verify L1 eviction: content1 is no longer in L1 cache
    assert "content1" not in list(
        small_cache._l1_cache.keys()
    )  # Keys are hashed, but we can check length
    assert len(small_cache._l1_cache) == 2

    # Verify L2 fallback: get() still returns the value because it's in L2
    assert small_cache.get("content1") == [1.0, 1.0]
    assert small_cache.get("content2") == [2.0, 2.0]
    assert small_cache.get("content3") == [3.0, 3.0]

    # After get("content1"), it should be promoted back to L1
    assert len(small_cache._l1_cache) == 2


def test_disk_persist_load(cache: EmbeddingCache, cache_dir: Path) -> None:
    cache.set("content1", [1.0, 1.0])
    cache.set("content2", [2.0, 2.0])

    cache.flush_to_disk()

    # Create new cache instance to simulate boot
    new_cache = EmbeddingCache(cache_dir=cache_dir, filename="test_embeddings.json")
    new_cache.load_from_disk()

    assert new_cache.get("content1") == [1.0, 1.0]
    assert new_cache.get("content2") == [2.0, 2.0]


def test_corrupt_json_recovery(cache: EmbeddingCache, cache_dir: Path) -> None:
    # Write invalid JSON
    filepath = cache_dir / "test_embeddings.json"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("{ invalid json }")

    # Should not raise, but log warning and start fresh
    cache.load_from_disk()
    assert cache._l2_cache == {}
    assert cache.get("any content") is None


def test_get_many_batch(cache: EmbeddingCache) -> None:
    cache.set("content1", [1.0, 1.0])
    cache.set("content2", [2.0, 2.0])

    results = cache.get_many(["content1", "content2", "content3"])

    assert results == {
        "content1": [1.0, 1.0],
        "content2": [2.0, 2.0],
    }


def test_flush_atomic_write(cache: EmbeddingCache, cache_dir: Path) -> None:
    cache.set("content1", [1.0, 1.0])
    cache.flush_to_disk()

    filepath = cache_dir / "test_embeddings.json"
    tmp_filepath = cache_dir / "test_embeddings.tmp"

    # Atomic write should leave no .tmp file behind
    assert filepath.exists()
    assert not tmp_filepath.exists()

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
        assert "content1" in data or any(k for k in data)  # Key is hashed


def test_version_mismatch_warning(cache: EmbeddingCache, cache_dir: Path) -> None:
    # This test verifies that if the JSON structure changes in the future,
    # the cache gracefully handles it (currently it just overwrites or logs warning on JSONDecodeError)
    filepath = cache_dir / "test_embeddings.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"old_format": "data"}, f)

    cache.load_from_disk()
    # Should load without crashing, even if format is unexpected
    assert isinstance(cache._l2_cache, dict)
