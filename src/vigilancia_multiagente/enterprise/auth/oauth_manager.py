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

import httpx
from cryptography.fernet import Fernet

from vigilancia_multiagente.infra.persistence.oauth_credentials_repository import (
    OAuthCredentialsRepository,
    OAuthRow,
)

logger = logging.getLogger(__name__)

_PROVIDER_REFRESH_URLS: dict[str, str] = {
    "google_workspace": "https://oauth2.googleapis.com/token",
}


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

    async def refresh_if_needed(self, provider: str, tenant_id: UUID) -> OAuthCredential | None:
        """Refresh the token if it expires within 7 days. Returns new credential or None."""
        row = await self._repo.get(provider, tenant_id)
        if row is None or row.expires_at is None:
            return None
        remaining = row.expires_at - datetime.now(UTC)
        if remaining >= timedelta(days=7):
            return None

        refresh_token = (
            self._fernet.decrypt(row.refresh_token_encrypted.encode()).decode()
            if row.refresh_token_encrypted
            else None
        )
        if not refresh_token:
            logger.warning(
                "Token for provider=%s tenant=%s expiring in %s but no refresh_token stored",
                provider,
                tenant_id,
                remaining,
            )
            return None

        refresh_url = _PROVIDER_REFRESH_URLS.get(provider)
        if not refresh_url:
            logger.warning(
                "No refresh endpoint known for provider=%s; token will expire",
                provider,
            )
            return None

        new_tokens = await self._do_refresh(refresh_url, provider, refresh_token)
        if new_tokens is None:
            return None

        new_access, new_refresh, new_expires = new_tokens
        await self.store(
            provider=provider,
            access_token=new_access,
            refresh_token=new_refresh or refresh_token,
            expires_at=new_expires,
            scopes=row.scopes,
            tenant_id=tenant_id,
        )
        logger.info(
            "Refreshed token for provider=%s tenant=%s (new expires=%s)",
            provider,
            tenant_id,
            new_expires,
        )
        return await self.get(provider, tenant_id)

    async def _do_refresh(
        self, refresh_url: str, provider: str, refresh_token: str
    ) -> tuple[str, str | None, datetime | None] | None:
        """Call the provider's refresh endpoint. Returns (access_token, refresh_token|None, expires_at|None)."""
        client_id = os.environ.get("VT_GOOGLE_CLIENT_ID", "")
        client_secret = os.environ.get("VT_GOOGLE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            logger.error("Missing VT_GOOGLE_CLIENT_ID or VT_GOOGLE_CLIENT_SECRET for refresh")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    refresh_url,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                new_access = data["access_token"]
                new_refresh = data.get("refresh_token")
                expires_in = data.get("expires_in")
                new_expires = (
                    datetime.now(UTC) + timedelta(seconds=expires_in)
                    if expires_in
                    else None
                )
                return new_access, new_refresh, new_expires
        except Exception as exc:
            logger.error("OAuth refresh failed for provider=%s: %s", provider, exc)
            return None
