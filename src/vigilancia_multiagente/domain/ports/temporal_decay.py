"""Port WS-A: configuracion del decaimiento temporal por dominio y tipo de fuente."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import TemporalDecayConfig


@runtime_checkable
class TemporalDecayConfigStore(Protocol):
    async def get(self, domain: str, source_type: str) -> TemporalDecayConfig: ...

    async def upsert(self, config: TemporalDecayConfig) -> None: ...
