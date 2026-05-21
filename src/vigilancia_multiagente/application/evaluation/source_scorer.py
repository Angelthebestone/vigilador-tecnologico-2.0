"""Scorer de confianza de fuente basado en reputación *aprendida* de dominio.

DOS ESTRATEGIAS disponibles:

1. **Snapshot** (:class:`SourceScorer`): scorer síncrono sin estado de red.
   Recibe un dict ``learned_scores`` ya materializado y devuelve el score de un
   dominio o ``None``. Ideal para pipelines de fusión donde no se necesita I/O.

2. **Transactional** (:class:`SourceScorerService`): scorer async con acceso a
   repositorio. Registra confirmaciones/contradicciones entre fuentes y persiste
   los cambios en ``source_trust``. Ideal para uso en tiempo real durante la
   evaluación de hallazgos.

No hay tabla de dominios hardcodeada ni nota inicial fija: un dominio
desconocido no tiene score (``None``) y no sobrescribe la confianza que el
agente ya reportó. La reputación se construye con el tiempo a partir de
confirmaciones/contradicciones cross-session persistidas en la tabla
``source_trust`` (ver :class:`SourceScorerService` y
``infra/persistence/source_trust_repository.py``).
"""
# STATUS: ACTIVE — consumers: evidence_linker, dependencies, finding_impact_scorer, source_quality_gate

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Rango de la tabla source_trust: el score aprendido vive en [10, 100]
# (ver SourceTrustRepository.update_score). Se normaliza a [0,1] para que el
# resto del pipeline (confidence) lo consuma sin cambios.
_LEARNED_MIN = 10.0
_LEARNED_MAX = 100.0


def normalize_domain(url: str) -> str | None:
    """Dominio registrable normalizado de *url*, o ``None`` si no parsea.

    Quita ``www.`` para que ``www.foo.com`` y ``foo.com`` compartan score.
    Es la misma clave (``source_id``) con la que :class:`SourceScorerService`
    persiste el aprendizaje, así el snapshot casa por dominio.
    """
    try:
        hostname = urlparse(url).hostname or ""
    except ValueError:
        return None
    if not hostname:
        return None
    return hostname.removeprefix("www.")


@dataclass(slots=True)
class SourceScorer:
    """Devuelve el score aprendido de un dominio, o ``None`` si no hay dato.

    ``learned_scores`` mapea dominio normalizado → score en [10,100] (tal como
    lo guarda ``source_trust``). Sin entrada para el dominio, ``score`` retorna
    ``None``: el llamador NO debe sobrescribir la confianza; el dominio aún no
    tiene reputación y la nota la pone el agente que lo encontró.

    Usage:
        scorer = SourceScorer(learned_scores={"arxiv.org": 88.0})
        scorer.score("https://arxiv.org/abs/2401.12345")  # → 0.78
        scorer.score("https://unknown.example")            # → None
    """

    learned_scores: dict[str, float] = field(default_factory=dict)

    def score(self, url: str) -> float | None:
        """Score aprendido 0.0-1.0 de *url*, o ``None`` si el dominio es nuevo.

        Prueba match exacto del dominio y luego dominios padre
        (``blog.reuters.com`` → ``reuters.com``).
        """
        domain = normalize_domain(url)
        if domain is None:
            return None

        learned = self.learned_scores.get(domain)
        if learned is None:
            parts = domain.split(".")
            for i in range(1, len(parts)):
                parent = ".".join(parts[i:])
                if parent in self.learned_scores:
                    learned = self.learned_scores[parent]
                    break

        if learned is None:
            return None
        return self._to_unit(learned)

    @staticmethod
    def _to_unit(learned: float) -> float:
        span = _LEARNED_MAX - _LEARNED_MIN
        unit = (learned - _LEARNED_MIN) / span
        return max(0.0, min(1.0, unit))


class SourceScorerService:
    """Transactional scorer: persiste confirmaciones/contradicciones en source_trust.

    Usa un repositorio async para registrar interacciones entre fuentes y
    ajustar sus scores aprendidos. Sin repositorio (``None``) opera como no-op.

    Usage:
        service = SourceScorerService(repository=source_trust_repo)
        await service.record_confirmation("arxiv.org", "pubmed.com")
        await service.record_contradiction("src_a", "src_b")
        preferred = await service.get_preferred_sources(limit=5)
    """
# STATUS: ACTIVE


    CONFIRMATION_BONUS = 5
    CONTRADICTION_PENALTY = -10
    CONFIRMER_BONUS = 3

    def __init__(self, repository=None):
        self.repository = repository

    async def record_confirmation(self, source_a: str, source_b: str) -> dict:
        if self.repository is None:
            return {}
        score_a = await self.repository.update_score(
            source_a, self.CONFIRMATION_BONUS, f"Confirmed by {source_b}"
        )
        score_b = await self.repository.update_score(
            source_b, self.CONFIRMATION_BONUS, f"Confirmed {source_a}"
        )
        logger.info(f"Confirmation: {source_a} ({score_a}) confirmed by {source_b} ({score_b})")
        return {"source_a_score": score_a, "source_b_score": score_b}

    async def record_contradiction(self, source_a: str, source_b: str) -> dict:
        if self.repository is None:
            return {}
        score_a = await self.repository.update_score(
            source_a, self.CONTRADICTION_PENALTY, f"Contradicted by {source_b}"
        )
        score_b = await self.repository.update_score(
            source_b, self.CONFIRMER_BONUS, f"Contradicted {source_a}"
        )
        logger.info(f"Contradiction: {source_a} ({score_a}) contradicted by {source_b} ({score_b})")
        return {"source_a_score": score_a, "source_b_score": score_b}

    async def get_preferred_sources(self, limit: int = 5) -> list[dict]:
        if self.repository is None:
            return []
        all_sources = await self.repository.get_top_sources(limit * 2)

        high = [s for s in all_sources if s.get("current_score", 0) > 70]
        low = [s for s in all_sources if s.get("current_score", 0) <= 70]

        result = high[:limit]
        if len(result) < limit:
            result.extend(low[: limit - len(result)])

        return result
