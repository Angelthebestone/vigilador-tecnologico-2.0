"""Tests for SelfImprovementPhase — T030."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext
from vigilancia_multiagente.enterprise.dreaming.phases.self_improvement import (
    SelfImprovementPhase,
)


class FakeFeedbackStore:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts

    async def get_negative_feedback_counts(self, days: int) -> dict[str, int]:
        return self._counts

    async def get_prompt_content(self, prompt_id: str) -> str:
        return f"Original prompt for {prompt_id}"


class FakeVariantGenerator:
    async def generate_variant(self, original: str) -> str:
        return f"Improved: {original}"


class FakeABTestManager:
    def __init__(self, active_tests: list[dict[str, Any]] | None = None) -> None:
        self._active = active_tests or []
        self.created: list[tuple[str, str]] = []
        self.promoted: list[str] = []
        self.reverted: list[str] = []
        self._evaluations: dict[str, dict[str, Any]] = {}

    def set_evaluation(self, test_id: str, result: dict[str, Any]) -> None:
        self._evaluations[test_id] = result

    async def create_test(self, prompt_id: str, variant: str) -> str:
        self.created.append((prompt_id, variant))
        return f"test_{prompt_id}"

    async def get_active_tests(self) -> list[dict[str, Any]]:
        return self._active

    async def evaluate_test(self, test_id: str) -> dict[str, Any]:
        return self._evaluations.get(test_id, {})

    async def promote_variant(self, test_id: str) -> None:
        self.promoted.append(test_id)

    async def revert_variant(self, test_id: str) -> None:
        self.reverted.append(test_id)


def _ctx(llm: bool = True) -> DreamingContext:
    return DreamingContext(
        cycle_id="c1", started_at=datetime.now(UTC), tenant_id="t1", llm_available=llm
    )


@pytest.mark.asyncio
async def test_detects_negative_feedback_prompts() -> None:
    feedback = FakeFeedbackStore({"p1": 6, "p2": 3})
    ab = FakeABTestManager()
    phase = SelfImprovementPhase(feedback, FakeVariantGenerator(), ab)
    result = await phase.execute(_ctx())
    assert result.metrics_dict["variants_created"] == 1
    assert ab.created[0][0] == "p1"


@pytest.mark.asyncio
async def test_generates_variant_via_llm() -> None:
    feedback = FakeFeedbackStore({"p1": 5})
    ab = FakeABTestManager()
    phase = SelfImprovementPhase(feedback, FakeVariantGenerator(), ab)
    await phase.execute(_ctx())
    assert "Improved:" in ab.created[0][1]


@pytest.mark.asyncio
async def test_activates_ab_test() -> None:
    feedback = FakeFeedbackStore({"p1": 7})
    ab = FakeABTestManager()
    phase = SelfImprovementPhase(feedback, FakeVariantGenerator(), ab)
    await phase.execute(_ctx())
    assert len(ab.created) == 1


@pytest.mark.asyncio
async def test_promotes_winning_variant() -> None:
    ab = FakeABTestManager(active_tests=[{"test_id": "t1"}])
    ab.set_evaluation("t1", {"winner": "variant", "confidence_drop": 0.0})
    feedback = FakeFeedbackStore({})
    phase = SelfImprovementPhase(feedback, FakeVariantGenerator(), ab)
    result = await phase.execute(_ctx())
    assert "t1" in ab.promoted
    assert result.metrics_dict["promoted"] == 1


@pytest.mark.asyncio
async def test_reverts_variant_with_confidence_drop() -> None:
    ab = FakeABTestManager(active_tests=[{"test_id": "t1"}])
    ab.set_evaluation("t1", {"confidence_drop": 0.15})
    feedback = FakeFeedbackStore({})
    phase = SelfImprovementPhase(feedback, FakeVariantGenerator(), ab)
    result = await phase.execute(_ctx())
    assert "t1" in ab.reverted
    assert result.metrics_dict["reverted"] == 1
