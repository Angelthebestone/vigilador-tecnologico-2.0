"""PostgresTemporalDecayConfigRepository — spec 007 T048.

Persiste configuraciones de decaimiento temporal por dominio y tipo de fuente
en tabla `temporal_decay_config`. Sirve a `TemporalDecayConfigStore` Protocol.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import text

from vigilancia_multiagente.domain.evaluation_entities import (
    SourceType,
    TemporalDecayConfig,
)
from vigilancia_multiagente.infra.db.connection import Database

_DEFAULT_HALF_LIFE = 12


class PostgresTemporalDecayConfigRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, domain: str, source_type: str) -> TemporalDecayConfig:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT domain, source_type, half_life_months"
                    " FROM temporal_decay_config"
                    " WHERE domain = :domain AND source_type = :source_type"
                ),
                {"domain": domain, "source_type": source_type},
            )
            row = result.fetchone()
            if row is not None:
                return TemporalDecayConfig(
                    domain=str(row[0]),
                    source_type=SourceType(str(row[1])),
                    half_life_months=int(cast(int, row[2])),
                )
        return TemporalDecayConfig(
            domain=domain,
            source_type=SourceType(source_type),
            half_life_months=_DEFAULT_HALF_LIFE,
        )

    async def upsert(self, config: TemporalDecayConfig) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO temporal_decay_config (domain, source_type, half_life_months)"
                    " VALUES (:domain, :source_type, :half_life_months)"
                    " ON CONFLICT (domain, source_type) DO UPDATE SET"
                    "  half_life_months = EXCLUDED.half_life_months"
                ),
                {
                    "domain": config.domain,
                    "source_type": config.source_type.value,
                    "half_life_months": config.half_life_months,
                },
            )
            await db.commit()
