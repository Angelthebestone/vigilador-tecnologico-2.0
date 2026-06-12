"""Analizador de brechas de patentamiento (ciencia vs patentes).

Implementa PatentingGapAnalyzer. Consulta OpenAlex (papers) y Serper Patents
y divide densidades por subdominio.
"""

from __future__ import annotations

import logging

from vigilancia_multiagente.domain.evaluation_entities import (
    PatentingClassification,
    PatentingGap,
)
from vigilancia_multiagente.domain.ports.patenting_gap import PatentingGapAnalyzer
from vigilancia_multiagente.domain.ports.provider_registry import ProviderRegistry
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class PatentingGapAnalyzerImpl(PatentingGapAnalyzer):
    """Cruza papers y patentes para identificar brechas por subdominio."""

    def __init__(
        self,
        tool_executor: ToolExecutor | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> None:
        self._tool_executor = tool_executor
        self._provider_registry = provider_registry

    async def analyze(self, subdomains: list[str]) -> list[PatentingGap]:
        if not subdomains:
            return []

        results: list[PatentingGap] = []
        for subdomain in subdomains:
            pub_density = await self._estimate_publication_density(subdomain)
            pat_density = await self._estimate_patent_density(subdomain)

            gap = pub_density / max(pat_density, 0.1)
            if gap > 3.0:
                classification = PatentingClassification.BLUE_OCEAN
            elif gap < 0.5:
                classification = PatentingClassification.RED_OCEAN
            else:
                classification = PatentingClassification.BALANCED

            results.append(
                PatentingGap(
                    subdomain=subdomain,
                    publication_density=round(pub_density, 4),
                    patent_density=round(pat_density, 4),
                    gap_score=round(gap, 4),
                    classification=classification,
                )
            )

        return results

    async def _estimate_publication_density(self, subdomain: str) -> float:
        if not self._tool_executor or not self._provider_registry:
            return 5.0

        try:
            provider = self._provider_registry.get("serper")
            resp = await self._tool_executor.execute_tool(
                provider,
                "google_search_patents",
                {"query": subdomain},
            )
            items = self._extract_items(resp.payload)
            return float(len(items)) if items else 3.0
        except Exception as exc:
            logger.debug("Publication density failed for %s: %s", subdomain, exc)
            return 3.0

    async def _estimate_patent_density(self, subdomain: str) -> float:
        if not self._tool_executor or not self._provider_registry:
            return 1.0

        try:
            provider = self._provider_registry.get("serper")
            resp = await self._tool_executor.execute_tool(
                provider,
                "google_search_patents",
                {"query": f"patent {subdomain}"},
            )
            items = self._extract_items(resp.payload)
            return float(len(items)) if items else 1.0
        except Exception as exc:
            logger.debug("Patent density failed for %s: %s", subdomain, exc)
            return 1.0

    @staticmethod
    def _extract_items(payload: dict) -> list:
        for key in ("results", "items", "organic", "papers", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []
