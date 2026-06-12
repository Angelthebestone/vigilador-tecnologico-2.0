"""ToolRegistry — registro central de tools del Vigilador 3.0 (F1.2).

Responsabilidades:
- Registro de tools con validación de unicidad.
- Listado filtrado por rol con gating (API key faltante oculta tool).
- Fichas progresivas: ToolCard → ToolSummary → ToolDocs.
- Descubrimiento semántico por similitud coseno via EmbeddingGateway.
- Spec 021 F5a.D / T136: orquesta `execute()` con auditoría JSONL opcional.
"""

from __future__ import annotations

import math
import os
import time
from typing import Any
from uuid import UUID

from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.enterprise.governance.audit_log import AuditLogPort
from vigilancia_multiagente.enterprise.tooling.tool_card import ToolCard, ToolDocs, ToolSummary
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper
from vigilancia_multiagente.infra.embeddings.embedding_cache import EmbeddingCache
from vigilancia_multiagente.infra.persistence.tool_health_repository import (
    ToolHealthRepository,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class ToolRegistry:
    """Registro central de tools."""

    def __init__(
        self,
        tool_health_repo: ToolHealthRepository,
        embedding_gateway: EmbeddingGateway,
        audit_log: AuditLogPort | None = None,
        embedding_cache: EmbeddingCache | None = None,
    ) -> None:
        self._health_repo = tool_health_repo
        self._embedding_gw = embedding_gateway
        self._tools: dict[str, ToolWrapper] = {}
        self._audit_log = audit_log
        self._embedding_cache = embedding_cache
        self._tool_embeddings: dict[str, list[float]] = {}

    async def register(self, tool: ToolWrapper) -> None:
        """Registra una tool. Falla si el name ya existe."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

        # Pre-compute embedding for tool description (FR-001)
        desc = getattr(tool, "description", tool.name)
        vec: list[float] | None = None
        if self._embedding_gw:
            vec = await self._embedding_gw.embed(desc)
            self._tool_embeddings[tool.name] = vec
        if self._embedding_cache and vec is not None:
            self._embedding_cache.set(desc, vec)

    async def aclose_all(self) -> None:
        """Close all tools that have an aclose() method (BaseHTTPProvider, etc.)."""
        import inspect

        for tool in self._tools.values():
            closer = getattr(tool, "aclose", None)
            if callable(closer):
                try:
                    result = closer()
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    pass

    async def is_capability_available(self, name: str) -> bool:
        """Retorna True si `name` está registrado y pasa gating (spec 015 A-01).

        Mapeo plano: cada capability string corresponde al tool.name registrado.
        """
        tool = self._tools.get(name)
        if tool is None:
            return False
        return self._passes_gating(tool)

    async def list_tools_for_role(self, role: str, tenant_id: UUID) -> list[ToolCard]:
        """Lista tools disponibles, aplicando gating por API key."""
        cards: list[ToolCard] = []
        for tool in self._tools.values():
            if not self._passes_gating(tool):
                continue
            status = await self._get_status(tool.name, tenant_id)
            cards.append(self._to_card(tool, status))
        return cards

    async def get_summary(self, name: str) -> ToolSummary:
        """Retorna ficha resumida de la tool."""
        tool = self._tools[name]
        card = self._to_card(tool, "UNKNOWN")
        return ToolSummary(
            card=card,
            input_schema=getattr(tool, "input_schema", {}),
            output_schema=getattr(tool, "output_schema", {}),
            examples=getattr(tool, "examples", []),
        )

    async def get_docs(self, name: str) -> ToolDocs:
        """Retorna documentación completa de la tool."""
        summary = await self.get_summary(name)
        tool = self._tools[name]
        # FR-034: Load long_description from prompts/tools/{name}.txt
        long_description = getattr(tool, "long_description", "")
        if not long_description:
            try:
                from vigilancia_multiagente.infra.prompts.loader import FilesystemPromptLoader

                loader = FilesystemPromptLoader()
                long_description = loader.load(f"tools/{name}")
            except (FileNotFoundError, Exception):
                long_description = ""
        return ToolDocs(
            summary=summary,
            long_description=long_description,
            full_examples=getattr(tool, "full_examples", []),
        )

    async def discover(self, role: str, intent: str, tenant_id: UUID) -> list[ToolCard]:
        """Descubre tools ordenadas por similitud semántica al intent."""
        intent_vec = await self._embedding_gw.embed(intent)
        scored: list[tuple[float, ToolCard]] = []

        # Get all valid tool names first
        valid_tools = [tool for tool in self._tools.values() if self._passes_gating(tool)]
        valid_names = [tool.name for tool in valid_tools]

        # Batch fetch statuses (FR-002)
        statuses = await self._health_repo.get_statuses_batch(valid_names, tenant_id)

        for tool in valid_tools:
            # Use pre-computed embedding (FR-001)
            tool_vec = self._tool_embeddings.get(tool.name)
            if tool_vec is None:
                # Fallback if not pre-computed
                desc = getattr(tool, "description", tool.name)
                tool_vec = await self._embedding_gw.embed(desc)

            sim = _cosine_similarity(intent_vec, tool_vec)
            status = statuses.get(tool.name, "UNKNOWN")
            scored.append((sim, self._to_card(tool, status)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [card for _, card in scored]

    async def execute(
        self,
        name: str,
        args: dict[str, Any],
        operation: str = "execute",
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, object]:
        """Spec 021 F5a.D / T136 — central tool dispatch with audit JSONL.

        Looks up the registered ``ToolWrapper`` and delegates to its
        ``execute(name, args)``. Around the call, when an
        :class:`AuditLogPort` is configured, emits a ``tool_invocation``
        event capturing outcome, duration, and any error.

        Raises ``KeyError`` if ``name`` is not registered.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' is not registered")

        t0 = time.perf_counter()
        outcome = "success"
        error: str | None = None
        try:
            return await tool.execute(name, args)
        except Exception as exc:
            outcome = "error"
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            if self._audit_log is not None:
                duration_ms = (time.perf_counter() - t0) * 1000
                self._audit_log.log_tool_invocation(
                    tool_id=name,
                    operation=operation,
                    outcome=outcome,
                    duration_ms=duration_ms,
                    agent_id=agent_id,
                    session_id=session_id,
                    error=error,
                )

    # --- private helpers ---

    def _passes_gating(self, tool: ToolWrapper) -> bool:
        if not tool.requires_auth:
            return True
        env_var = getattr(tool, "auth_env_var", "")
        if not env_var:
            return False
        return bool(os.environ.get(env_var))

    async def _get_status(self, name: str, tenant_id: UUID) -> str:
        row = await self._health_repo.read_status(name, tenant_id)
        return row.status if row else "UNKNOWN"

    def _to_card(self, tool: ToolWrapper, status: str) -> ToolCard:
        desc = getattr(tool, "description", tool.name)[:80]
        return ToolCard(
            id=tool.name,
            description=desc,
            domains=[tool.domain],
            requires_auth=tool.requires_auth,
            cost_tier=getattr(tool, "cost_tier", "free"),
            status=status,
        )
