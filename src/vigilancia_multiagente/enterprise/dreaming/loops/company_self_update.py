"""Loop 5 — COMPANY self-update: detect gaps and propose config additions."""

from __future__ import annotations

from typing import Any, Protocol

from vigilancia_multiagente.enterprise.dreaming.models import DreamingContext


class CompanyGapDetector(Protocol):
    """Port for detecting knowledge gaps in COMPANY config."""

    async def detect(self, tenant_id: str) -> list[dict[str, Any]]: ...


class CompanyProposalGenerator(Protocol):
    """Port for generating COMPANY config proposals via LLM."""

    async def generate(self, gap: dict[str, Any]) -> dict[str, Any]: ...


class CompanyModifier(Protocol):
    """Port for applying COMPANY config changes via AgentModifier."""

    async def apply(self, proposal: dict[str, Any]) -> None: ...


class CompanySelfUpdateLoop:
    """Detects COMPANY gaps and generates proposals via AgentModifier."""

    def __init__(
        self,
        gap_detector: CompanyGapDetector,
        proposal_generator: CompanyProposalGenerator,
        modifier: CompanyModifier,
    ) -> None:
        self._gap_detector = gap_detector
        self._proposal_generator = proposal_generator
        self._modifier = modifier

    async def run(self, context: DreamingContext) -> dict[str, Any]:
        gaps = await self._gap_detector.detect(context.tenant_id)
        proposals_applied = 0

        for gap in gaps:
            proposal = await self._proposal_generator.generate(gap)
            await self._modifier.apply(proposal)
            proposals_applied += 1

        return {"gaps_detected": len(gaps), "proposals_applied": proposals_applied}
