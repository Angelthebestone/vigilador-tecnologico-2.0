"""Scorer de confianza de fuente basado en reputación *aprendida* de dominio.
...
"""
# STATUS: ACTIVE — consumers: evidence_linker, dependencies, finding_impact_scorer, source_quality_gate

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.ports.temporal_decay import TemporalDecayConfigStore

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

    ``authenticity_signals`` (opcional): dict url -> effective_freshness para
    ajuste multiplicativo cuando WS-B esta activo.

    Usage:
        scorer = SourceScorer(learned_scores={"arxiv.org": 88.0})
        scorer.score("https://arxiv.org/abs/2401.12345")  # → 0.78
        scorer.score("https://unknown.example")            # → None
    """

    learned_scores: dict[str, float] = field(default_factory=dict)
    authenticity_signals: dict[str, float] | None = None

    def score(self, url: str) -> float | None:
        """Score aprendido 0.0-1.0 de *url*, o ``None`` si el dominio es nuevo.

        Prueba match exacto del dominio y luego dominios padre
        (``blog.reuters.com`` → ``reuters.com``). Cuando WS-B activo,
        multiplica por ``effective_freshness`` del signal correspondiente.
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
        base = self._to_unit(learned)

        if self.authenticity_signals:
            eff = self.authenticity_signals.get(url) or self.authenticity_signals.get(
                str(domain)
            )
            if isinstance(eff, (int, float)):
                return base * min(1.0, max(0.0, float(eff)))

        return base

    @staticmethod
    def _to_unit(learned: float) -> float:
        span = _LEARNED_MAX - _LEARNED_MIN
        unit = (learned - _LEARNED_MIN) / span
        return max(0.0, min(1.0, unit))


class SourceScorerService:
    """Transactional scorer: persiste confirmaciones/contradicciones en source_trust.

    Usa un repositorio async para registrar interacciones entre fuentes y
    ajustar sus scores aprendidos. Sin repositorio (``None``) opera como no-op.

    Spec 007 T060: cuando WS-A activo, los pesos fijos CONFIRMATION_BONUS,
    CONTRADICTION_PENALTY, CONFIRMER_BONUS pasan a leerse de TemporalDecayConfig
    por dominio. Mantener los valores hardcodeados como fallback cuando el
    flag esta off.

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

    def __init__(
        self,
        repository=None,
        temporal_decay_store: TemporalDecayConfigStore | None = None,
    ) -> None:
        self.repository = repository
        self._temporal_decay_store = temporal_decay_store
        self._ws_a_enabled = get_settings().eval_ws_a_enabled

    async def _get_weights(self, domain: str = "general") -> dict[str, int]:
        if not self._ws_a_enabled or self._temporal_decay_store is None:
            return {
                "confirmation_bonus": self.CONFIRMATION_BONUS,
                "contradiction_penalty": self.CONTRADICTION_PENALTY,
                "confirmer_bonus": self.CONFIRMER_BONUS,
            }
        try:
            config = await self._temporal_decay_store.get(domain, "paper")
            factor = max(1, config.half_life_months // 12)
            return {
                "confirmation_bonus": self.CONFIRMATION_BONUS * factor,
                "contradiction_penalty": self.CONTRADICTION_PENALTY * factor,
                "confirmer_bonus": self.CONFIRMER_BONUS * factor,
            }
        except Exception:
            return {
                "confirmation_bonus": self.CONFIRMATION_BONUS,
                "contradiction_penalty": self.CONTRADICTION_PENALTY,
                "confirmer_bonus": self.CONFIRMER_BONUS,
            }

    async def record_confirmation(
        self, source_a: str, source_b: str, domain: str = "general"
    ) -> dict:
        if self.repository is None:
            return {}
        weights = await self._get_weights(domain)
        score_a = await self.repository.update_score(
            source_a, weights["confirmation_bonus"], f"Confirmed by {source_b}"
        )
        score_b = await self.repository.update_score(
            source_b, weights["confirmation_bonus"], f"Confirmed {source_a}"
        )
        logger.info(f"Confirmation: {source_a} ({score_a}) confirmed by {source_b} ({score_b})")
        return {"source_a_score": score_a, "source_b_score": score_b}

    async def record_contradiction(
        self, source_a: str, source_b: str, domain: str = "general"
    ) -> dict:
        if self.repository is None:
            return {}
        weights = await self._get_weights(domain)
        score_a = await self.repository.update_score(
            source_a, weights["contradiction_penalty"], f"Contradicted by {source_b}"
        )
        score_b = await self.repository.update_score(
            source_b, weights["confirmer_bonus"], f"Contradicted {source_a}"
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
