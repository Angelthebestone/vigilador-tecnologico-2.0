"""Port WS-B: normalizador multilingue (deteccion + traduccion + distribucion)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.models import SourceRef


@runtime_checkable
class MultilingualNormalizer(Protocol):
    async def detect_language(self, text: str) -> str: ...

    async def translate(self, text: str, target: str = "en") -> str: ...

    async def language_distribution(
        self, sources: list[SourceRef]
    ) -> dict[str, float]: ...
