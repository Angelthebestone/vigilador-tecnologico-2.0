import logging

logger = logging.getLogger(__name__)


class SourceScorerService:
    CONFIRMATION_BONUS = 5
    CONTRADICTION_PENALTY = -10
    CONFIRMER_BONUS = 3

    def __init__(self, repository=None):
        self.repository = repository

    async def record_confirmation(self, source_a: str, source_b: str) -> dict:
        score_a = await self.repository.update_score(
            source_a, self.CONFIRMATION_BONUS, f"Confirmed by {source_b}"
        )
        score_b = await self.repository.update_score(
            source_b, self.CONFIRMATION_BONUS, f"Confirmed {source_a}"
        )
        logger.info(f"Confirmation: {source_a} ({score_a}) confirmed by {source_b} ({score_b})")
        return {"source_a_score": score_a, "source_b_score": score_b}

    async def record_contradiction(self, source_a: str, source_b: str) -> dict:
        score_a = await self.repository.update_score(
            source_a, self.CONTRADICTION_PENALTY, f"Contradicted by {source_b}"
        )
        score_b = await self.repository.update_score(
            source_b, self.CONFIRMER_BONUS, f"Contradicted {source_a}"
        )
        logger.info(f"Contradiction: {source_a} ({score_a}) contradicted by {source_b} ({score_b})")
        return {"source_a_score": score_a, "source_b_score": score_b}

    async def get_preferred_sources(self, limit: int = 5) -> list[dict]:
        all_sources = await self.repository.get_top_sources(limit * 2)

        high = [s for s in all_sources if s.get("current_score", 0) > 70]
        low = [s for s in all_sources if s.get("current_score", 0) <= 70]

        result = high[:limit]
        if len(result) < limit:
            result.extend(low[: limit - len(result)])

        return result
