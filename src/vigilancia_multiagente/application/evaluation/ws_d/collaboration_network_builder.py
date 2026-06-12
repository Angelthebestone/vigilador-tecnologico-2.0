"""Constructor de redes de colaboracion (co-autores, co-inventores).

Implementa CollaborationNetworkBuilder. Extiende GraphBuilder (spec 006)
con nodos Author/Inventor y edges co_author/co_inventor.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from uuid import uuid4

from vigilancia_multiagente.application.graph.graph_builder import GraphBuilder
from vigilancia_multiagente.domain.evaluation_entities import (
    CollaborationNetwork,
    CollaborationNode,
)
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.collaboration_network import (
    CollaborationNetworkBuilder,
)

logger = logging.getLogger(__name__)


class CollaborationNetworkBuilderImpl(CollaborationNetworkBuilder):
    """Construye redes de co-autoria/co-invencion desde fuentes."""

    def __init__(self, graph_builder: GraphBuilder | None = None) -> None:
        self._graph_builder = graph_builder or GraphBuilder()

    async def build(
        self,
        sources: list[SourceRef],
    ) -> CollaborationNetwork:
        author_map: dict[str, CollaborationNode] = {}
        edge_weights: dict[tuple[str, str], int] = defaultdict(int)

        for src in sources:
            authors = self._extract_authors(src)
            for author in authors:
                if author.node_id not in author_map:
                    author_map[author.node_id] = author

            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    a_id = authors[i].node_id
                    b_id = authors[j].node_id
                    if a_id != b_id:
                        key = (min(a_id, b_id), max(a_id, b_id))
                        edge_weights[key] += 1

        nodes = sorted(author_map.values(), key=lambda n: n.centrality, reverse=True)
        edges = list(edge_weights.items())
        edges_list = [(a, b, w) for (a, b), w in edges]

        centrality = self._compute_centrality(nodes, edges_list)
        network = CollaborationNetwork(
            network_id=uuid4(),
            nodes=nodes,
            edges=edges_list,
            centrality_metrics=centrality,
        )
        bubbles = self.detect_bubbles(network)

        return CollaborationNetwork(
            network_id=uuid4(),
            nodes=nodes,
            edges=edges_list,
            centrality_metrics=centrality,
            bubble_clusters=bubbles,
        )

    def detect_bubbles(
        self,
        network: CollaborationNetwork,
        max_bubble_size: int = 8,
    ) -> list[list[str]]:
        node_ids = {n.node_id for n in network.nodes}
        adjacency: dict[str, set[str]] = {nid: set() for nid in node_ids}
        for a, b, _ in network.edges:
            if a in adjacency and b in adjacency:
                adjacency[a].add(b)
                adjacency[b].add(a)

        visited: set[str] = set()
        bubbles: list[list[str]] = []

        for nid in node_ids:
            if nid in visited:
                continue
            component = self._bfs_component(nid, adjacency, visited)
            if 2 < len(component) <= max_bubble_size:
                edge_set = {(a, b) for a, b, _ in network.edges}
                total_pairs = len(component) * (len(component) - 1) / 2
                internal_edges = sum(
                    1 for a in component for b in component if a < b and (a, b) in edge_set
                )
                density = internal_edges / max(total_pairs, 1)
                if density > 0.6:
                    bubbles.append(sorted(component))

        return bubbles

    def _extract_authors(self, source: SourceRef) -> list[CollaborationNode]:
        result: list[CollaborationNode] = []
        raw = source.url or source.title or ""
        parts = raw.replace("https://", "").replace("http://", "").split("/")
        domains = [p for p in parts if p and "." in p]
        for domain in domains[:3]:
            name = domain.split(".")[0].capitalize() if domain.split(".")[0] else "Unknown"
            node_id = f"author:{name.lower()}"
            result.append(
                CollaborationNode(
                    node_id=node_id,
                    label=name,
                    role="author",
                    centrality=1.0,
                )
            )
        return result

    def _compute_centrality(
        self,
        nodes: list[CollaborationNode],
        edges: list[tuple[str, str, int]],
    ) -> dict[str, float]:
        total = len(nodes)
        if total < 2:
            return {}
        degrees: dict[str, int] = defaultdict(int)
        for a, b, _ in edges:
            degrees[a] += 1
            degrees[b] += 1
        max_deg = max(degrees.values()) if degrees else 1
        return {n.node_id: degrees.get(n.node_id, 0) / max_deg for n in nodes}

    @staticmethod
    def _bfs_component(
        start: str,
        adjacency: dict[str, set[str]],
        visited: set[str],
    ) -> list[str]:
        component: list[str] = []
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    stack.append(neighbor)
        return component
