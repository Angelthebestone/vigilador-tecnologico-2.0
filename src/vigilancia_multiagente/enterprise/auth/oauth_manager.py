"""OAuthManager - gestion de credenciales OAuth con encriptacion Fernet (F1.4)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet

from vigilancia_multiagente.infra.persistence.oauth_credentials_repository import (
    OAuthCredentialsRepository,
    OAuthRow,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OAuthCredential:
    provider: str
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]


class OAuthManager:
    """Encripta/desencripta tokens OAuth y delega persistencia al repositorio."""

    def __init__(
        self,
        repo: OAuthCredentialsRepository,
        credentials_dir: Path | None = None,
    ) -> None:
        self._repo = repo
        self._dir = credentials_dir or Path.home() / ".vigilador" / "credentials"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._key_path = self._dir / ".fernet_key"
        self._fernet = Fernet(self._ensure_key())

    def _ensure_key(self) -> bytes:
        if self._key_path.exists():
            return self._key_path.read_bytes().strip()
        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        if sys.platform == "win32":
            subprocess.run(
                [
                    "icacls",
                    str(self._key_path),
                    "/inheritance:r",
                    "/grant:r",
                    f"{os.getlogin()}:F",
                ],
                check=False,
            )
        else:
            self._key_path.chmod(0o600)
        return key

    async def store(
        self,
        provider: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
        scopes: list[str],
        tenant_id: UUID,
    ) -> None:
        row = OAuthRow(
            tenant_id=tenant_id,
            provider=provider,
            token_encrypted=self._fernet.encrypt(access_token.encode()).decode(),
            refresh_token_encrypted=(
                self._fernet.encrypt(refresh_token.encode()).decode() if refresh_token else None
            ),
            expires_at=expires_at,
            scopes=scopes,
        )
        await self._repo.store(row)

    async def get(self, provider: str, tenant_id: UUID) -> OAuthCredential | None:
        row = await self._repo.get(provider, tenant_id)
        if row is None:
            return None
        return OAuthCredential(
            provider=row.provider,
            access_token=self._fernet.decrypt(row.token_encrypted.encode()).decode(),
            refresh_token=(
                self._fernet.decrypt(row.refresh_token_encrypted.encode()).decode()
                if row.refresh_token_encrypted
                else None
            ),
            expires_at=row.expires_at,
            scopes=row.scopes,
        )

    async def refresh_if_needed(self, provider: str, tenant_id: UUID) -> None:
        row = await self._repo.get(provider, tenant_id)
        if row is None or row.expires_at is None:
            return
        remaining = row.expires_at - datetime.now(UTC)
        if remaining < timedelta(days=7):
            logger.warning(
                "Token for provider=%s tenant=%s expiring in %s - refresh needed",
                provider,
                tenant_id,
                remaining,
            )
