"""Selección de tool por señal, no por posición.

El bucle de agente histórico hacía ``tool_order[index]``: la posición en la
lista decidía la tool. Eso ataba la estrategia a un guion fijo —
herramientas tardías (p.ej. ``read_paper``) nunca se alcanzaban si el
``depth_limit`` cortaba antes, y 35 tools registradas jamás se invocaban.

Este selector convierte ``tool_order`` en un *conjunto disponible* y elige,
en cada iteración, la tool que el contexto pide — usando solo señales que ya
existen sin LLM (clasificación de query, sugerencia del payload previo,
estrategia aprendida). Es la base evolutiva sobre la que conectar
tool-calling real cuando haya un LLM activo.

Orden de prioridad (la primera que aplica gana):

1. **Cadena forzada (MiniMax + PDF)**: si la iteración previa ejecutó una
   tool que produce binario (``download_paper``), la siguiente DEBE ser la
   que lo convierte a texto (``read_paper`` / ``convert_to_markdown``).
   MiniMax no lee PDFs; romper esta cadena alucina o falla. No es heurística
   negociable: es una invariante de corrección.
2. **Sugerencia del payload previo** (``mcp_suggestion``): si la tool
   anterior recomienda explícitamente otra del conjunto, se respeta.
3. **Afinidad query→tool**: la tool del conjunto cuyo tipo casa mejor con el
   tipo de query clasificado.
4. **Recorrido determinista**: barre el conjunto sin repetir la última tool
   mientras queden alternativas — preserva cobertura y reproducibilidad.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# download_tool -> tool que materializa su salida binaria a texto. MiniMax
# solo procesa texto; tras descargar un PDF hay que extraerlo antes de
# pasarlo al modelo. La cadena es una invariante, no una preferencia.
_BINARY_TO_TEXT_CHAIN: dict[str, tuple[str, ...]] = {
    "download_paper": ("read_paper", "convert_to_markdown"),
}


@dataclass(slots=True, frozen=True)
class SelectionContext:
    """Todo lo que el selector necesita para una iteración. Inmutable."""

    iteration_index: int  # 1-based, tal como lo emite run_followup_loop
    query_type: str  # de SmartToolRouter.classify
    last_tool: str | None  # tool de la iteración previa, None en la primera
    suggested_tool: str | None  # mcp_suggestion del payload previo, si la hubo


class ToolSelector:
    """Elige una tool del conjunto disponible según el contexto.

    El conjunto se fija al construir (las tools que la rama puede usar). La
    clasificación query→tipo se delega en el router ya existente para no
    duplicar la tabla de keywords.
    """

    def __init__(
        self,
        available_tools: Sequence[str],
        tool_query_types: dict[str, str],
    ) -> None:
        if not available_tools:
            raise ValueError("available_tools must not be empty")
        # dict.fromkeys preserva orden y deduplica: el recorrido determinista
        # del paso 4 necesita un orden estable y sin repetidos.
        self._tools: tuple[str, ...] = tuple(dict.fromkeys(available_tools))
        self._tool_set = frozenset(self._tools)
        self._tool_query_types = tool_query_types

    def select(self, ctx: SelectionContext) -> str:
        """Tool para esta iteración. Garantiza devolver una del conjunto."""
        forced = self._forced_chain_tool(ctx.last_tool)
        if forced is not None:
            return forced

        if ctx.suggested_tool in self._tool_set:
            return ctx.suggested_tool

        affine = self._affine_tool(ctx.query_type)
        if affine is not None and affine != ctx.last_tool:
            return affine

        return self._sweep(ctx.iteration_index, ctx.last_tool)

    def _forced_chain_tool(self, last_tool: str | None) -> str | None:
        """Tool obligatoria tras una que produjo binario, si está disponible.

        Si ninguna tool de extracción está en el conjunto se devuelve None y
        la selección sigue con las reglas normales — no se inventa una tool
        que la rama no tiene.
        """
        if last_tool is None:
            return None
        for candidate in _BINARY_TO_TEXT_CHAIN.get(last_tool, ()):
            if candidate in self._tool_set:
                return candidate
        return None

    def _affine_tool(self, query_type: str) -> str | None:
        """Primera tool del conjunto cuyo tipo coincide con *query_type*.

        Respeta el orden del conjunto para que el desempate sea estable.
        """
        for tool in self._tools:
            if self._tool_query_types.get(tool) == query_type:
                return tool
        return None

    def _sweep(self, iteration_index: int, last_tool: str | None) -> str:
        """Recorrido determinista del conjunto evitando repetir la última.

        El módulo del índice preserva el barrido posicional histórico (misma
        secuencia para la misma entrada → tests reproducibles); el salto solo
        actúa si repetiríamos la última tool habiendo alternativas.
        """
        pick = self._tools[(iteration_index - 1) % len(self._tools)]
        if pick == last_tool and len(self._tools) > 1:
            return self._tools[iteration_index % len(self._tools)]
        return pick
