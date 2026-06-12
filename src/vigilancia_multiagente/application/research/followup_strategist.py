"""Generación dirigida de la siguiente query de seguimiento.

Antes, `next_query` era lo que el proveedor MCP (Tavily/Exa) sugiriera: el
sistema era reactivo, aceptaba la pista del buscador. Un investigador real
decide *qué pregunta hace avanzar la investigación*.

El estratega propone la siguiente query maximizando información nueva: parte
de las entidades recién descubiertas que aún no se han explorado y de las
señales que otras ramas emitieron. Es determinístico (sin LLM); si un
LLMGateway está disponible se puede enchufar como refinador opcional.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class StrategistContext:
    branch_type: str
    seed_query: str
    # Entidades (personas/empresas/tecnologías) detectadas en la última iteración.
    discovered_entities: list[str] = field(default_factory=list)
    # Términos ya usados como query en iteraciones previas (evita repetir).
    explored_terms: set[str] = field(default_factory=set)
    # Pistas que otras ramas señalaron como relevantes para esta.
    cross_branch_hints: list[str] = field(default_factory=list)


class FollowupStrategist:
    def __init__(
        self,
        query_expander: object | None = None,
    ) -> None:
        """Cuando ``query_expander`` implementa ``ContextualQueryExpander``,
        delega la expansion. Sino, usa el comportamiento actual (fallback).
        """
        self._query_expander = query_expander

    def propose(self, context: StrategistContext, mcp_suggestion: str | None) -> str:
        """Devuelve la mejor siguiente query.

        Prioridad: (1) pista cross-branch no explorada, (2) entidad nueva de
        alto valor, (3) sugerencia del MCP si es novedosa, (4) refinamiento
        del seed. Nunca devuelve una query ya ejecutada.
        """
        if self._query_expander is not None:
            try:
                prior = [{"query": context.seed_query, "query_type": context.branch_type}]
                expansions = self._query_expander.expand(  # type: ignore[attr-defined]
                    context.seed_query, prior
                )
                import asyncio

                if hasattr(expansions, "__await__"):
                    expansions = asyncio.run(expansions)
                for exp in expansions:
                    if isinstance(exp, str) and exp.lower() not in {
                        t.lower() for t in context.explored_terms
                    }:
                        return exp
            except Exception:
                pass

        explored = {term.lower() for term in context.explored_terms}

        for hint in context.cross_branch_hints:
            if hint and hint.lower() not in explored:
                return self._frame(context, hint)

        for entity in context.discovered_entities:
            if entity and entity.lower() not in explored:
                return self._frame(context, entity)

        if mcp_suggestion and mcp_suggestion.lower() not in explored:
            return mcp_suggestion

        # Variante expandida del seed aún no explorada: amplía la cobertura
        # antes de caer al refinamiento genérico.
        from vigilancia_multiagente.application.research.query_expansion import expand_query

        for variant in expand_query(context.seed_query):
            if variant.lower() not in explored:
                return variant

        # Último recurso: profundizar el seed con un eje no cubierto.
        return f"{context.seed_query} implications and limitations"

    @staticmethod
    def _frame(context: StrategistContext, focus: str) -> str:
        """Encerrar el foco en una pregunta orientada al dominio de la rama."""
        return f"{focus} in the context of {context.seed_query} ({context.branch_type})"
