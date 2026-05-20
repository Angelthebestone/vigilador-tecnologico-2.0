"""Analytics over knowledge graph payloads.

Computes centrality, community detection, layout, and traversals.
SRP: This class ONLY analyses the graph. It does NOT build it.
"""

from __future__ import annotations

from math import sqrt
from typing import cast

import networkx as nx
from networkx.algorithms.community import label_propagation_communities

from vigilancia_multiagente.domain.models import GraphCentrality, GraphCluster
from vigilancia_multiagente.shared.graph_dto import GraphAnalyticsPayload, GraphPayload


class GraphAnalytics:
    """Computes graph analytics: centrality, clusters, layout, traversals."""

    def analytics(self, graph: GraphPayload) -> GraphAnalyticsPayload:
        if not graph.nodes:
            return GraphAnalyticsPayload(
                session_id=graph.session_id,
                node_count=0,
                edge_count=0,
                centrality=[],
                clusters=[],
                layout=[],
                traversals={"bfs": [], "dfs": []},
            )

        G = self._to_nx(graph)
        node_ids = list(G.nodes())

        # Centralidad
        deg = nx.degree_centrality(G)
        btw = nx.betweenness_centrality(G)
        pr = nx.pagerank(G, weight="weight")
        centrality = [
            GraphCentrality(
                node_id=nid,
                degree=round(deg.get(nid, 0.0), 4),
                betweenness=round(btw.get(nid, 0.0), 4),
                pagerank=round(pr.get(nid, 0.0), 4),
            )
            for nid in node_ids
        ]

        # Clusters via Label Propagation
        clusters = self._clusters(G, node_ids)

        # Layout force-directed (Fruchterman-Reingold) → normalizado [-1, 1]
        layout = self._layout(G, node_ids)

        # Recorridos BFS/DFS desde el nodo con mayor grado
        root = max(node_ids, key=lambda nid: G.degree(nid)) if node_ids else None
        if root:
            bfs = [root] + [v for _, v in nx.bfs_edges(G, source=root)]
            dfs = [root] + [v for _, v in nx.dfs_edges(G, source=root)]
        else:
            bfs = dfs = []

        return GraphAnalyticsPayload(
            session_id=graph.session_id,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            centrality=centrality,
            clusters=clusters,
            layout=layout,
            traversals={"bfs": bfs, "dfs": dfs},
        )

    # ------------------------------------------------------------------
    # Internal: construir nx.Graph a partir del payload
    # ------------------------------------------------------------------

    @staticmethod
    def _to_nx(graph: GraphPayload) -> nx.Graph:
        G = nx.Graph()
        for node in graph.nodes:
            G.add_node(str(node["id"]))
        for edge in graph.edges:
            G.add_edge(
                str(edge["source"]),
                str(edge["target"]),
                id=str(edge["id"]),
                weight=float(cast(float, edge.get("weight", 1.0))),
            )
        return G

    # ------------------------------------------------------------------
    # Clusters con NetworkX + score de densidad interna
    # ------------------------------------------------------------------

    @staticmethod
    def _clusters(G: nx.Graph, node_ids: list[str]) -> list[GraphCluster]:
        communities = list(label_propagation_communities(G))
        clusters: list[GraphCluster] = []
        for index, community in enumerate(communities, start=1):
            members = sorted(community)
            sub = G.subgraph(members)
            internal = sub.number_of_edges()
            possible = max(1, len(members) * (len(members) - 1) // 2)
            score = internal / possible if len(members) > 1 else 0.0
            clusters.append(
                GraphCluster(cluster_id=f"cluster-{index}", node_ids=members, score=round(score, 4))
            )
        return clusters

    # ------------------------------------------------------------------
    # Layout force-directed (Fruchterman-Reingold vía NetworkX)
    # ------------------------------------------------------------------

    @staticmethod
    def _layout(G: nx.Graph, node_ids: list[str]) -> list[dict[str, object]]:
        if not node_ids:
            return []
        k = 2.0 / max(sqrt(len(node_ids)), 1.0)
        pos = nx.spring_layout(G, k=k, iterations=100, seed=42)
        xs = [pos[n][0] for n in node_ids]
        ys = [pos[n][1] for n in node_ids]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max(max_x - min_x, 1.0)
        range_y = max(max_y - min_y, 1.0)
        max_deg = max(G.degree(n) for n in node_ids) or 1
        layout = []
        for nid in node_ids:
            nx_pos = pos[nid]
            nx_norm = ((nx_pos[0] - min_x) / range_x) * 2.0 - 1.0
            ny_norm = ((nx_pos[1] - min_y) / range_y) * 2.0 - 1.0
            deg = G.degree(nid)
            size = 0.8 + (deg / max_deg) * 2.2
            layout.append(
                {
                    "node_id": nid,
                    "x": round(nx_norm, 4),
                    "y": round(ny_norm, 4),
                    "size": round(size, 4),
                }
            )
        return layout
