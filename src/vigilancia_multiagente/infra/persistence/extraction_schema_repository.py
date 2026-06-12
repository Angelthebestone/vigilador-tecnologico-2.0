"""PostgresExtractionSchemaRepository — spec 007 T067.

CRUD sobre tabla `extraction_schema` con versionado.
PK compuesta: (source_type, domain, version).
"""

from __future__ import annotations

import json
from typing import cast

from sqlalchemy import text

from vigilancia_multiagente.domain.evaluation_entities import (
    ExtractionSchema,
    SourceType,
)
from vigilancia_multiagente.infra.db.connection import Database


class PostgresExtractionSchemaRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_schema(self, source_type: str, domain: str) -> ExtractionSchema:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT source_type, domain, json_schema, version"
                    " FROM extraction_schema"
                    " WHERE source_type = :source_type AND domain = :domain"
                    " ORDER BY version DESC LIMIT 1"
                ),
                {"source_type": source_type, "domain": domain},
            )
            row = result.fetchone()
            if row is None:
                raise KeyError(f"No schema for source_type={source_type!r} domain={domain!r}")
            return _row_to_schema(tuple(row))

    async def save(self, schema: ExtractionSchema) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO extraction_schema"
                    " (source_type, domain, json_schema, version)"
                    " VALUES (:source_type, :domain, :json_schema, :version)"
                    " ON CONFLICT (source_type, domain, version)"
                    " DO UPDATE SET json_schema = EXCLUDED.json_schema"
                ),
                {
                    "source_type": schema.source_type.value,
                    "domain": schema.domain,
                    "json_schema": json.dumps(schema.json_schema),
                    "version": schema.version,
                },
            )
            await db.commit()

    async def list_versions(self, source_type: str, domain: str) -> list[ExtractionSchema]:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT source_type, domain, json_schema, version"
                    " FROM extraction_schema"
                    " WHERE source_type = :source_type AND domain = :domain"
                    " ORDER BY version DESC"
                ),
                {"source_type": source_type, "domain": domain},
            )
            return [_row_to_schema(tuple(row)) for row in result.fetchall()]


def _row_to_schema(row: tuple[object, ...]) -> ExtractionSchema:
    schema_raw = row[2]
    schema_dict: dict[str, object] = {}
    if schema_raw is not None:
        if isinstance(schema_raw, dict):
            schema_dict = cast(dict[str, object], schema_raw)
        elif isinstance(schema_raw, str) and schema_raw.strip():
            schema_dict = cast(dict[str, object], json.loads(schema_raw))
    return ExtractionSchema(
        source_type=SourceType(str(row[0])),
        domain=str(row[1]),
        json_schema=schema_dict,
        version=int(cast(int, row[3])),
    )
