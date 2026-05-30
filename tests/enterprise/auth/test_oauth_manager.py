"""Tests for OAuthManager (F1.4)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from vigilancia_multiagente.enterprise.auth.oauth_manager import (
    OAuthManager,
)
from vigilancia_multiagente.infra.persistence.oauth_credentials_repository import OAuthRow


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def manager(tmp_path, repo) -> OAuthManager:
    return OAuthManager(repo=repo, credentials_dir=tmp_path)


class TestFernetKeyCreation:
    def test_fernet_key_created_on_first_boot(self, tmp_path, repo):
        """Fernet key se crea al primer arranque con permisos restrictivos."""
        key_path = tmp_path / ".fernet_key"
        assert not key_path.exists()

        with patch("subprocess.run") as mock_run:
            OAuthManager(repo=repo, credentials_dir=tmp_path)

        assert key_path.exists()
        # Key debe ser válida Fernet (44 bytes url-safe base64)
        assert len(key_path.read_bytes().strip()) == 44
        # En Windows se llama icacls
        if sys.platform == "win32":
            mock_run.assert_called_once()


class TestStore:
    @pytest.mark.asyncio
    async def test_store_encrypts_and_persists(self, manager, repo):
        """store encripta y persiste."""
        tenant = uuid4()
        await manager.store(
            provider="google",
            access_token="access123",
            refresh_token="refresh456",
            expires_at=datetime(2026, 6, 1, tzinfo=UTC),
            scopes=["read", "write"],
            tenant_id=tenant,
        )

        repo.store.assert_awaited_once()
        row: OAuthRow = repo.store.call_args[0][0]
        assert row.provider == "google"
        assert row.tenant_id == tenant
        # Tokens deben estar encriptados (no plaintext)
        assert row.token_encrypted != "access123"
        assert row.refresh_token_encrypted != "refresh456"


class TestGet:
    @pytest.mark.asyncio
    async def test_get_decrypts_correctly(self, manager, repo):
        """get desencripta correctamente."""
        tenant = uuid4()
        # Store first to get encrypted values
        await manager.store(
            provider="github",
            access_token="tok_abc",
            refresh_token="ref_xyz",
            expires_at=datetime(2026, 7, 1, tzinfo=UTC),
            scopes=["repo"],
            tenant_id=tenant,
        )
        stored_row: OAuthRow = repo.store.call_args[0][0]

        # Mock repo.get to return the stored row
        repo.get = AsyncMock(return_value=stored_row)

        cred = await manager.get(provider="github", tenant_id=tenant)
        assert cred is not None
        assert cred.access_token == "tok_abc"
        assert cred.refresh_token == "ref_xyz"
        assert cred.provider == "github"
        assert cred.scopes == ["repo"]


class TestRoundtripMultiProvider:
    @pytest.mark.asyncio
    async def test_roundtrip_multi_provider(self, manager, repo):
        """roundtrip multi-provider."""
        tenant = uuid4()
        stored_rows: dict[str, OAuthRow] = {}

        async def fake_store(row: OAuthRow) -> None:
            stored_rows[row.provider] = row

        repo.store = AsyncMock(side_effect=fake_store)

        await manager.store("google", "g_tok", "g_ref", None, ["mail"], tenant)
        await manager.store("github", "gh_tok", None, None, ["repo"], tenant)

        # Verify roundtrip for each provider
        for provider, expected_access, expected_refresh in [
            ("google", "g_tok", "g_ref"),
            ("github", "gh_tok", None),
        ]:
            repo.get = AsyncMock(return_value=stored_rows[provider])
            cred = await manager.get(provider=provider, tenant_id=tenant)
            assert cred is not None
            assert cred.access_token == expected_access
            assert cred.refresh_token == expected_refresh


class TestRefreshIfNeeded:
    @pytest.mark.asyncio
    async def test_refresh_warns_when_expiring_soon(self, manager, repo, caplog):
        """refresh_if_needed dispara cuando expires_at - now < 7d."""
        tenant = uuid4()
        expires_soon = datetime.now(UTC) + timedelta(days=3)

        await manager.store("azure", "az_tok", "az_ref", expires_soon, ["openid"], tenant)
        stored_row: OAuthRow = repo.store.call_args[0][0]
        repo.get = AsyncMock(return_value=stored_row)

        import logging

        with caplog.at_level(logging.WARNING):
            await manager.refresh_if_needed(provider="azure", tenant_id=tenant)

        assert any("expir" in msg.lower() for msg in caplog.messages)
