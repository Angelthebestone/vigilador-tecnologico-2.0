"""T050: Verify SkillRegistry uses EmbeddingCache."""

import tempfile

import pytest

from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    SkillCard,
    SkillSource,
    SkillSummary,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import SkillRegistry
from vigilancia_multiagente.infra.embeddings.embedding_cache import EmbeddingCache


class FakeEmbeddingGateway:
    def __init__(self):
        self.call_count = 0

    async def embed(self, text: str, task_type=None) -> list[float]:
        self.call_count += 1
        # Simple hash-based embedding
        h = hash(text) % 1000
        return [float(h), float(h + 1), float(h + 2)]


class FakeToolRegistry:
    async def is_capability_available(self, cap: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_registry_caches_embeddings():
    """SkillRegistry caches embeddings and doesn't recompute on re-registration."""
    with tempfile.TemporaryDirectory() as tmp:
        cache = EmbeddingCache(cache_dir=tmp, filename="skills.json")

        gateway = FakeEmbeddingGateway()
        tool_registry = FakeToolRegistry()
        registry = SkillRegistry(gateway, tool_registry, embedding_cache=cache)

        card = SkillCard(
            id="test-skill",
            display_name="Test Skill",
            description="A test skill",
            tags=["test"],
            source=SkillSource.CURATED,
        )
        summary = SkillSummary(required_capabilities=[])

        # First registration should call embed
        await registry.register(card, summary)
        assert gateway.call_count == 1

        # Remove from in-memory and re-register — should hit cache
        del registry._cards["test-skill"]
        del registry._embeddings["test-skill"]
        await registry.register(card, summary)
        assert gateway.call_count == 1  # Still 1, cache was used
