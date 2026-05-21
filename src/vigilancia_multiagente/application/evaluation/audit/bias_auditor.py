"""BiasAuditor — spec 007 T023 (WS-E).

Audita sesgos geografico, de genero e institucional en los metadatos del
reporte. Si alguno supera un umbral critico, `BiasAudit.critical_bias_detected`
es True y `ReportQualityGate` bloquea la entrega (HTTP 409).

Clase concreta sin Protocol (YAGNI): calculo puro sobre metadatos ya
recolectados, sin llamadas externas.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import TYPE_CHECKING

from vigilancia_multiagente.domain.evaluation_entities import (
    BiasAudit,
    BiasThresholds,
)

if TYPE_CHECKING:
    from vigilancia_multiagente.domain.models import FinalReport, SourceRef


class BiasAuditor:
    async def audit(
        self,
        report: FinalReport,
        thresholds: BiasThresholds,
    ) -> BiasAudit:
        # Spec 007 anade `report.session_id` como FK al audit; usamos session_id
        # como `report_id` ya que un session_id <-> un FinalReport.
        sources = report.all_sources

        geo = _distribution(_iter_geographic(sources))
        gender = _distribution(_iter_gender(sources))
        institutional = _distribution(_iter_institutional(sources))

        categories: list[str] = []
        if _max_share(geo) > thresholds.geographic_max_share:
            categories.append("geographic")
        if _max_share(gender) > thresholds.gender_max_share:
            categories.append("gender")
        if _max_share(institutional) > thresholds.institutional_max_share:
            categories.append("institutional")

        return BiasAudit(
            report_id=report.session_id,
            geographic_distribution=geo,
            gender_distribution=gender,
            institutional_distribution=institutional,
            critical_bias_detected=bool(categories),
            bias_categories=categories,
        )


def _distribution(values: Iterable[str]) -> dict[str, float]:
    counter = Counter(v for v in values if v)
    total = sum(counter.values())
    if total == 0:
        return {}
    return {key: round(count / total, 4) for key, count in counter.items()}


def _max_share(distribution: dict[str, float]) -> float:
    return max(distribution.values(), default=0.0)


def _iter_geographic(sources: list[SourceRef]) -> Iterable[str]:
    for source in sources:
        # Pista pragmatica: ccTLD del proveedor (`.uk`, `.de`, `.cn`, ...).
        # Sin metadatos geograficos estructurados disponibles en el modelo
        # actual; cuando WS-A los enriquezca con AuthorReputation se puede
        # extender. POLA: lo que no se sabe, no se inventa.
        host = source.url.lower()
        if ".uk" in host:
            yield "UK"
        elif ".de" in host:
            yield "DE"
        elif ".cn" in host:
            yield "CN"
        elif ".jp" in host:
            yield "JP"
        elif ".com" in host or ".org" in host or ".edu" in host:
            yield "US"


def _iter_gender(_sources: list[SourceRef]) -> Iterable[str]:
    # Sin senal de genero en el modelo actual; placeholder hasta que WS-A
    # publique `AuthorReputation.display_name` enriquecido. Devolver vacio
    # mantiene `max_share = 0` y nunca dispara critico.
    return iter(())


def _iter_institutional(sources: list[SourceRef]) -> Iterable[str]:
    for source in sources:
        host = source.url.lower()
        if ".edu" in host or "arxiv" in host or "pubmed" in host:
            yield "academic"
        elif ".gov" in host:
            yield "government"
        else:
            yield "industry"
