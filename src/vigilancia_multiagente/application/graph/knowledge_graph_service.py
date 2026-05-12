from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from heapq import heappop, heappush
from math import cos, pi, sin, sqrt
from uuid import UUID

from vigilancia_multiagente.domain.models import (
    Finding,
    GraphCentrality,
    GraphCluster,
    GraphPathResult,
    GraphSearchHit,
    SourceRef,
)


@dataclass(slots=True)
class GraphPayload:
    session_id: UUID
    nodes: list[dict[str, object]]
    edges: list[dict[str, object]]


@dataclass(slots=True)
class GraphAnalyticsPayload:
    session_id: UUID
    node_count: int
    edge_count: int
    centrality: list[GraphCentrality]
    clusters: list[GraphCluster]
    layout: list[dict[str, object]]
    traversals: dict[str, list[str]]


class KnowledgeGraphService:
    def build(self, session_id: UUID, findings: list[Finding], sources: list[SourceRef]) -> GraphPayload:
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        source_nodes = {source.id: f"source:{source.id}" for source in sources}
        for source in sources:
            nodes.append(
                {
                    "id": source_nodes[source.id],
                    "type": "SOURCE",
                    "label": source.title or source.url,
                    "metadata": {
                        "provider": source.provider,
                        "branch_type": source.branch_type.value,
                        "url": source.url,
                    },
                }
            )
        for finding in findings:
            finding_node = f"finding:{finding.id}"
            nodes.append(
                {
                    "id": finding_node,
                    "type": "FINDING",
                    "label": finding.topic,
                    "metadata": {
                        "statement": finding.statement,
                        "confidence": finding.confidence,
                        "tags": list(finding.tags),
                    },
                }
            )
            for source_id in finding.source_ids:
                source_node = source_nodes.get(source_id)
                if source_node is None:
                    continue
                edges.append(
                    {
                        "id": f"{finding_node}->{source_node}",
                        "source": finding_node,
                        "target": source_node,
                        "relation_type": "REFERENCES",
                        "weight": 1.0,
                    }
                )
        return GraphPayload(session_id=session_id, nodes=nodes, edges=edges)

    def analytics(self, graph: GraphPayload) -> GraphAnalyticsPayload:
        adjacency, undirected_edges = self._adjacency(graph)
        node_ids = [str(node["id"]) for node in graph.nodes]
        degree = self._degree_centrality(node_ids, adjacency)
        betweenness = self._betweenness_centrality(node_ids, adjacency)
        pagerank = self._pagerank(node_ids, adjacency)
        centrality = [
            GraphCentrality(
                node_id=node_id,
                degree=degree.get(node_id, 0.0),
                betweenness=betweenness.get(node_id, 0.0),
                pagerank=pagerank.get(node_id, 0.0),
            )
            for node_id in node_ids
        ]
        clusters = self._clusters(node_ids, adjacency)
        layout = self._layout(node_ids, adjacency)
        root = self._primary_node(node_ids, adjacency)
        traversals = {
            "bfs": self.traverse(graph, root, "bfs") if root else [],
            "dfs": self.traverse(graph, root, "dfs") if root else [],
        }
        del undirected_edges
        return GraphAnalyticsPayload(
            session_id=graph.session_id,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            centrality=centrality,
            clusters=clusters,
            layout=layout,
            traversals=traversals,
        )

    def traverse(self, graph: GraphPayload, start_node_id: str, strategy: str = "bfs") -> list[str]:
        adjacency, _ = self._adjacency(graph)
        if start_node_id not in adjacency:
            return []
        visited: set[str] = set()
        order: list[str] = []
        if strategy == "dfs":
            stack = [start_node_id]
            while stack:
                node_id = stack.pop()
                if node_id in visited:
                    continue
                visited.add(node_id)
                order.append(node_id)
                stack.extend(reversed(adjacency[node_id]))
            return order
        queue: deque[str] = deque([start_node_id])
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            order.append(node_id)
            queue.extend(adjacency[node_id])
        return order

    def shortest_path(self, graph: GraphPayload, source_node_id: str, target_node_id: str) -> GraphPathResult:
        adjacency, edge_lookup = self._adjacency(graph)
        if source_node_id not in adjacency or target_node_id not in adjacency:
            return GraphPathResult(source_node_id, target_node_id, [], [], float("inf"))
        queue: list[tuple[float, str]] = [(0.0, source_node_id)]
        distances: dict[str, float] = {source_node_id: 0.0}
        previous: dict[str, str] = {}
        while queue:
            cost, node_id = heappop(queue)
            if node_id == target_node_id:
                break
            if cost > distances.get(node_id, float("inf")):
                continue
            for neighbor in adjacency[node_id]:
                new_cost = cost + 1.0
                if new_cost < distances.get(neighbor, float("inf")):
                    distances[neighbor] = new_cost
                    previous[neighbor] = node_id
                    heappush(queue, (new_cost, neighbor))
        if target_node_id not in distances:
            return GraphPathResult(source_node_id, target_node_id, [], [], float("inf"))
        node_ids = [target_node_id]
        while node_ids[-1] != source_node_id:
            node_ids.append(previous[node_ids[-1]])
        node_ids.reverse()
        edge_ids = []
        for left, right in zip(node_ids, node_ids[1:], strict=True):
            edge_ids.append(edge_lookup[frozenset({left, right})])
        return GraphPathResult(source_node_id, target_node_id, node_ids, edge_ids, distances[target_node_id])

    def search(
        self,
        graph: GraphPayload,
        query: str,
        query_vector: list[float] | None = None,
        vector_records: list[dict[str, object]] | None = None,
        limit: int = 5,
    ) -> list[GraphSearchHit]:
        candidates: list[GraphSearchHit] = []
        vector_by_node_id = self._vector_lookup(vector_records or [])
        query_terms = {token for token in query.lower().split() if token}
        for node in graph.nodes:
            node_id = str(node["id"])
            label = str(node.get("label", ""))
            metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
            text_score = self._text_score(query_terms, label, metadata)
            vector_score = self._vector_score(query_vector, vector_by_node_id.get(node_id))
            score = max(text_score, vector_score)
            if score <= 0.0:
                continue
            explanation = "lexical match" if text_score >= vector_score else "embedding similarity"
            candidates.append(
                GraphSearchHit(
                    node_id=node_id,
                    label=label,
                    score=round(score, 4),
                    explanation=explanation,
                )
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:limit]

    def sources_for_node(self, node_id: str, graph: GraphPayload) -> list[str]:
        related_source_ids: set[str] = set()
        for edge in graph.edges:
            if edge["source"] == node_id and str(edge["target"]).startswith("source:"):
                related_source_ids.add(str(edge["target"]))
            if edge["target"] == node_id and str(edge["source"]).startswith("source:"):
                related_source_ids.add(str(edge["source"]))
        return sorted(related_source_ids)

    def _adjacency(self, graph: GraphPayload) -> tuple[dict[str, list[str]], dict[frozenset[str], str]]:
        adjacency: dict[str, list[str]] = defaultdict(list)
        edge_lookup: dict[frozenset[str], str] = {}
        for edge in graph.edges:
            source = str(edge["source"])
            target = str(edge["target"])
            adjacency[source].append(target)
            adjacency[target].append(source)
            edge_lookup[frozenset({source, target})] = str(edge["id"])
        for node in graph.nodes:
            adjacency.setdefault(str(node["id"]), [])
        for neighbors in adjacency.values():
            neighbors[:] = sorted(dict.fromkeys(neighbors))
        return adjacency, edge_lookup

    def _degree_centrality(self, node_ids: list[str], adjacency: dict[str, list[str]]) -> dict[str, float]:
        if len(node_ids) <= 1:
            return {node_id: 0.0 for node_id in node_ids}
        denominator = len(node_ids) - 1
        return {node_id: len(adjacency[node_id]) / denominator for node_id in node_ids}

    def _betweenness_centrality(self, node_ids: list[str], adjacency: dict[str, list[str]]) -> dict[str, float]:
        betweenness = {node_id: 0.0 for node_id in node_ids}
        for source in node_ids:
            stack: list[str] = []
            predecessors: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
            sigma = {node_id: 0.0 for node_id in node_ids}
            sigma[source] = 1.0
            distance = {node_id: -1 for node_id in node_ids}
            distance[source] = 0
            queue: deque[str] = deque([source])
            while queue:
                v = queue.popleft()
                stack.append(v)
                for w in adjacency[v]:
                    if distance[w] < 0:
                        queue.append(w)
                        distance[w] = distance[v] + 1
                    if distance[w] == distance[v] + 1:
                        sigma[w] += sigma[v]
                        predecessors[w].append(v)
            delta = {node_id: 0.0 for node_id in node_ids}
            while stack:
                w = stack.pop()
                for v in predecessors[w]:
                    if sigma[w]:
                        delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != source:
                    betweenness[w] += delta[w]
        scale = 1.0 / max(1, (len(node_ids) - 1) * (len(node_ids) - 2))
        return {node_id: value * scale for node_id, value in betweenness.items()}

    def _pagerank(self, node_ids: list[str], adjacency: dict[str, list[str]]) -> dict[str, float]:
        if not node_ids:
            return {}
        damping = 0.85
        n = len(node_ids)
        ranks = {node_id: 1.0 / n for node_id in node_ids}
        for _ in range(25):
            new_ranks = {node_id: (1.0 - damping) / n for node_id in node_ids}
            sink_rank = sum(ranks[node_id] for node_id in node_ids if not adjacency[node_id])
            for node_id in node_ids:
                neighbors = adjacency[node_id]
                if not neighbors:
                    continue
                share = ranks[node_id] / len(neighbors)
                for neighbor in neighbors:
                    new_ranks[neighbor] += damping * share
            if sink_rank:
                sink_share = damping * sink_rank / n
                for node_id in node_ids:
                    new_ranks[node_id] += sink_share
            delta = sum(abs(new_ranks[node_id] - ranks[node_id]) for node_id in node_ids)
            ranks = new_ranks
            if delta < 1e-8:
                break
        total = sum(ranks.values()) or 1.0
        return {node_id: value / total for node_id, value in ranks.items()}

    def _clusters(self, node_ids: list[str], adjacency: dict[str, list[str]]) -> list[GraphCluster]:
        labels = {node_id: node_id for node_id in node_ids}
        changed = True
        iterations = 0
        while changed and iterations < 20:
            changed = False
            iterations += 1
            for node_id in node_ids:
                neighbors = adjacency[node_id]
                if not neighbors:
                    continue
                counts: dict[str, int] = defaultdict(int)
                for neighbor in neighbors:
                    counts[labels[neighbor]] += 1
                best_label = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
                if labels[node_id] != best_label:
                    labels[node_id] = best_label
                    changed = True
        clusters_by_label: dict[str, list[str]] = defaultdict(list)
        for node_id, label in labels.items():
            clusters_by_label[label].append(node_id)
        clusters: list[GraphCluster] = []
        for index, (label, members) in enumerate(sorted(clusters_by_label.items()), start=1):
            if len(members) == 1:
                score = 0.0
            else:
                internal_edges = 0
                for node_id in members:
                    internal_edges += sum(1 for neighbor in adjacency[node_id] if neighbor in members)
                possible_edges = max(1, len(members) * (len(members) - 1))
                score = internal_edges / possible_edges
            clusters.append(GraphCluster(cluster_id=f"cluster-{index}", node_ids=sorted(members), score=round(score, 4)))
        return clusters

    def _layout(self, node_ids: list[str], adjacency: dict[str, list[str]]) -> list[dict[str, object]]:
        if not node_ids:
            return []
        center = (0.0, 0.0)
        radius = max(1.0, len(node_ids) / pi)
        layout = []
        for index, node_id in enumerate(node_ids):
            angle = 2 * pi * index / len(node_ids)
            neighbor_count = len(adjacency[node_id])
            layout.append(
                {
                    "node_id": node_id,
                    "x": round(center[0] + radius * cos(angle), 4),
                    "y": round(center[1] + radius * sin(angle), 4),
                    "size": 1.0 + neighbor_count * 0.15,
                }
            )
        return layout

    def _primary_node(self, node_ids: list[str], adjacency: dict[str, list[str]]) -> str | None:
        if not node_ids:
            return None
        return max(node_ids, key=lambda node_id: (len(adjacency[node_id]), node_id))

    def _vector_lookup(self, vector_records: list[dict[str, object]]) -> dict[str, list[float]]:
        lookup: dict[str, list[float]] = {}
        for record in vector_records:
            content_ref_id = str(record.get("content_ref_id", ""))
            vector = record.get("vector")
            if not content_ref_id or not isinstance(vector, list):
                continue
            lookup[f"finding:{content_ref_id}"] = [float(item) for item in vector]
        return lookup

    def _vector_score(self, query_vector: list[float] | None, candidate_vector: list[float] | None) -> float:
        if not query_vector or not candidate_vector:
            return 0.0
        numerator = sum(left * right for left, right in zip(query_vector, candidate_vector, strict=False))
        left_norm = sqrt(sum(left * left for left in query_vector))
        right_norm = sqrt(sum(right * right for right in candidate_vector))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _text_score(self, query_terms: set[str], label: str, metadata: dict[str, object]) -> float:
        text = f"{label} " + " ".join(str(value) for value in metadata.values())
        tokens = {token.strip(".,:/_-").lower() for token in text.split() if token}
        if not tokens:
            return 0.0
        overlap = len(query_terms & tokens)
        if overlap:
            return overlap / max(len(query_terms), 1)
        lowered = label.lower()
        for term in query_terms:
            if term in lowered:
                return 0.5
        return 0.0
