# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Phase 6 — Regulatory/local watch: search official sources by company_geo."""

from __future__ import annotations

import time
from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)


class GeoConfig(Protocol):
    """Port for reading company geographic configuration."""

    @property
    def country(self) -> str: ...

    @property
    def department(self) -> str: ...

    @property
    def municipality(self) -> str: ...

    @property
    def sector(self) -> str: ...


class RegulatorySourceSearcher(Protocol):
    """Port for searching official regulatory sources."""

    async def search(self, query: str) -> list[dict[str, Any]]: ...


class RegulatoryProposalStore(Protocol):
    """Port for storing regulatory change proposals."""

    async def store_proposal(self, proposal: dict[str, Any]) -> None: ...

    async def store_uncertainty(self, topic: str, reason: str) -> None: ...


class RegulatoryWatchPhase:
    """Searches official sources for regulatory changes relevant to company_geo."""

    def __init__(
        self,
        geo_config: GeoConfig,
        searcher: RegulatorySourceSearcher,
        proposal_store: RegulatoryProposalStore,
    ) -> None:
        self._geo_config = geo_config
        self._searcher = searcher
        self._proposal_store = proposal_store

    @property
    def name(self) -> str:
        return "regulatory_watch"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        if not context.llm_available:
            return PhaseResult(
                phase_name=self.name,
                status=PhaseStatus.SKIPPED,
                duration_ms=0.0,
                error="LLM not available",
            )

        t0 = time.perf_counter()
        queries = self._build_queries()
        proposals_count = 0
        uncertainties_count = 0

        for query in queries:
            results = await self._searcher.search(query)
            if results:
                for result in results:
                    await self._proposal_store.store_proposal(
                        {
                            "query": query,
                            "source": result.get("source", ""),
                            "citation": result.get("citation", ""),
                            "summary": result.get("summary", ""),
                            "consulted_at": context.started_at.isoformat(),
                        }
                    )
                    proposals_count += 1
            else:
                await self._proposal_store.store_uncertainty(
                    topic=query,
                    reason="No official source found with sufficient information",
                )
                uncertainties_count += 1

        duration_ms = (time.perf_counter() - t0) * 1000
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict={
                "queries_executed": len(queries),
                "proposals": proposals_count,
                "uncertainties": uncertainties_count,
            },
        )

    def _build_queries(self) -> list[str]:
        geo = self._geo_config
        base = f"{geo.country} {geo.department} {geo.municipality}"
        return [
            f"{base} normativa {geo.sector}",
            f"{base} impuestos municipales",
            f"{base} regulacion vigente",
        ]
