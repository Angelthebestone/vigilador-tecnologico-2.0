"""Port WS-B: mapas de consenso y disputa sobre findings."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import ConsensusDisputeMap
from vigilancia_multiagente.domain.models import Finding


@runtime_checkable
class ConsensusDisputeMapper(Protocol):
    async def build(self, findings: list[Finding]) -> list[ConsensusDisputeMap]: ...
