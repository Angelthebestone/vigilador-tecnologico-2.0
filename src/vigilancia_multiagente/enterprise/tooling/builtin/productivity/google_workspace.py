"""Google Workspace tool — native WRAP-SDK over Google's Drive/Docs/Sheets/Gmail REST APIs.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``google_workspace`` / domain ``productivity`` / capabilities
``[read_docs, write_docs, read_sheets, send_email]``.

Strategy: WRAP-SDK using ``httpx`` directly against the public REST APIs.
Auth uses the existing :class:`OAuthManager` (Fernet-encrypted tokens
in ``~/.vigilador/credentials/``). The provider name is ``google_workspace``.

The tool is tenant-aware (FR-019): each tenant's credential is fetched
separately via ``OAuthManager.get(provider, tenant_id)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx

from vigilancia_multiagente.enterprise.auth.oauth_manager import OAuthManager
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3"
_DOCS_BASE_URL = "https://docs.googleapis.com/v1"
_SHEETS_BASE_URL = "https://sheets.googleapis.com/v4"
_GMAIL_BASE_URL = "https://gmail.googleapis.com/gmail/v1"
_DEFAULT_TIMEOUT_S = 30.0
_PROVIDER = "google_workspace"


@dataclass(frozen=True)
class GoogleWorkspaceTool:
    """Native tool for Google Workspace APIs (OAuth via OAuthManager)."""

    oauth_manager: OAuthManager | None
    tenant_id: UUID
    name: str = "google_workspace"
    domain: str = "productivity"
    is_external_mcp: bool = False
    requires_auth: bool = True

    async def healthcheck(self) -> HealthcheckResult:
        """Check whether a Google OAuth credential is on file for the tenant."""
        if self.oauth_manager is None:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error="OAuthManager not wired (tenant not onboarded)",
            )
        cred = await self.oauth_manager.get(_PROVIDER, self.tenant_id)
        if cred is None:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=(
                    f"No Google OAuth credential on file for tenant "
                    f"{self.tenant_id}; complete onboarding to grant access."
                ),
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``read_docs`` — args: ``document_id`` (str). Reads a Google Doc.
        * ``write_docs`` — args: ``document_id`` (str), ``text`` (str).
          Appends ``text`` at the end.
        * ``read_sheets`` — args: ``spreadsheet_id`` (str), ``range`` (str).
        * ``send_email`` — args: ``to`` (str), ``subject`` (str), ``body`` (str).
        """
        token = await self._access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if tool_name == "read_docs":
            return await self._read_doc(headers, args)
        if tool_name == "write_docs":
            return await self._append_doc(headers, args)
        if tool_name == "read_sheets":
            return await self._read_sheet(headers, args)
        if tool_name == "send_email":
            return await self._send_email(headers, args)
        raise ValueError(
            f"GoogleWorkspaceTool: unknown tool_name '{tool_name}' "
            f"(supported: read_docs, write_docs, read_sheets, send_email)"
        )

    async def _access_token(self) -> str:
        if self.oauth_manager is None:
            raise RuntimeError(
                "GoogleWorkspaceTool: OAuthManager not wired (no tenant credentials)"
            )
        cred = await self.oauth_manager.get(_PROVIDER, self.tenant_id)
        if cred is None:
            raise RuntimeError(
                f"GoogleWorkspaceTool: no OAuth credential for tenant "
                f"{self.tenant_id}; complete onboarding first"
            )
        return cred.access_token

    async def _read_doc(
        self, headers: dict[str, str], args: dict[str, object]
    ) -> dict[str, object]:
        doc_id = _required_str(args, "document_id", "GoogleWorkspaceTool")
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_DOCS_BASE_URL}/documents/{doc_id}", headers=headers
            )
            response.raise_for_status()
            return {"document_id": doc_id, "document": response.json()}

    async def _append_doc(
        self, headers: dict[str, str], args: dict[str, object]
    ) -> dict[str, object]:
        doc_id = _required_str(args, "document_id", "GoogleWorkspaceTool")
        text = _required_str(args, "text", "GoogleWorkspaceTool")
        # Use insertText at the document end (index 1 = beginning of body).
        body = {
            "requests": [
                {"insertText": {"location": {"index": 1}, "text": text}}
            ]
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_DOCS_BASE_URL}/documents/{doc_id}:batchUpdate",
                headers={**headers, "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            return {"document_id": doc_id, "result": response.json()}

    async def _read_sheet(
        self, headers: dict[str, str], args: dict[str, object]
    ) -> dict[str, object]:
        sid = _required_str(args, "spreadsheet_id", "GoogleWorkspaceTool")
        rng = _required_str(args, "range", "GoogleWorkspaceTool")
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.get(
                f"{_SHEETS_BASE_URL}/spreadsheets/{sid}/values/{rng}",
                headers=headers,
            )
            response.raise_for_status()
            return {"spreadsheet_id": sid, "range": rng, "values": response.json()}

    async def _send_email(
        self, headers: dict[str, str], args: dict[str, object]
    ) -> dict[str, object]:
        import base64

        to = _required_str(args, "to", "GoogleWorkspaceTool")
        subject = _required_str(args, "subject", "GoogleWorkspaceTool")
        body = _required_str(args, "body", "GoogleWorkspaceTool")
        message = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        raw = base64.urlsafe_b64encode(message.encode()).decode()
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
            response = await client.post(
                f"{_GMAIL_BASE_URL}/users/me/messages/send",
                headers={**headers, "Content-Type": "application/json"},
                json={"raw": raw},
            )
            response.raise_for_status()
            return {"to": to, "subject": subject, "result": response.json()}


def _required_str(args: dict[str, object], key: str, tool: str) -> str:
    val = args.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"{tool}: '{key}' must be a non-empty string")
    return val
