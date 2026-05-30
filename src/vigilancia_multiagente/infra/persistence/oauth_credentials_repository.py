"""Repositorio de la tabla `oauth_credentials` (T018).

SQL crudo vía `sqlalchemy.text()`. Los tokens se guardan YA encriptados
(Fernet) por el `OAuthManager`; este repositorio NO encripta ni desencripta:
solo persiste y recupera el texto cifrado.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.infra.db.connection import Database


@dataclass(frozen=True, slots=True)
class OAuthRow:
    tenant_id: UUID
    provider: str
    token_encrypted: str
    refresh_token_encrypted: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)


def _row_to_dataclass(row: object) -> OAuthRow:
    m = row  # RowMapping
    raw_scopes = m["scopes"]  # type: ignore[index]
    scopes = raw_scopes if isinstance(raw_scopes, list) else json.loads(raw_scopes or "[]")
    return OAuthRow(
        tenant_id=m["tenant_id"],  # type: ignore[index]
        provider=str(m["provider"]),  # type: ignore[index]
        token_encrypted=str(m["token_encrypted"]),  # type: ignore[index]
        refresh_token_encrypted=m["refresh_token_encrypted"],  # type: ignore[index]
        expires_at=m["expires_at"],  # type: ignore[index]
        scopes=list(scopes),
    )


class OAuthCredentialsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, provider: str, tenant_id: UUID) -> OAuthRow | None:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT tenant_id, provider, token_encrypted, "
                    "refresh_token_encrypted, expires_at, scopes "
                    "FROM oauth_credentials "
                    "WHERE provider = :provider AND tenant_id = :tenant_id"
                ),
                {"provider": provider, "tenant_id": tenant_id},
            )
            row = result.mappings().one_or_none()
            return _row_to_dataclass(row) if row is not None else None

    async def store(self, row: OAuthRow) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO oauth_credentials "
                    "(tenant_id, provider, token_encrypted, refresh_token_encrypted, "
                    " expires_at, scopes, updated_at) "
                    "VALUES (:tenant_id, :provider, :token_encrypted, "
                    " :refresh_token_encrypted, :expires_at, CAST(:scopes AS jsonb), NOW()) "
                    "ON CONFLICT (tenant_id, provider) DO UPDATE SET "
                    "  token_encrypted = EXCLUDED.token_encrypted, "
                    "  refresh_token_encrypted = EXCLUDED.refresh_token_encrypted, "
                    "  expires_at = EXCLUDED.expires_at, "
                    "  scopes = EXCLUDED.scopes, "
                    "  updated_at = NOW()"
                ),
                {
                    "tenant_id": row.tenant_id,
                    "provider": row.provider,
                    "token_encrypted": row.token_encrypted,
                    "refresh_token_encrypted": row.refresh_token_encrypted,
                    "expires_at": row.expires_at,
                    "scopes": json.dumps(row.scopes),
                },
            )
            await db.commit()

    async def delete(self, provider: str, tenant_id: UUID) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "DELETE FROM oauth_credentials "
                    "WHERE provider = :provider AND tenant_id = :tenant_id"
                ),
                {"provider": provider, "tenant_id": tenant_id},
            )
            await db.commit()
