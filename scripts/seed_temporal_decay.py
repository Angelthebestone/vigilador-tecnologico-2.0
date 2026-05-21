#!/usr/bin/env python3
"""Seed TemporalDecayConfig — spec 007 T049.

Inserta configuraciones de decaimiento temporal por dominio tecnologico.
Ejecutar manualmente::

    python scripts/seed_temporal_decay.py

Usa las mismas env vars que el backend (VT_DATABASE_URL). Requiere que
la tabla `temporal_decay_config` exista (migration 005 aplicada).
"""

from __future__ import annotations

import asyncio
import logging

from vigilancia_multiagente.domain.evaluation_entities import SourceType, TemporalDecayConfig
from vigilancia_multiagente.infra.db.connection import Database
from vigilancia_multiagente.infra.persistence.temporal_decay_repository import (
    PostgresTemporalDecayConfigRepository,
)

logger = logging.getLogger(__name__)

# Half-life por dominio (AI=12 meses, MATH=60, BIO=24, NANO=18,
# QUANTUM=36, ENERGY=24, MATERIALS=24, general=12)
_DOMAIN_HALF_LIVES: dict[str, int] = {
    "AI": 12,
    "MATH": 60,
    "BIO": 24,
    "NANO": 18,
    "QUANTUM": 36,
    "ENERGY": 24,
    "MATERIALS": 24,
    "general": 12,
}

_SOURCE_TYPES = [SourceType.PAPER, SourceType.PATENT, SourceType.NEWS, SourceType.BLOG]


async def _seed() -> None:
    database = Database()
    repo = PostgresTemporalDecayConfigRepository(database)

    total = 0
    for domain, half_life in _DOMAIN_HALF_LIVES.items():
        for source_type in _SOURCE_TYPES:
            config = TemporalDecayConfig(
                domain=domain,
                half_life_months=half_life,
                source_type=source_type,
            )
            await repo.upsert(config)
            total += 1

    await database.dispose()
    logger.info("Seeded %d temporal decay configs across %d domains", total, len(_DOMAIN_HALF_LIVES))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
