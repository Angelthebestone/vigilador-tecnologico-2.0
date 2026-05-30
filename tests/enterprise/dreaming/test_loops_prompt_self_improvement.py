"""Tests for PromptSelfImprovementLoop — T052."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.loops.prompt_self_improvement import (
    PromptSelfImprovementLoop,
)
from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class FakeFeedbackSource:
    def __init__(self, prompts: list[dict[str, Any]]) -> None:
        self._prompts = prompts

    async def get_negative_prompts(self, days: int, threshold: int) -> list[dict[str, Any]]:
        return self._prompts


class FakeVariantEngine:
    async def generate(self, original_content: str) -> str:
        return f"Improved: {original_content}"


class FakeABStore:
    def __init__(self, active: list[dict[str, Any]] | None = None) -> None:
        self._active = active or []
        self.created: list[tuple[str, str]] = []
        self.promoted: list[str] = []
        self.reverted: list[str] = []
        self._evals: dict[str, dict[str, Any]] = {}

    def set_eval(self, test_id: str, result: dict[str, Any]) -> None:
        self._evals[test_id] = result

    async def create(self, prompt_id: str, variant_content: str) -> str:
        self.created.append((prompt_id, variant_content))
        return f"test_{prompt_id}"

    async def get_active(self) -> list[dict[str, Any]]:
        return self._active

    async def evaluate(self, test_id: str) -> dict[str, Any]:
        return self._evals.get(test_id, {})

    async def promote(self, test_id: str) -> None:
        self.promoted.append(test_id)

    async def revert(self, test_id: str) -> None:
        self.reverted.append(test_id)


def _ctx() -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(timezone.utc), tenant_id="t1", llm_available=True
    )


@pytest.mark.asyncio
async def test_generates_variant() -> None:
    source = FakeFeedbackSource([{"prompt_id": "p1", "content": "old prompt"}])
    store = FakeABStore()
    loop = PromptSelfImprovementLoop(source, FakeVariantEngine(), store)
    result = await loop.run(_ctx())
    assert result["variants_created"] == 1
    assert "Improved:" in store.created[0][1]


@pytest.mark.asyncio
async def test_executes_ab_test() -> None:
    store = FakeABStore(active=[{"test_id": "t1"}])
    store.set_eval("t1", {"winner": "variant", "confidence_drop": 0.0})
    loop = PromptSelfImprovementLoop(FakeFeedbackSource([]), FakeVariantEngine(), store)
    result = await loop.run(_ctx())
    assert result["promoted"] == 1


@pytest.mark.asyncio
async def test_reverts_if_confidence_drops() -> None:
    store = FakeABStore(active=[{"test_id": "t1"}])
    store.set_eval("t1", {"confidence_drop": 0.15})
    loop = PromptSelfImprovementLoop(FakeFeedbackSource([]), FakeVariantEngine(), store)
    result = await loop.run(_ctx())
    assert result["reverted"] == 1
