"""Niveles de detalle de la ficha de una tool (T016).

Tres niveles progresivos de información, para que el agente pida solo lo que
necesita y no sature el contexto:

  - `ToolCard`    → tarjeta mínima (≤ 80 chars de descripción) para listados.
  - `ToolSummary` → ficha con schema de inputs/outputs + 2-3 ejemplos.
  - `ToolDocs`    → documentación completa (descripción larga + ejemplos).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ToolCard:
    """Tarjeta mínima de una tool, para listados por rol."""

    id: str
    description: str  # ≤ 80 chars (validado por el registry)
    domains: list[str]
    requires_auth: bool
    cost_tier: str  # "free" | "low" | "medium" | "high"
    status: str  # "UP" | "DOWN" | "UNCONFIGURED" | "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ToolSummary:
    """Ficha resumida: tarjeta + schema de inputs/outputs + ejemplos cortos."""

    card: ToolCard
    input_schema: dict[str, object] = field(default_factory=dict)
    output_schema: dict[str, object] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)  # 2-3 ejemplos


@dataclass(frozen=True, slots=True)
class ToolDocs:
    """Documentación completa: resumen + descripción larga + ejemplos completos."""

    summary: ToolSummary
    long_description: str = ""
    full_examples: list[str] = field(default_factory=list)
