"""SkillRegistry — central registry with semantic index and progressive loading (CQS)."""

from __future__ import annotations

import logging
import math
from typing import Protocol

from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    SkillBody,
    SkillCard,
    SkillSource,
    SkillState,
    SkillSummary,
)
from vigilancia_multiagente.infra.embeddings.embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)

_SOURCE_PRIORITY: dict[SkillSource, int] = {
    SkillSource.CURATED: 0,
    SkillSource.LEARNED: 1,
    SkillSource.EXTERNAL_CLAUDE_LOCAL: 2,
}


class ToolRegistryPort(Protocol):
    """Minimal interface expected from ToolRegistry (DIP)."""

    async def is_capability_available(self, name: str) -> bool: ...


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SkillRegistry:
    """Central skill registry with semantic discovery and progressive loading.

    CQS: register/mark_* are commands; discover/get_* are queries.
    """

    def __init__(
        self,
        embedding_gateway: EmbeddingGateway,
        tool_registry: ToolRegistryPort,
        embedding_cache: EmbeddingCache | None = None,
    ) -> None:
        self._embedding_gw = embedding_gateway
        self._tool_registry = tool_registry
        self._embedding_cache = embedding_cache
        self._cards: dict[str, SkillCard] = {}
        self._summaries: dict[str, SkillSummary] = {}
        self._body_paths: dict[str, str] = {}
        self._embeddings: dict[str, list[float]] = {}

    # --- Commands ---

    async def register(
        self, card: SkillCard, summary: SkillSummary, body_path: str = ""
    ) -> None:
        """Register a skill. Deduplicates by id with source priority."""
        existing = self._cards.get(card.id)
        if existing is not None:
            if existing.source == card.source:
                raise ValueError(
                    f"Duplicate skill id '{card.id}' from same source '{card.source}'"
                )
            existing_prio = _SOURCE_PRIORITY.get(existing.source, 99)
            new_prio = _SOURCE_PRIORITY.get(card.source, 99)
            if new_prio >= existing_prio:
                logger.info(
                    "Skill '%s' from '%s' shadowed by existing '%s'",
                    card.id, card.source, existing.source,
                )
                return

        self._cards[card.id] = card
        self._summaries[card.id] = summary
        if body_path:
            self._body_paths[card.id] = body_path

        # Compute embedding for description+tags (FR-003)
        embed_text = f"{card.description} {' '.join(card.tags)}"
        if self._embedding_cache:
            cached_vec = self._embedding_cache.get(embed_text)
            if cached_vec is not None:
                self._embeddings[card.id] = cached_vec
                return
        
        vec = await self._embedding_gw.embed(embed_text)
        self._embeddings[card.id] = vec
        if self._embedding_cache:
            self._embedding_cache.set(embed_text, vec)

    async def flush_cache(self) -> None:
        """Flush skill embeddings cache to disk."""
        if self._embedding_cache:
            self._embedding_cache.flush_to_disk()

    def mark_unavailable(self, skill_id: str, reason: str) -> None:
        """Mark a skill as unavailable."""
        card = self._cards.get(skill_id)
        if card is None:
            raise KeyError(f"Skill '{skill_id}' not found in registry")
        card.state = SkillState.UNAVAILABLE
        logger.info("Skill '%s' marked unavailable: %s", skill_id, reason)

    def mark_pending_revalidation(self, skill_id: str) -> None:
        """Mark a skill as pending revalidation (hash changed)."""
        card = self._cards.get(skill_id)
        if card is None:
            raise KeyError(f"Skill '{skill_id}' not found in registry")
        card.state = SkillState.PENDING_REVALIDATION
        logger.info("Skill '%s' marked pending_revalidation", skill_id)

    # --- Queries ---

    async def discover(
        self, intent: str, mode: str | None = None, limit: int = 5
    ) -> list[SkillCard]:
        """Semantic search over registered skills, filtered by mode and availability."""
        intent_vec = await self._embedding_gw.embed(intent)
        scored: list[tuple[float, SkillCard]] = []

        for skill_id, card in self._cards.items():
            if card.state != SkillState.AVAILABLE:
                continue
            if mode and card.mode_compatible and mode not in card.mode_compatible:
                continue
            embedding = self._embeddings.get(skill_id)
            if embedding is None:
                continue
            sim = _cosine_similarity(intent_vec, embedding)
            scored.append((sim, card))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [card for _, card in scored[:limit]]

    def get_cards(self, mode: str | None = None) -> list[SkillCard]:
        """Return all available skill cards, optionally filtered by mode."""
        results: list[SkillCard] = []
        for card in self._cards.values():
            if card.state != SkillState.AVAILABLE:
                continue
            if mode and card.mode_compatible and mode not in card.mode_compatible:
                continue
            results.append(card)
        return results

    def get_summary(self, skill_id: str) -> SkillSummary:
        """Return intermediate detail for a skill."""
        summary = self._summaries.get(skill_id)
        if summary is None:
            raise KeyError(f"Skill '{skill_id}' not found in registry")
        return summary

    def get_body(self, skill_id: str) -> SkillBody:
        """Load full skill body on demand from file."""
        body_path = self._body_paths.get(skill_id)
        if not body_path:
            raise KeyError(f"No body path for skill '{skill_id}'")
        from pathlib import Path

        path = Path(body_path)
        if not path.is_file():
            raise FileNotFoundError(f"Skill body file not found: {body_path}")
        content = path.read_text(encoding="utf-8")
        return SkillBody(full_content=content)
