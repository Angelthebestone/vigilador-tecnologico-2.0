"""Criterio de parada por saturación semántica.

Mide la ganancia marginal de información: si una iteración es semánticamente
casi idéntica a las anteriores ya no se aprende nada nuevo y conviene parar,
en vez de agotar un depth_limit fijo.
"""

from __future__ import annotations

from vigilancia_multiagente.application.research.semantic_relations import cosine_similarity

# Por encima de esta similitud con una iteración previa, la nueva no aportó
# información nueva apreciable.
_SATURATION_SIMILARITY = 0.93


def is_saturated(
    new_vector: list[float],
    prior_vectors: list[list[float]],
    threshold: float = _SATURATION_SIMILARITY,
) -> bool:
    """True si *new_vector* es redundante frente a cualquier iteración previa.

    Compara contra todas las anteriores (no solo la última) porque una
    investigación puede oscilar entre dos sub-temas sin progresar.
    """
    return any(cosine_similarity(new_vector, prior) >= threshold for prior in prior_vectors)


def information_gain(
    new_vector: list[float],
    prior_vectors: list[list[float]],
) -> float:
    """Ganancia marginal en [0,1]: 1 = totalmente nuevo, 0 = duplicado exacto."""
    if not prior_vectors:
        return 1.0
    max_sim = max(cosine_similarity(new_vector, prior) for prior in prior_vectors)
    return round(max(0.0, 1.0 - max_sim), 6)


class SaturationTracker:
    """Embebe la iteración una sola vez y cachea el vector por índice.

    El mismo vector sirve para (a) decidir saturación durante el loop y
    (b) construir relaciones semánticas después, evitando re-embeber el mismo
    texto dos veces contra la API de embeddings.
    """

    def __init__(self, embed_document, threshold: float = _SATURATION_SIMILARITY) -> None:
        self._embed_document = embed_document
        self._threshold = threshold
        self._vectors_by_index: dict[int, list[float]] = {}

    async def is_saturated(self, index: int, text: str) -> bool:
        """True si la iteración *index* (texto *text*) no aporta novedad.

        Resiliente: cualquier fallo de embedding => no satura, preservando el
        comportamiento de parar solo por depth/confianza.
        """
        if not text:
            return False
        try:
            vector = await self._embed_document(text)
        except Exception:
            return False
        prior = list(self._vectors_by_index.values())
        self._vectors_by_index[index] = vector
        return is_saturated(vector, prior, self._threshold)

    def vector_for(self, index: int) -> list[float] | None:
        return self._vectors_by_index.get(index)
