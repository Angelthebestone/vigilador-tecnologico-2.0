"""Ingestion connector port (Spec 021 FR-013).

Connectors discover documents from external systems, extract their raw
bytes/text, and resolve per-document ACL scopes. The orchestrator
(``enterprise/ingestion/orchestrator.py``) wires connectors → chunking →
dedup → embeddings → ``IngestionVectorIndex``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True)
class DocumentRef:
    """Lightweight pointer to a remote document."""

    connector: str  # e.g. "google_drive"
    external_id: str  # connector-side stable id
    title: str
    mime_type: str
    last_modified: datetime
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RawDoc:
    """Document content + provenance after extraction."""

    ref: DocumentRef
    text: str
    bytes_size: int


@dataclass(frozen=True)
class ACLScope:
    """ACL scope attached to a document, evaluated in ``acl_resolver``.

    Roles and users are sets of ids the connector says are allowed to read
    the document. The orchestrator stores them per-chunk so search-time
    filtering is a constant-time set check.
    """

    tenant_id: UUID
    roles: frozenset[str] = frozenset()
    users: frozenset[str] = frozenset()
    public: bool = False


@runtime_checkable
class IngestionConnector(Protocol):
    """Source-system adapter (Drive, SharePoint, …) for ingestion."""

    name: str
    """Connector id matching the catalog (e.g. ``"google_drive"``)."""

    async def discover(self) -> list[DocumentRef]:
        """List documents visible to the configured credential."""
        ...

    async def extract(self, ref: DocumentRef) -> RawDoc:
        """Fetch the document bytes and return its plain-text content."""
        ...

    async def acl_for(self, ref: DocumentRef) -> ACLScope:
        """Resolve the ACL scope (tenant + roles/users) for ``ref``."""
        ...
