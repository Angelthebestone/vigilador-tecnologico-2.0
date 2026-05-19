"""Scorer de confianza de fuente basado en reputación *aprendida* de dominio.

No hay tabla de dominios hardcodeada ni nota inicial fija: un dominio
desconocido no tiene score (``None``) y no sobrescribe la confianza que el
agente ya reportó. La reputación se construye con el tiempo a partir de
confirmaciones/contradicciones cross-session persistidas en la tabla
``source_trust`` (ver :class:`SourceScorerService` y
``infra/persistence/source_trust_repository.py``).

El scorer es síncrono y sin estado de red: recibe un snapshot de los scores
aprendidos (``learned_scores``) ya materializado por quien lo construye. Las
rutas que lo usan cargan ese snapshot async desde el repositorio antes de
invocarlo, de modo que ``deduplicate_sources`` y el quality gate siguen siendo
síncronos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

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
