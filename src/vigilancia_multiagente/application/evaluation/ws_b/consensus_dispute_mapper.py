"""ConsensusDisputeMapper — spec 007 T074.

Implementa ConsensusDisputeMapper reusando ContradictionAnalyzer + embeddings + triangulacion.
"""

from __future__ import annotations

import logging
from typing import Any

from vigilancia_multiagente.application.evaluation.contradiction_analyzer import (
    ContradictionAnalyzer,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    ConsensusDisputeMap,
    EvidenceStrength,
)
from vigilancia_multiagente.domain.models import Finding
from vigilancia_multiagente.domain.ports.consensus_dispute import ConsensusDisputeMapper
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway, TaskType

logger = logging.getLogger(__name__)


class ConsensusDisputeMapperImpl:
    def __init__(
        self,
        contradiction_analyzer: ContradictionAnalyzer | None = None,
        embedding_gateway: EmbeddingGateway | None = None,
    ) -> None:
        self._analyzer = contradiction_analyzer or ContradictionAnalyzer()
        self._embedding_gateway = embedding_gateway

    async def build(self, findings: list[Finding]) -> list[ConsensusDisputeMap]:
        if len(findings) < 2:
            return []

        lex_report = self._analyzer.analyze(findings)
        maps: list[ConsensusDisputeMap] = []

        for disputed in lex_report.disputed_points:
            maps.append(
                ConsensusDisputeMap(
                    claim=disputed.statement_a,
                    supporting_sources=[_source_id(disputed)],
                    contradicting_sources=[],
                    evidence_strength=EvidenceStrength.WEAK,
                )
            )

        if self._embedding_gateway is not None and len(findings) >= 3:
            emb_maps = await self._triangulate(findings)
            maps.extend(emb_maps)

        return maps

    async def _triangulate(
        self, findings: list[Finding]
    ) -> list[ConsensusDisputeMap]:
        maps: list[ConsensusDisputeMap] = []
        texts = [f"{f.topic} {f.statement}" for f in findings]

        try:
            vectors = await self._embedding_gateway.embed_documents(texts)
        except Exception as exc:
            logger.warning("Embedding failed during triangulation: %s", exc)
            return []

        import math

        for i in range(len(findings)):
            for j in range(i + 1, len(findings)):
                dot = sum(
                    a * b for a, b in zip(vectors[i], vectors[j], strict=False)
                )
                ni = math.sqrt(sum(x * x for x in vectors[i]))
                nj = math.sqrt(sum(y * y for y in vectors[j]))
                sim = dot / (ni * nj) if ni * nj > 0 else 0

                if sim < 0.3:
                    maps.append(
                        ConsensusDisputeMap(
                            claim=f"{findings[i].topic} — {findings[i].statement}",
                            supporting_sources=findings[i].source_ids,
                            contradicting_sources=findings[j].source_ids,
                            evidence_strength=EvidenceStrength.MODERATE,
                            resolution="Low semantic similarity suggests different claims or stances.",
                        )
                    )

        return maps


def _source_id(disputed: Any) -> Any:
    return getattr(disputed, "source_id", None)
