"""Knowledge Graph Service — Facade over GraphBuilder + GraphAnalytics.

Keeps the canonical public API so callers don't notice the split.
New code should prefer GraphBuilder / GraphAnalytics directly.
"""

from __future__ import annotations

from collections import defaultdict, deque
from itertools import pairwise
from typing import cast
from uuid import UUID

import networkx as nx
from scipy.spatial.distance import cosine as _cosine

from vigilancia_multiagente.application.graph.graph_analytics import GraphAnalytics
from vigilancia_multiagente.application.graph.graph_builder import GraphBuilder
from vigilancia_multiagente.domain.models import (
    Finding,
    GraphPathResult,
    GraphSearchHit,
    NamedEntity,
    SourceRef,
)
from vigilancia_multiagente.shared.graph_dto import GraphAnalyticsPayload, GraphPayload


class KnowledgeGraphService:
    """Facade that delegates build/analytics to dedicated classes.

    Also owns graph-traversal / search / ecosystem-discovery methods
    that don't belong in either builder or analytics.
    """

    def __init__(self) -> None:
        self._builder = GraphBuilder()
        self._analytics = GraphAnalytics()

    # ------------------------------------------------------------------
    # Delegated to GraphBuilder
    # ------------------------------------------------------------------

    def build(
        self,
        session_id: UUID,
        findings: list[Finding],
        sources: list[SourceRef],
        topic: str | None = None,
        patents: list[dict] | None = None,
        entities: list[NamedEntity] | None = None,
    ) -> GraphPayload:
        return self._builder.build(
            session_id, findings, sources, topic=topic, patents=patents, entities=entities
        )

    # ------------------------------------------------------------------
    # Delegated to GraphAnalytics
    # ------------------------------------------------------------------

    def analytics(self, graph: GraphPayload) -> GraphAnalyticsPayload:
        return self._analytics.analytics(graph)

    # ------------------------------------------------------------------
    # Recorridos y caminos
    # ------------------------------------------------------------------

    def traverse(self, graph: GraphPayload, start_node_id: str, strategy: str = "bfs") -> list[str]:
        G = self._to_nx(graph)
        if start_node_id not in G:
            return []
        if strategy == "dfs":
            return [start_node_id] + [v for _, v in nx.dfs_edges(G, source=start_node_id)]
        return [start_node_id] + [v for _, v in nx.bfs_edges(G, source=start_node_id)]

    def shortest_path(
        self, graph: GraphPayload, source_node_id: str, target_node_id: str
    ) -> GraphPathResult:
        G = self._to_nx(graph)
        if source_node_id not in G or target_node_id not in G:
            return GraphPathResult(source_node_id, target_node_id, [], [], float("inf"))
        try:
            node_ids = nx.shortest_path(
                G, source=source_node_id, target=target_node_id, weight="weight"
            )
        except nx.NetworkXNoPath:
            return GraphPathResult(source_node_id, target_node_id, [], [], float("inf"))
        edge_ids = []
        for left, right in pairwise(node_ids):
            eid = G.edges[left, right].get("id", f"{left}->{right}")
            edge_ids.append(eid)
        total_cost = float(len(edge_ids))
        return GraphPathResult(source_node_id, target_node_id, node_ids, edge_ids, total_cost)

    # ------------------------------------------------------------------
    # Búsqueda cross-session (vectores)
    # ------------------------------------------------------------------

    async def search_across_sessions(
        self,
        query: str,
        query_vector: list[float] | None = None,
        vector_records: list[dict[str, object]] | None = None,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        if not vector_records or not query_vector:
            return []
        candidates: list[tuple[float, str, str]] = []
        for record in vector_records:
            ref_id = str(record.get("content_ref_id", ""))
            raw_vector = record.get("vector")
            if not ref_id or not isinstance(raw_vector, list):
                continue
            node_vector = [float(item) for item in raw_vector]
            score = self._vector_score(query_vector, node_vector)
            if score <= 0.0:
                continue
            candidates.append((score, ref_id, f"finding:{ref_id}"))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "score": round(score, 4),
                "content_ref_id": ref_id,
                "node_id": node_id,
                "explanation": "embedding similarity",
            }
            for score, ref_id, node_id in candidates[:limit]
        ]

    # ------------------------------------------------------------------
    # Descubrimiento de ecosistema
    # ------------------------------------------------------------------

    def discover_ecosystem(
        self, seed: str, graph: GraphPayload, depth: int = 2
    ) -> dict[str, object]:
        if not graph.nodes:
            return {}
        node_by_id = {str(node["id"]): node for node in graph.nodes}
        G = self._to_nx(graph)
        seed_nodes = [
            str(node["id"]) for node in graph.nodes if seed.lower() in str(node["label"]).lower()
        ]
        if not seed_nodes:
            return {}
        visited: set[str] = set(seed_nodes)
        queue: deque[tuple[str, int]] = deque((n, 0) for n in seed_nodes)
        result: dict[str, object] = {
            "seed": seed,
            "seed_nodes": seed_nodes,
            "competes_with": [],
            "adopted_by": [],
            "depends_on": [],
            "emerging": [],
        }
        while queue:
            current, cur_depth = queue.popleft()
            if cur_depth >= depth:
                continue
            for neighbor in list(G.neighbors(current)) if current in G else []:
                is_new = neighbor not in visited
                if is_new:
                    visited.add(neighbor)
                    queue.append((neighbor, cur_depth + 1))
                current_node = node_by_id.get(current, {})
                neighbor_node = node_by_id.get(neighbor, {})
                cur_type = current_node.get("type", "")
                nbr_type = neighbor_node.get("type", "")
                if cur_type == "FINDING" and nbr_type == "SOURCE":
                    adopted = cast(list[dict[str, object]], result.setdefault("adopted_by", []))
                    adopted.append(
                        {
                            "finding_id": current,
                            "finding_label": current_node.get("label", ""),
                            "source_id": neighbor,
                            "source_label": neighbor_node.get("label", ""),
                        }
                    )
                if cur_depth > 0 and nbr_type == "FINDING":
                    depends = cast(list[dict[str, object]], result.setdefault("depends_on", []))
                    depends.append(
                        {
                            "source_node": current,
                            "target_node": neighbor,
                        }
                    )
        source_findings: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            src = str(edge["source"])
            tgt = str(edge["target"])
            if src.startswith("finding:") and tgt.startswith("source:"):
                source_findings[tgt].append(src)
        for source_id, finding_ids in source_findings.items():
            in_reach = [fid for fid in finding_ids if fid in visited]
            if len(in_reach) > 1:
                for i in range(len(in_reach)):
                    for j in range(i + 1, len(in_reach)):
                        cast(list[dict[str, object]], result.setdefault("competes_with", [])).append(
                            {
                                "source_id": source_id,
                                "finding_a": in_reach[i],
                                "finding_b": in_reach[j],
                            }
                        )
        for node in graph.nodes:
            node_id = str(node["id"])
            if node_id not in visited or node.get("type") != "FINDING":
                continue
            metadata = cast(dict[str, object], node["metadata"])
            confidence = metadata.get("confidence", 0)
            if isinstance(confidence, (int, float)) and confidence >= 0.8:
                tags = metadata.get("tags", [])
                cast(list[dict[str, object]], result.setdefault("emerging", [])).append(
                    {
                        "node_id": node_id,
                        "label": node.get("label", ""),
                        "confidence": confidence,
                        "tags": list(tags) if isinstance(tags, list) else [],
                    }
                )
        return result

    # ------------------------------------------------------------------
    # Búsqueda textual + vectorial en el grafo
    # ------------------------------------------------------------------

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
            metadata = cast(dict[str, object], node["metadata"])
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

    # ------------------------------------------------------------------
    # Helpers
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

    @staticmethod
    def _vector_lookup(vector_records: list[dict[str, object]]) -> dict[str, list[float]]:
        lookup: dict[str, list[float]] = {}
        for record in vector_records:
            content_ref_id = str(record.get("content_ref_id", ""))
            vector = record.get("vector")
            if not content_ref_id or not isinstance(vector, list):
                continue
            lookup[f"finding:{content_ref_id}"] = [float(item) for item in vector]
        return lookup

    @staticmethod
    def _vector_score(
        query_vector: list[float] | None, candidate_vector: list[float] | None
    ) -> float:
        if not query_vector or not candidate_vector:
            return 0.0
        return round(1.0 - _cosine(query_vector, candidate_vector), 4)

    @staticmethod
    def _text_score(query_terms: set[str], label: str, metadata: dict[str, object]) -> float:
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
