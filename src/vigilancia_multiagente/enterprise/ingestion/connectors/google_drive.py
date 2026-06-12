"""Google Drive ingestion connector (Spec 021 F2.C T065, FR-013/FR-016).

Implements :class:`IngestionConnector` for Google Drive. Auth is per-tenant
via :class:`OAuthManager` (already used by ``GoogleWorkspaceTool``). The
connector requests **read-only scopes** so it can never modify the source
of truth — FR-016: ``drive.readonly`` for arbitrary files,
``drive.file`` for files explicitly shared with the OAuth client.

Capabilities:

* ``discover()`` — lists files visible to the credential, optionally
  scoped to a folder id (``VT_GDRIVE_ROOT_FOLDER_ID``).
* ``extract(ref)`` — Google-native types (Docs/Sheets/Slides) export to
  ``text/plain``; everything else streams the raw bytes and returns
  empty text (the orchestrator skips chunking on empty text).
* ``acl_for(ref)`` — pulls the file's permissions and maps them to
  :class:`ACLScope`. The connector's ``tenant_id`` is supplied at
  construction; ``users`` is the set of ``emailAddress`` permissions;
  ``roles`` is empty (Drive's "role" field is reader/writer/etc., not a
  business role).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import httpx

from vigilancia_multiagente.domain.ports.ingestion_connector import (
    ACLScope,
    DocumentRef,
    RawDoc,
)
from vigilancia_multiagente.enterprise.auth.oauth_manager import OAuthManager

logger = logging.getLogger(__name__)

_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
_DEFAULT_TIMEOUT_S = 30.0
_PROVIDER = "google_workspace"
_NATIVE_EXPORT_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


@dataclass
class GoogleDriveConnector:
    """Read-only Drive ingestion adapter."""

    oauth_manager: OAuthManager
    tenant_id: UUID
    name: str = "google_drive"

    async def discover(self) -> list[DocumentRef]:
        """List files visible to the OAuth credential (page 1, up to 100)."""
        token = await self._access_token()
        params: dict[str, str | int] = {
            "pageSize": 100,
            "fields": ("files(id,name,mimeType,modifiedTime,owners(emailAddress))"),
        }
        root = os.getenv("VT_GDRIVE_ROOT_FOLDER_ID") or ""
        if root:
            params["q"] = f"'{root}' in parents and trashed = false"
        else:
            params["q"] = "trashed = false"

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_DRIVE_API_BASE}/files",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()

        out: list[DocumentRef] = []
        for f in payload.get("files", []):
            modified = self._parse_iso(f.get("modifiedTime"))
            out.append(
                DocumentRef(
                    connector=self.name,
                    external_id=f["id"],
                    title=f.get("name", "(untitled)"),
                    mime_type=f.get("mimeType", ""),
                    last_modified=modified,
                    metadata={
                        "owners": [o.get("emailAddress", "") for o in f.get("owners", [])],
                    },
                )
            )
        return out

    async def extract(self, ref: DocumentRef) -> RawDoc:
        """Fetch text content for ``ref``.

        Native Google types are exported via ``/export`` to ``text/plain``
        (Sheets to ``text/csv``). Other types stream binary; we return
        empty text — pre-extraction (e.g. ``markitdown``) lives elsewhere.
        """
        token = await self._access_token()
        export_mime = _NATIVE_EXPORT_MIME.get(ref.mime_type)
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            if export_mime:
                response = await client.get(
                    f"{_DRIVE_API_BASE}/files/{ref.external_id}/export",
                    params={"mimeType": export_mime},
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                text = response.text
                size = len(response.content)
            else:
                response = await client.get(
                    f"{_DRIVE_API_BASE}/files/{ref.external_id}",
                    params={"alt": "media"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                size = len(response.content)
                text = ""  # binary blobs go through markitdown elsewhere
        return RawDoc(ref=ref, text=text, bytes_size=size)

    async def acl_for(self, ref: DocumentRef) -> ACLScope:
        """Map Drive's ``/permissions`` to an :class:`ACLScope`."""
        token = await self._access_token()
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_DRIVE_API_BASE}/files/{ref.external_id}/permissions",
                params={"fields": "permissions(type,emailAddress,role)"},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()

        users: set[str] = set()
        public = False
        for perm in payload.get("permissions", []):
            ptype = perm.get("type", "")
            if ptype in ("anyone", "domain"):
                public = True
            elif ptype == "user":
                email = perm.get("emailAddress", "").lower()
                if email:
                    users.add(email)
        return ACLScope(
            tenant_id=self.tenant_id,
            users=frozenset(users),
            roles=frozenset(),
            public=public,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _access_token(self) -> str:
        cred = await self.oauth_manager.get(_PROVIDER, self.tenant_id)
        if cred is None:
            raise RuntimeError(
                "GoogleDriveConnector: no OAuth credential on file for "
                f"tenant {self.tenant_id} — complete onboarding to grant "
                "Drive read-only scope."
            )
        return cred.access_token

    @staticmethod
    def _parse_iso(value: object) -> datetime:
        if not isinstance(value, str) or not value:
            return datetime.now(UTC)
        # Drive returns ISO 8601 with 'Z'; Python 3.11+ parses with fromisoformat
        cleaned = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return datetime.now(UTC)
