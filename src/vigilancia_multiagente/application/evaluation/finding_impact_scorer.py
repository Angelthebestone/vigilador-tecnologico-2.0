"""Jerarquiza findings por impacto en vez de tratarlos todos por igual.

impact = autoridad_de_fuente * novedad * convergencia_multi-rama

Convierte un volcado plano de hallazgos en inteligencia priorizada: lo crítico
arriba, el ruido abajo.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from vigilancia_multiagente.domain.models import BranchResult, Finding, SourceRef

# Autoridad relativa por proveedor: fuentes académicas/patentes pesan más que
# scraping web genérico. Valores en [0,1], neutro = 0.6.
_PROVIDER_AUTHORITY: dict[str, float] = {
    "arxiv": 0.95,
    "google_scholar": 0.95,
    "serper": 0.8,
    "exa": 0.75,
    "tavily": 0.7,
    "firecrawl": 0.65,
    "brave": 0.6,
    "jina": 0.6,
}
_DEFAULT_AUTHORITY = 0.6


@dataclass(slots=True)
class ScoredFinding:
    finding: Finding
    impact: float
    authority: float
    novelty: float
    convergence: float


class FindingImpactScorer:
    """Calcula un impact score por finding combinando tres factores ya
    disponibles en el pipeline (no requiere LLM ni datos nuevos)."""

    def score(self, branch_results: list[BranchResult]) -> list[ScoredFinding]:
        sources_by_id: dict[UUID, SourceRef] = {
            source.id: source for result in branch_results for source in result.sources
        }
        topic_branches = self._topic_branch_spread(branch_results)

        scored: list[ScoredFinding] = []
        for result in branch_results:
            for finding in result.findings:
                authority = self._authority(finding, sources_by_id)
                novelty = finding.confidence
                convergence = self._convergence(finding.topic, topic_branches)
                impact = round(authority * novelty * convergence, 4)
                scored.append(
                    ScoredFinding(
                        finding=finding,
                        impact=impact,
                        authority=round(authority, 3),
                        novelty=round(novelty, 3),
                        convergence=round(convergence, 3),
                    )
                )
        scored.sort(key=lambda item: item.impact, reverse=True)
        return scored

    @staticmethod
    def _topic_branch_spread(
        branch_results: list[BranchResult],
    ) -> dict[str, set[str]]:
        spread: dict[str, set[str]] = {}
        for result in branch_results:
            for finding in result.findings:
                spread.setdefault(finding.topic, set()).add(result.branch_type.value)
        return spread

    @staticmethod
    def _authority(finding: Finding, sources_by_id: dict[UUID, SourceRef]) -> float:
        authorities = [
            _PROVIDER_AUTHORITY.get(sources_by_id[sid].provider, _DEFAULT_AUTHORITY)
            for sid in finding.source_ids
            if sid in sources_by_id
        ]
        if not authorities:
            return _DEFAULT_AUTHORITY
        return max(authorities)

    @staticmethod
    def _convergence(topic: str, topic_branches: dict[str, set[str]]) -> float:
        """Un tema confirmado por varias ramas independientes es más sólido.
        1 rama => 0.7 (neutro), escala hasta 1.0 con 3+ ramas."""
        branch_count = len(topic_branches.get(topic, ()))
        return min(1.0, 0.7 + 0.15 * max(0, branch_count - 1))
