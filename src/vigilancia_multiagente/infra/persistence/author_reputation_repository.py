"""PostgresAuthorReputationRepository — spec 007 T047.

CRUD sobre tabla `author_reputation` con validacion de frescura de datos
(> 30d se considera stale y requiere re-consulta).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import text

from vigilancia_multiagente.domain.evaluation_entities import (
    AffiliationType,
    AuthorReputation,
)
from vigilancia_multiagente.infra.db.connection import Database

_STALE_DAYS = 30


class PostgresAuthorReputationRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def lookup(self, author_id: str) -> AuthorReputation | None:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT author_id, display_name, h_index, total_citations,"
                    " retraction_count, primary_affiliation, affiliation_type,"
                    " domain_weights, last_refreshed FROM author_reputation"
                    " WHERE author_id = :author_id"
                ),
                {"author_id": author_id},
            )
            row = result.fetchone()
            if row is None:
                return None
            return _row_to_reputation(tuple(row))

    async def search_by_name(self, name: str, limit: int = 5) -> list[AuthorReputation]:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT author_id, display_name, h_index, total_citations,"
                    " retraction_count, primary_affiliation, affiliation_type,"
                    " domain_weights, last_refreshed FROM author_reputation"
                    " WHERE display_name ILIKE :pattern"
                    " ORDER BY h_index DESC LIMIT :limit"
                ),
                {"pattern": f"%{name}%", "limit": limit},
            )
            return [_row_to_reputation(tuple(row)) for row in result.fetchall()]

    async def upsert(self, reputation: AuthorReputation) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO author_reputation"
                    " (author_id, display_name, h_index, total_citations,"
                    "  retraction_count, primary_affiliation, affiliation_type,"
                    "  domain_weights, last_refreshed)"
                    " VALUES (:author_id, :display_name, :h_index, :total_citations,"
                    "         :retraction_count, :primary_affiliation, :affiliation_type,"
                    "         :domain_weights, :last_refreshed)"
                    " ON CONFLICT (author_id) DO UPDATE SET"
                    "  display_name = EXCLUDED.display_name,"
                    "  h_index = EXCLUDED.h_index,"
                    "  total_citations = EXCLUDED.total_citations,"
                    "  retraction_count = EXCLUDED.retraction_count,"
                    "  primary_affiliation = EXCLUDED.primary_affiliation,"
                    "  affiliation_type = EXCLUDED.affiliation_type,"
                    "  domain_weights = EXCLUDED.domain_weights,"
                    "  last_refreshed = EXCLUDED.last_refreshed"
                ),
                {
                    "author_id": reputation.author_id,
                    "display_name": reputation.display_name,
                    "h_index": reputation.h_index,
                    "total_citations": reputation.total_citations,
                    "retraction_count": reputation.retraction_count,
                    "primary_affiliation": reputation.primary_affiliation,
                    "affiliation_type": reputation.affiliation_type.value,
                    "domain_weights": json.dumps(reputation.domain_weights),
                    "last_refreshed": reputation.last_refreshed,
                },
            )
            await db.commit()

    async def refresh(self, author_id: str) -> AuthorReputation:
        """Refresca devolviendo la entrada actualizada en DB."""
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "UPDATE author_reputation SET last_refreshed = NOW()"
                    " WHERE author_id = :author_id"
                    " RETURNING author_id, display_name, h_index, total_citations,"
                    " retraction_count, primary_affiliation, affiliation_type,"
                    " domain_weights, last_refreshed"
                ),
                {"author_id": author_id},
            )
            row = result.fetchone()
            if row is None:
                return AuthorReputation(
                    author_id=author_id,
                    display_name="",
                    h_index=0,
                    total_citations=0,
                    retraction_count=0,
                    primary_affiliation=None,
                    affiliation_type=AffiliationType.INDEPENDENT,
                    last_refreshed=datetime.now(UTC),
                )
            await db.commit()
            return _row_to_reputation(tuple(row))

    @staticmethod
    def is_stale(reputation: AuthorReputation) -> bool:
        cutoff = datetime.now(UTC) - timedelta(days=_STALE_DAYS)
        last = reputation.last_refreshed
        if last.tzinfo is None:
            return last.replace(tzinfo=UTC) < cutoff
        return last < cutoff


def _row_to_reputation(row: tuple[object, ...]) -> AuthorReputation:
    weights_raw = row[7]
    domain_weights: dict[str, float] = {}
    if weights_raw is not None:
        if isinstance(weights_raw, dict):
            domain_weights = {k: float(v) for k, v in cast(dict[str, float], weights_raw).items()}
        elif isinstance(weights_raw, str) and weights_raw.strip():
            domain_weights = {
                k: float(v) for k, v in json.loads(weights_raw).items()
            }
    return AuthorReputation(
        author_id=str(row[0]),
        display_name=str(row[1]),
        h_index=int(cast(int, row[2])),
        total_citations=int(cast(int, row[3])),
        retraction_count=int(cast(int, row[4])),
        primary_affiliation=str(row[5]) if row[5] is not None else None,
        affiliation_type=AffiliationType(str(row[6])),
        domain_weights=domain_weights,
        last_refreshed=cast(datetime, row[8]),
    )
