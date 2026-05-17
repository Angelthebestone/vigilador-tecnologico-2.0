"""Expansión de entidades como nuevas líneas de investigación.

El extractor híbrido + spaCy ya saca PERSON/COMPANY a nodos del grafo, pero
hoy son pasivos. Si una entidad aparece con alta centralidad (mucha gente
habla de ella, conecta muchos temas) es una señal de que merece su propia
investigación dedicada. La investigación se ramifica siguiendo lo que el
propio dato revela como importante, en vez de quedarse en el plan inicial.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.domain.models import GraphCentrality, NamedEntity

# Percentil mínimo de pagerank para considerar una entidad "central". 0.0-1.0.
_CENTRALITY_FLOOR = 0.15


@dataclass(slots=True)
class EntitySeed:
    entity_name: str
    query: str
    pagerank: float
    rationale: str


class EntitySeedExpander:
    def expand(
        self,
        entities: list[NamedEntity],
        centralities: list[GraphCentrality],
        max_seeds: int = 5,
    ) -> list[EntitySeed]:
        """Devuelve queries semilla derivadas de las entidades más centrales.

        Cruza las entidades extraídas con su centralidad en el grafo; las que
        superan el umbral se convierten en nuevas líneas de investigación.
        """
        rank_by_node = {c.node_id: c.pagerank for c in centralities}
        seeds: list[EntitySeed] = []
        seen: set[str] = set()

        for entity in entities:
            key = entity.name.lower()
            if key in seen:
                continue
            pagerank = rank_by_node.get(entity.name) or rank_by_node.get(str(entity.id), 0.0)
            if pagerank < _CENTRALITY_FLOOR:
                continue
            seen.add(key)
            focus = entity.affiliation or entity.entity_type.value.lower()
            seeds.append(
                EntitySeed(
                    entity_name=entity.name,
                    query=f"{entity.name} latest developments and {focus} relevance",
                    pagerank=round(pagerank, 4),
                    rationale=(
                        f"Entidad central (pagerank {pagerank:.3f}); "
                        f"amerita investigación dedicada."
                    ),
                )
            )

        seeds.sort(key=lambda s: s.pagerank, reverse=True)
        return seeds[:max_seeds]
