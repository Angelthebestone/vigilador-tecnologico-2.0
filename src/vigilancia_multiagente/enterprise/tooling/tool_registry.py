"""ToolRegistry — registro central de tools del Vigilador 3.0 (F1.2).

Responsabilidades:
- Registro de tools con validación de unicidad.
- Listado filtrado por rol con gating (API key faltante oculta tool).
- Fichas progresivas: ToolCard → ToolSummary → ToolDocs.
- Descubrimiento semántico por similitud coseno via EmbeddingGateway.
"""

from __future__ import annotations

import math
import os
from uuid import UUID

from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.enterprise.tooling.tool_card import ToolCard, ToolDocs, ToolSummary
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import ToolWrapper
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
    ) -> None:
        self._health_repo = tool_health_repo
        self._embedding_gw = embedding_gateway
        self._tools: dict[str, ToolWrapper] = {}

    async def register(self, tool: ToolWrapper) -> None:
        """Registra una tool. Falla si el name ya existe."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

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
        return ToolDocs(
            summary=summary,
            long_description=getattr(tool, "long_description", ""),
            full_examples=getattr(tool, "full_examples", []),
        )

    async def discover(self, role: str, intent: str, tenant_id: UUID) -> list[ToolCard]:
        """Descubre tools ordenadas por similitud semántica al intent."""
        intent_vec = await self._embedding_gw.embed(intent)
        scored: list[tuple[float, ToolCard]] = []
        for tool in self._tools.values():
            if not self._passes_gating(tool):
                continue
            desc = getattr(tool, "description", tool.name)
            tool_vec = await self._embedding_gw.embed(desc)
            sim = _cosine_similarity(intent_vec, tool_vec)
            status = await self._get_status(tool.name, tenant_id)
            scored.append((sim, self._to_card(tool, status)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [card for _, card in scored]

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
