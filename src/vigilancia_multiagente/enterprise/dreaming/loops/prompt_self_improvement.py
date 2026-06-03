# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Loop 3 — Prompt self-improvement: generate variants and manage A/B tests."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class PromptFeedbackSource(Protocol):
    """Port for querying prompt feedback data."""

    async def get_negative_prompts(self, days: int, threshold: int) -> list[dict[str, Any]]: ...


class PromptVariantEngine(Protocol):
    """Port for generating prompt variants via LLM."""

    async def generate(self, original_content: str) -> str: ...


class PromptABTestStore(Protocol):
    """Port for managing prompt A/B tests."""

    async def create(self, prompt_id: str, variant_content: str) -> str: ...

    async def get_active(self) -> list[dict[str, Any]]: ...

    async def evaluate(self, test_id: str) -> dict[str, Any]: ...

    async def promote(self, test_id: str) -> None: ...

    async def revert(self, test_id: str) -> None: ...


class PromptSelfImprovementLoop:
    """Generates prompt variants and manages their A/B lifecycle."""

    CONFIDENCE_DROP_LIMIT = 0.10

    def __init__(
        self,
        feedback_source: PromptFeedbackSource,
        variant_engine: PromptVariantEngine,
        ab_store: PromptABTestStore,
    ) -> None:
        self._feedback_source = feedback_source
        self._variant_engine = variant_engine
        self._ab_store = ab_store

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        variants_created = 0
        reverted = 0
        promoted = 0

        # Evaluate active tests
        active = await self._ab_store.get_active()
        for test in active:
            result = await self._ab_store.evaluate(test["test_id"])
            if result.get("confidence_drop", 0.0) > self.CONFIDENCE_DROP_LIMIT:
                await self._ab_store.revert(test["test_id"])
                reverted += 1
            elif result.get("winner") == "variant":
                await self._ab_store.promote(test["test_id"])
                promoted += 1

        # Generate new variants
        bad_prompts = await self._feedback_source.get_negative_prompts(days=7, threshold=5)
        for prompt in bad_prompts:
            variant = await self._variant_engine.generate(prompt["content"])
            await self._ab_store.create(prompt["prompt_id"], variant)
            variants_created += 1

        return {
            "variants_created": variants_created,
            "reverted": reverted,
            "promoted": promoted,
        }
