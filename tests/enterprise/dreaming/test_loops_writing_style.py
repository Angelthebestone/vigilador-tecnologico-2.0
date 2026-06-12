"""Tests for WritingStyleLoop — T050."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.writing_style import WritingStyleLoop
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeAnalyzer:
    def __init__(self, emails: list[dict[str, Any]], stats: dict[str, Any]) -> None:
        self._emails = emails
        self._stats = stats

    async def get_recent_emails(self, tenant_id: str, days: int) -> list[dict[str, Any]]:
        return self._emails

    async def extract_style_stats(self, emails: list[dict[str, Any]]) -> dict[str, Any]:
        return self._stats


class FakeUpdater:
    def __init__(self, baseline: dict[str, Any] | None = None) -> None:
        self._baseline = baseline
        self.updated: list[dict[str, Any]] = []

    async def update(self, stats: dict[str, Any]) -> None:
        self.updated.append(stats)

    async def get_baseline(self, days: int) -> dict[str, Any] | None:
        return self._baseline


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_analyzes_approved_emails() -> None:
    analyzer = FakeAnalyzer([{"id": "e1"}], {"formality": 0.8, "length": 150})
    loop = WritingStyleLoop(analyzer, FakeUpdater())
    result = await loop.run(_ctx())
    assert result["emails_analyzed"] == 1


@pytest.mark.asyncio
async def test_updates_style_profile() -> None:
    analyzer = FakeAnalyzer([{"id": "e1"}], {"formality": 0.8})
    updater = FakeUpdater()
    loop = WritingStyleLoop(analyzer, updater)
    await loop.run(_ctx())
    assert len(updater.updated) == 1


@pytest.mark.asyncio
async def test_detects_drift_and_flags() -> None:
    analyzer = FakeAnalyzer([{"id": "e1"}], {"formality": 0.8, "length": 300})
    baseline = {"formality": 0.3, "length": 100}  # big change
    updater = FakeUpdater(baseline=baseline)
    loop = WritingStyleLoop(analyzer, updater)
    result = await loop.run(_ctx())
    assert result["drift_detected"] is True
    assert result["flagged_for_review"] is True
