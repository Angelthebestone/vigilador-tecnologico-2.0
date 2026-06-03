"""Tests for ``enterprise.ingestion.connectors.google_drive`` (Spec 021 T064).

Uses ``respx`` (already in dev deps) to mock the Drive REST surface and
a lightweight stub for ``OAuthManager`` so no real credentials/network
are touched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import pytest
import respx
from httpx import Response

from vigilancia_multiagente.enterprise.ingestion.connectors.google_drive import (
    GoogleDriveConnector,
)

_TENANT = UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class _StubCred:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scopes: tuple[str, ...] = ("drive.readonly",)
    provider: str = "google_workspace"


class _StubOAuth:
    def __init__(self, token: str | None = "token-XYZ"):
        self._token = token

    async def get(self, provider, tenant_id):
        if self._token is None:
            return None
        return _StubCred(access_token=self._token)


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_discover_returns_doc_refs():
    respx.get("https://www.googleapis.com/drive/v3/files").mock(
        return_value=Response(
            200,
            json={
                "files": [
                    {
                        "id": "1abcd",
                        "name": "Roadmap.docx",
                        "mimeType": "application/vnd.google-apps.document",
                        "modifiedTime": "2024-12-01T10:00:00Z",
                        "owners": [{"emailAddress": "alice@example.com"}],
                    },
                ]
            },
        )
    )
    conn = GoogleDriveConnector(
        oauth_manager=_StubOAuth(), tenant_id=_TENANT
    )
    refs = await conn.discover()
    assert len(refs) == 1
    assert refs[0].external_id == "1abcd"
    assert refs[0].title == "Roadmap.docx"
    assert refs[0].mime_type == "application/vnd.google-apps.document"


@pytest.mark.asyncio
async def test_discover_raises_without_credential():
    conn = GoogleDriveConnector(
        oauth_manager=_StubOAuth(token=None), tenant_id=_TENANT
    )
    with pytest.raises(RuntimeError, match="no OAuth credential"):
        await conn.discover()


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_extract_native_doc_uses_export():
    respx.get(
        "https://www.googleapis.com/drive/v3/files/abc/export"
    ).mock(return_value=Response(200, text="hello world"))
    conn = GoogleDriveConnector(
        oauth_manager=_StubOAuth(), tenant_id=_TENANT
    )
    from vigilancia_multiagente.domain.ports.ingestion_connector import DocumentRef

    ref = DocumentRef(
        connector="google_drive",
        external_id="abc",
        title="x",
        mime_type="application/vnd.google-apps.document",
        last_modified=datetime(2024, 12, 1, tzinfo=__import__("datetime").timezone.utc),
    )
    raw = await conn.extract(ref)
    assert raw.text == "hello world"


# ---------------------------------------------------------------------------
# acl_for
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_acl_for_marks_public_when_anyone_permission():
    respx.get(
        "https://www.googleapis.com/drive/v3/files/abc/permissions"
    ).mock(
        return_value=Response(
            200,
            json={
                "permissions": [
                    {"type": "anyone", "role": "reader"},
                    {
                        "type": "user",
                        "emailAddress": "bob@example.com",
                        "role": "writer",
                    },
                ]
            },
        )
    )
    conn = GoogleDriveConnector(
        oauth_manager=_StubOAuth(), tenant_id=_TENANT
    )
    from vigilancia_multiagente.domain.ports.ingestion_connector import DocumentRef

    ref = DocumentRef(
        connector="google_drive",
        external_id="abc",
        title="x",
        mime_type="application/pdf",
        last_modified=datetime(2024, 12, 1, tzinfo=__import__("datetime").timezone.utc),
    )
    scope = await conn.acl_for(ref)
    assert scope.tenant_id == _TENANT
    assert scope.public is True
    assert "bob@example.com" in scope.users


@pytest.mark.asyncio
@respx.mock
async def test_acl_for_extracts_user_emails_only():
    respx.get(
        "https://www.googleapis.com/drive/v3/files/abc/permissions"
    ).mock(
        return_value=Response(
            200,
            json={
                "permissions": [
                    {
                        "type": "user",
                        "emailAddress": "alice@example.com",
                        "role": "reader",
                    },
                ]
            },
        )
    )
    conn = GoogleDriveConnector(
        oauth_manager=_StubOAuth(), tenant_id=_TENANT
    )
    from vigilancia_multiagente.domain.ports.ingestion_connector import DocumentRef

    ref = DocumentRef(
        connector="google_drive",
        external_id="abc",
        title="x",
        mime_type="text/plain",
        last_modified=datetime(2024, 12, 1, tzinfo=__import__("datetime").timezone.utc),
    )
    scope = await conn.acl_for(ref)
    assert scope.public is False
    assert scope.users == frozenset({"alice@example.com"})
