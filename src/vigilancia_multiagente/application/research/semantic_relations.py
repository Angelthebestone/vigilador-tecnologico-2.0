from dataclasses import dataclass
from uuid import UUID

from vigilancia_multiagente.shared.math_utils import cosine_similarity


@dataclass(slots=True, frozen=True)
class IterationEmbedding:
    iteration_id: UUID
    vector: list[float]


@dataclass(slots=True, frozen=True)
class SemanticRelation:
    source_iteration_id: UUID
    target_iteration_id: UUID
    relation_type: str
    similarity_score: float


def build_relations(
    embeddings: list[IterationEmbedding],
    duplicate_threshold: float = 0.92,
    support_threshold: float = 0.75,
) -> list[SemanticRelation]:
    relations: list[SemanticRelation] = []
    for i, source in enumerate(embeddings):
        for target in embeddings[i + 1 :]:
            similarity = cosine_similarity(source.vector, target.vector)
            if similarity >= duplicate_threshold:
                relation_type = "DUPLICATES"
            elif similarity >= support_threshold:
                relation_type = "SUPPORTS"
            else:
                continue
            relations.append(
                SemanticRelation(
                    source_iteration_id=source.iteration_id,
                    target_iteration_id=target.iteration_id,
                    relation_type=relation_type,
                    similarity_score=round(similarity, 6),
                )
            )
    return relations
