# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Phase 3 — Self-improvement: detect bad prompts, generate variants, A/B test."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class FeedbackStore(Protocol):
    """Port for querying prompt feedback."""

    async def get_negative_feedback_counts(self, days: int) -> dict[str, int]: ...

    async def get_prompt_content(self, prompt_id: str) -> str: ...


class PromptVariantGenerator(Protocol):
    """Port for LLM-based prompt variant generation."""

    async def generate_variant(self, original: str) -> str: ...


class ABTestManager(Protocol):
    """Port for managing A/B tests on prompts."""

    async def create_test(self, prompt_id: str, variant: str) -> str: ...

    async def get_active_tests(self) -> list[dict[str, Any]]: ...

    async def evaluate_test(self, test_id: str) -> dict[str, Any]: ...

    async def promote_variant(self, test_id: str) -> None: ...

    async def revert_variant(self, test_id: str) -> None: ...


class SelfImprovementPhase:
    """Detects prompts with negative feedback, generates variants, manages A/B tests."""

    NEGATIVE_THRESHOLD = 5
    CONFIDENCE_DROP_THRESHOLD = 0.10

    def __init__(
        self,
        feedback_store: FeedbackStore,
        variant_generator: PromptVariantGenerator,
        ab_test_manager: ABTestManager,
    ) -> None:
        self._feedback_store = feedback_store
        self._variant_generator = variant_generator
        self._ab_test_manager = ab_test_manager

    @property
    def name(self) -> str:
        return "self_improvement"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        if not context.llm_available:
            return PhaseResult(
                phase_name=self.name,
                status=PhaseStatus.SKIPPED,
                duration_ms=0.0,
                error="LLM not available",
            )

        t0 = time.perf_counter()
        variants_created = 0
        promoted = 0
        reverted = 0

        # Evaluate existing A/B tests
        active_tests = await self._ab_test_manager.get_active_tests()
        for test in active_tests:
            evaluation = await self._ab_test_manager.evaluate_test(test["test_id"])
            confidence_drop = evaluation.get("confidence_drop", 0.0)
            if confidence_drop > self.CONFIDENCE_DROP_THRESHOLD:
                await self._ab_test_manager.revert_variant(test["test_id"])
                reverted += 1
            elif evaluation.get("winner") == "variant":
                await self._ab_test_manager.promote_variant(test["test_id"])
                promoted += 1

        # Create new variants for bad prompts
        feedback_counts = await self._feedback_store.get_negative_feedback_counts(days=7)
        for prompt_id, count in feedback_counts.items():
            if count >= self.NEGATIVE_THRESHOLD:
                original = await self._feedback_store.get_prompt_content(prompt_id)
                variant = await self._variant_generator.generate_variant(original)
                await self._ab_test_manager.create_test(prompt_id, variant)
                variants_created += 1

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={
                "variants_created": variants_created,
                "promoted": promoted,
                "reverted": reverted,
            },
        )
