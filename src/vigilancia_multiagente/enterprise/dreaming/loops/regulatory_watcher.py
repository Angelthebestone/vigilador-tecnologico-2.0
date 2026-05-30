"""Loop 6 — Regulatory watcher: search by company_geo and propose with citations."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class RegulatorySearchEngine(Protocol):
    """Port for searching regulatory sources."""

    async def search_by_geo(
        self, country: str, department: str, municipality: str, sector: str
    ) -> list[dict[str, Any]]: ...


class RegulatoryProposalWriter(Protocol):
    """Port for writing regulatory proposals with citations."""

    async def write_proposal(self, finding: dict[str, Any]) -> None: ...

    async def write_uncertainty(self, topic: str, reason: str) -> None: ...


class RegulatoryWatcherLoop:
    """Searches regulatory sources by geo and generates cited proposals."""

    def __init__(
        self,
        search_engine: RegulatorySearchEngine,
        proposal_writer: RegulatoryProposalWriter,
        country: str = "",
        department: str = "",
        municipality: str = "",
        sector: str = "",
    ) -> None:
        self._search_engine = search_engine
        self._proposal_writer = proposal_writer
        self._country = country
        self._department = department
        self._municipality = municipality
        self._sector = sector

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        results = await self._search_engine.search_by_geo(
            self._country, self._department, self._municipality, self._sector
        )
        proposals = 0
        uncertainties = 0

        if results:
            for finding in results:
                if finding.get("citation"):
                    await self._proposal_writer.write_proposal(finding)
                    proposals += 1
                else:
                    await self._proposal_writer.write_uncertainty(
                        topic=finding.get("topic", "unknown"),
                        reason="No official citation available",
                    )
                    uncertainties += 1
        else:
            await self._proposal_writer.write_uncertainty(
                topic=f"{self._country}/{self._department}/{self._municipality}",
                reason="No results found from official sources",
            )
            uncertainties += 1

        return {"proposals": proposals, "uncertainties": uncertainties}
