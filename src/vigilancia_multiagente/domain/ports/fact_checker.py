"""Port WS-A: verificacion cruzada de claims contra bases externas."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import ClaimExternalValidation


@runtime_checkable
class ExternalFactChecker(Protocol):
    async def verify(self, claim: str) -> ClaimExternalValidation: ...
