"""Port WS-B: registro de esquemas pydantic por (source_type, domain)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vigilancia_multiagente.domain.evaluation_entities import ExtractionSchema


@runtime_checkable
class ExtractionSchemaRegistry(Protocol):
    def get_schema(self, source_type: str, domain: str) -> ExtractionSchema: ...

    def validate(
        self, raw: dict[str, object], schema: ExtractionSchema
    ) -> dict[str, object]: ...
