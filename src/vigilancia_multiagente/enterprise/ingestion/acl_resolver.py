"""ACL resolver (Spec 021 F2.C T063 + FR-014).

Maintains a per-tenant index of ``chunk_id → ACLScope`` and computes the
allowlist of chunk ids that satisfy a given query principal (tenant +
roles + user). The allowlist is then passed to
``IngestionVectorIndex.query(allowlist=...)`` so filtering happens
inside the vector kernel rather than as a Python post-filter.

Constitución:
* SRP: one concern (ACL membership). No persistence, no DI knobs.
* CQS: ``register_chunk`` is a command (mutates state, returns None);
  ``allowlist_for`` is a query (pure read).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from vigilancia_multiagente.domain.ports.ingestion_connector import ACLScope


@dataclass(frozen=True)
class Principal:
    """Search-time identity (FR-014)."""

    tenant_id: UUID
    user: str
    roles: frozenset[str] = frozenset()


class ACLResolver:
    """In-memory ACL store. One instance per process; per-tenant maps."""

    def __init__(self) -> None:
        # tenant_id → chunk_id → ACLScope
        self._by_tenant: dict[UUID, dict[int, ACLScope]] = {}

    def register_chunk(self, chunk_id: int, scope: ACLScope) -> None:
        """Record ``scope`` for ``chunk_id`` under ``scope.tenant_id``."""
        bucket = self._by_tenant.setdefault(scope.tenant_id, {})
        bucket[chunk_id] = scope

    def register_many(self, chunks_with_scope: list[tuple[int, ACLScope]]) -> None:
        for chunk_id, scope in chunks_with_scope:
            self.register_chunk(chunk_id, scope)

    def allowlist_for(self, principal: Principal) -> list[int]:
        """Return the list of chunk_ids the ``principal`` can read.

        A chunk is visible iff:
        * its ``tenant_id`` matches the principal's, AND
        * the chunk is ``public``, OR the principal's ``user`` is in
          ``scope.users``, OR any of the principal's ``roles`` is in
          ``scope.roles``.
        """
        bucket = self._by_tenant.get(principal.tenant_id)
        if not bucket:
            return []
        out: list[int] = []
        principal_roles = principal.roles
        for chunk_id, scope in bucket.items():
            if scope.public:
                out.append(chunk_id)
                continue
            if principal.user in scope.users:
                out.append(chunk_id)
                continue
            if principal_roles & scope.roles:
                out.append(chunk_id)
        return out

    def total_for_tenant(self, tenant_id: UUID) -> int:
        """Diagnostic — chunk count under ``tenant_id``."""
        bucket = self._by_tenant.get(tenant_id)
        return len(bucket) if bucket else 0

    def reset(self, tenant_id: UUID | None = None) -> None:
        """Drop all entries (testing helper)."""
        if tenant_id is None:
            self._by_tenant.clear()
            return
        self._by_tenant.pop(tenant_id, None)
