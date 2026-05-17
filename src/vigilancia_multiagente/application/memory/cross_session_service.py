"""Service for cross-session memory retrieval and merging."""

import logging
from difflib import SequenceMatcher

from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
from vigilancia_multiagente.infra.persistence.global_knowledge_repository import (
    GlobalKnowledgeRepository,
)

logger = logging.getLogger(__name__)


class CrossSessionService:
    """Service that preloads related prior knowledge into new research sessions
    and merges new findings back into the global knowledge store."""

    def __init__(
        self,
        repository: GlobalKnowledgeRepository | None = None,
        embedding_gateway: GeminiEmbeddingGateway | None = None,
    ) -> None:
        self.repository = repository
        self.embedding_gateway = embedding_gateway

    async def preload_session(self, query: str) -> dict:
        """Query cross-session memory for related prior research.

        Returns:
            dict with:
              - related_sessions: list of prior session summaries with similarity scores
              - recurring_entities: entities that appear across multiple related sessions
              - coverage_gaps: topics identified as gaps in prior sessions
        """
        if self.embedding_gateway is None or self.repository is None:
            return {"related_sessions": [], "recurring_entities": [], "coverage_gaps": []}

        try:
            query_embedding = await self.embedding_gateway.embed_document(query)
        except Exception as exc:
            logger.warning("Failed to generate embedding for cross-session preload: %s", exc)
            return {"related_sessions": [], "recurring_entities": [], "coverage_gaps": []}

        related = await self.repository.find_related(query_embedding, limit=5)

        if not related:
            return {"related_sessions": [], "recurring_entities": [], "coverage_gaps": []}

        seen_entities: set[str] = set()
        for session in related:
            summary = session.get("query_summary", "")
            tokens = summary.lower().split()
            for token in tokens:
                cleaned = token.strip(".,;:!?()[]")
                if cleaned and len(cleaned) > 3 and cleaned not in seen_entities:
                    seen_entities.add(cleaned)

        return {
            "related_sessions": related,
            "recurring_entities": list(seen_entities)[:20],
            "coverage_gaps": [],
        }

    async def merge_findings(
        self,
        current_findings: list[dict],
        prior_findings: list[dict],
    ) -> dict:
        """Merge new findings with prior findings, detecting duplicates and contradictions.

        Args:
            current_findings: Findings from the current session
            prior_findings: Findings from related prior sessions

        Returns:
            dict with:
              - merged: deduplicated combined findings
              - contradictions: list of conflicting claim pairs with annotation
              - duplicates: findings that already existed
        """
        SIMILARITY_THRESHOLD = 0.75

        merged = list(current_findings)
        duplicates: list[dict] = []
        contradictions: list[dict] = []

        for prior in prior_findings:
            prior_stmt = prior.get("statement", "")
            prior_topic = prior.get("topic", "")

            is_duplicate = False
            for current in current_findings:
                curr_stmt = current.get("statement", "")
                similarity = SequenceMatcher(None, prior_stmt, curr_stmt).ratio()

                if similarity >= SIMILARITY_THRESHOLD:
                    if prior_topic and prior_topic == current.get("topic", ""):
                        duplicates.append({**prior, "matched_with": str(current.get("id", ""))})
                        is_duplicate = True
                        break

                    if _is_contradictory(prior, current):
                        contradictions.append(
                            {
                                "claim_a": prior,
                                "claim_b": current,
                                "annotation": "contradiction",
                            }
                        )
                        is_duplicate = True
                        break

            if not is_duplicate:
                merged.append({**prior, "_prior": True})

        return {
            "merged": merged,
            "contradictions": contradictions,
            "duplicates": duplicates,
        }


def _is_contradictory(a: dict, b: dict) -> bool:
    import re

    a_nums = re.findall(r"\d+\.?\d*", a.get("statement", ""))
    b_nums = re.findall(r"\d+\.?\d*", b.get("statement", ""))
    if a.get("topic") == b.get("topic") and a_nums and b_nums:
        return set(a_nums) != set(b_nums)
    return False
