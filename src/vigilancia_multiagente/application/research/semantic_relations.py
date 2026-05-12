from dataclasses import dataclass
from math import sqrt
from uuid import UUID


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


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding vectors must have the same size")
    numerator = sum(x * y for x, y in zip(left, right, strict=True))
    left_norm = sqrt(sum(x * x for x in left))
    right_norm = sqrt(sum(y * y for y in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


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

