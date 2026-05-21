"""Port WS-B: expansion contextual de queries aprendiendo de iteraciones previas.

`PriorIterationView` es una vista minima de una iteracion del followup loop
declarada en el port para evitar acoplarse a `IterationResult` (que vive en
`application/`). Los adapters consumen solo `query` y `query_type` — el
TypedDict mantiene el tipo estricto sin importar capas superiores.
"""

from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable


class PriorIterationView(TypedDict):
    query: str
    query_type: str


@runtime_checkable
class ContextualQueryExpander(Protocol):
    async def expand(
        self,
        base_query: str,
        prior_iterations: list[PriorIterationView],
    ) -> list[str]: ...
