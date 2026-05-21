"""JsonbForensicTraceWriter — spec 007 T024 (WS-E).

Construye trazas forenses claim -> fuente -> extracto -> razonamiento -> confianza
en memoria (record_step) y las persiste en la columna JSONB `findings.forensic_trace`
al invocar `finalize`. La persistencia concreta vive en
`infra/persistence/findings_repository.py` (T024 reusa el patron del 006 que
ya escribe findings; aqui solo se ensambla la traza).

Clase concreta sin Protocol (YAGNI): escribe en columna JSONB del finding,
sin frontera externa adicional.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from vigilancia_multiagente.domain.evaluation_entities import (
    ForensicTrace,
    TraceStep,
)


class JsonbForensicTraceWriter:
    """Mantiene el buffer de TraceStep por claim_id hasta finalize().

    Las trazas viven en memoria mientras el pipeline corre; al finalizar
    el claim el writer empaqueta ForensicTrace y lo entrega para que el
    repositorio de findings lo serialice como JSONB.
    """

    def __init__(self) -> None:
        self._steps: dict[UUID, list[tuple[TraceStep, float]]] = defaultdict(list)

    async def record_step(
        self,
        claim_id: UUID,
        step: TraceStep,
        confidence: float,
    ) -> None:
        self._steps[claim_id].append((step, confidence))

    async def finalize(self, claim_id: UUID) -> ForensicTrace:
        ordered = self._steps.pop(claim_id, [])
        return ForensicTrace(
            claim_id=claim_id,
            chain=[step for step, _ in ordered],
            confidence_at_each_step=[conf for _, conf in ordered],
        )
