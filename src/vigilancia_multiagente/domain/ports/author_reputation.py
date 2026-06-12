"""Port WS-A: lookup de reputacion del autor en bases bibliometricas externas."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import AuthorReputation


@runtime_checkable
class AuthorReputationGateway(Protocol):
    async def lookup(self, author_id: str) -> AuthorReputation | None:
        """Retorna None si la fuente externa no responde (degradacion controlada)."""
        ...

    async def search_by_name(self, name: str, limit: int = 5) -> list[AuthorReputation]: ...

    async def refresh(self, author_id: str) -> AuthorReputation: ...
