"""Integration tests for source trust scoring."""

import pytest

pytestmark = pytest.mark.asyncio


class MemorySourceTrustRepository:
    def __init__(self):
        self.scores: dict[str, int] = {}

    async def update_score(self, source_id: str, delta: int, reason: str) -> int:
        current = self.scores.get(source_id, 50)
        new_score = max(10, min(100, current + delta))
        self.scores[source_id] = new_score
        return new_score

    async def get_top_sources(self, limit: int = 10) -> list[dict]:
        sorted_sources = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        return [{"source_id": sid, "current_score": sc} for sid, sc in sorted_sources[:limit]]


async def test_confirmation_increases_score():
    """Test that recording a confirmation increases source scores."""
    from vigilancia_multiagente.application.routing.source_scorer import SourceScorerService

    repo = MemorySourceTrustRepository()
    scorer = SourceScorerService(repository=repo)

    result = await scorer.record_confirmation("source_a", "source_b")
    assert result.get("source_a_score", 0) > 50
    assert result.get("source_b_score", 0) > 50


async def test_contradiction_decreases_score():
    """Test that contradiction decreases the contradicted source's score."""
    from vigilancia_multiagente.application.routing.source_scorer import SourceScorerService

    repo = MemorySourceTrustRepository()
    repo.scores["source_a"] = 70
    repo.scores["source_b"] = 70
    scorer = SourceScorerService(repository=repo)

    result = await scorer.record_contradiction("source_a", "source_b")
    assert result["source_a_score"] < 70
    assert result["source_b_score"] > 70


async def test_preferred_sources_prioritization():
    """Test that get_preferred_sources returns high-scored sources first."""
    from vigilancia_multiagente.application.routing.source_scorer import SourceScorerService

    repo = MemorySourceTrustRepository()
    repo.scores["src_low"] = 30
    repo.scores["src_high"] = 90
    repo.scores["src_medium"] = 60
    scorer = SourceScorerService(repository=repo)

    preferred = await scorer.get_preferred_sources(limit=3)
    assert len(preferred) > 0
    assert preferred[0]["current_score"] >= preferred[-1]["current_score"]
