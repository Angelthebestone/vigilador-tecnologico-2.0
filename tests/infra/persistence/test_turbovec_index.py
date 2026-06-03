"""Tests for ``infra.persistence.turbovec_index.TurboVecIndex`` (Spec 021 D1).

The tests do **not** require ``turbovec`` to be actually installed: we
inject a fake module via ``sys.modules`` to exercise the adapter
contract. The optional-dep probe path is tested separately by removing
``turbovec`` from ``sys.modules`` before the call.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

_TENANT = uuid4()


@dataclass
class _Chunk:
    chunk_id: int
    embedding: list[float]
    metadata: dict[str, object]


# ---------------------------------------------------------------------------
# Fake turbovec module
# ---------------------------------------------------------------------------


class _FakeTurboQuantIndex:
    def __init__(self, dim: int, bit_width: int) -> None:
        self.dim = dim
        self.bit_width = bit_width
        self._vectors: list[list[float]] = []

    def add(self, vectors) -> None:
        # Accept a numpy array OR list-of-lists.
        for row in vectors:
            self._vectors.append(list(row))

    def search(self, query, k: int):
        # Naive cosine: we just return slot ids in insertion order with
        # decreasing scores — enough to validate the wiring.
        scores = list(range(len(self._vectors), 0, -1))[:k]
        indices = list(range(len(self._vectors)))[:k]
        return scores, indices

    def write(self, path: str) -> None:
        from pathlib import Path

        Path(path).write_text("fake-tq-blob", encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> _FakeTurboQuantIndex:
        return cls(dim=4, bit_width=4)


@pytest.fixture
def fake_turbovec(monkeypatch):
    fake_mod = SimpleNamespace(TurboQuantIndex=_FakeTurboQuantIndex)
    monkeypatch.setitem(sys.modules, "turbovec", fake_mod)
    yield fake_mod
    # cleanup handled by monkeypatch teardown


@pytest.fixture
def fake_numpy_required(monkeypatch):
    """Some tests need numpy; skip silently if not available."""
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        pytest.skip("numpy not installed in this environment")


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcheck_down_when_turbovec_missing(monkeypatch):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    monkeypatch.delitem(sys.modules, "turbovec", raising=False)
    # Also block fresh imports.
    real_finder = sys.meta_path[:]

    class _BlockTurbovec:
        def find_spec(self, name, *args, **kwargs):
            if name == "turbovec":
                raise ImportError("blocked by test")
            return

    sys.meta_path.insert(0, _BlockTurbovec())
    try:
        idx = TurboVecIndex(home_dir=None)
        result = await idx.healthcheck()
        assert result == "DOWN"
    finally:
        sys.meta_path[:] = real_finder


@pytest.mark.asyncio
async def test_healthcheck_up_when_turbovec_present(fake_turbovec, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    assert await idx.healthcheck() == "UP"


# ---------------------------------------------------------------------------
# add / query / persist / rebuild
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_then_query_round_trip(fake_turbovec, fake_numpy_required, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    chunks = [
        _Chunk(chunk_id=10, embedding=[0.1, 0.2, 0.3, 0.4], metadata={"src": "a"}),
        _Chunk(chunk_id=11, embedding=[0.5, 0.6, 0.7, 0.8], metadata={"src": "b"}),
    ]
    added = await idx.add(_TENANT, chunks)
    assert added == 2

    hits = await idx.query(_TENANT, [0.1, 0.2, 0.3, 0.4], k=2)
    # Fake search returns [(slot=0,score=2),(slot=1,score=1)] — both
    # slots resolve to chunk_ids 10 and 11.
    assert {chunk_id for chunk_id, _ in hits} == {10, 11}


@pytest.mark.asyncio
async def test_query_with_k_zero_raises(fake_turbovec, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    with pytest.raises(ValueError, match="k must be positive"):
        await idx.query(_TENANT, [0.1, 0.2], k=0)


@pytest.mark.asyncio
async def test_persist_writes_tq_file(fake_turbovec, fake_numpy_required, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    chunks = [_Chunk(chunk_id=1, embedding=[0.1, 0.2], metadata={})]
    await idx.add(_TENANT, chunks)
    await idx.persist(_TENANT)
    expected = tmp_path / f"{_TENANT}.tq"
    assert expected.exists(), f"persistence file not written: {expected}"
    sidecar = tmp_path / f"{_TENANT}.tq.meta.json"
    assert sidecar.exists(), "metadata sidecar missing"


@pytest.mark.asyncio
async def test_query_with_allowlist_filters_results(fake_turbovec, fake_numpy_required, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    chunks = [
        _Chunk(chunk_id=10, embedding=[0.1, 0.2], metadata={}),
        _Chunk(chunk_id=11, embedding=[0.3, 0.4], metadata={}),
    ]
    await idx.add(_TENANT, chunks)
    hits = await idx.query(_TENANT, [0.1, 0.2], k=2, allowlist=[10])
    assert {chunk_id for chunk_id, _ in hits} == {10}


@pytest.mark.asyncio
async def test_dim_mismatch_raises(fake_turbovec, fake_numpy_required, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    await idx.add(
        _TENANT,
        [_Chunk(chunk_id=1, embedding=[0.1, 0.2, 0.3, 0.4], metadata={})],
    )
    with pytest.raises(ValueError, match="dim mismatch"):
        await idx.add(
            _TENANT,
            [_Chunk(chunk_id=2, embedding=[0.1, 0.2], metadata={})],
        )


@pytest.mark.asyncio
async def test_rebuild_loads_existing_persistence(fake_turbovec, fake_numpy_required, tmp_path):
    from vigilancia_multiagente.infra.persistence.turbovec_index import TurboVecIndex

    idx = TurboVecIndex(home_dir=tmp_path)
    await idx.add(
        _TENANT,
        [_Chunk(chunk_id=1, embedding=[0.1, 0.2], metadata={"src": "x"})],
    )
    await idx.persist(_TENANT)
    # Drop the in-memory state and rebuild from disk.
    idx._handles.clear()
    await idx.rebuild(_TENANT)
    assert _TENANT in idx._handles
