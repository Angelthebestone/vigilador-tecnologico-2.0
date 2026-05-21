"""Port WS-C: mapeo de dependencias criticas (materiales, librerias, vendors, regulaciones)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import CriticalDependency
from vigilancia_multiagente.domain.models import Finding


@runtime_checkable
class CriticalDependencyMapper(Protocol):
    async def map(
        self,
        technology: str,
        findings: list[Finding],
    ) -> list[CriticalDependency]: ...
