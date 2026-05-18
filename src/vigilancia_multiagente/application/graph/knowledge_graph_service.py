from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import pairwise
from math import sqrt
from typing import cast
from uuid import UUID

import networkx as nx
from networkx.algorithms.community import label_propagation_communities
from scipy.spatial.distance import cosine as _cosine

from vigilancia_multiagente.domain.models import (
    EntityType,
    Finding,
    GraphCentrality,
    GraphCluster,
    GraphPathResult,
    GraphSearchHit,
    NamedEntity,
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
    def build(
        self,
        session_id: UUID,
        findings: list[Finding],
        sources: list[SourceRef],
        topic: str | None = None,
        patents: list[dict] | None = None,
        entities: list[NamedEntity] | None = None,
    ) -> GraphPayload:
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        source_nodes = {source.id: f"source:{source.id}" for source in sources}

        # --- Technology node from session topic ---
        if topic:
            nodes.append(
                {
                    "id": "technology:main",
                    "type": "TECHNOLOGY",
                    "label": topic,
                    "metadata": {"category": "emerging", "status": "active"},
                }
            )

        # --- Patent nodes from Serper results ---
        if patents:
            for patent in patents:
                patent_num = patent.get("patentNumber") or patent.get("title", "")
                patent_id = f"patent:{patent_num}"
                nodes.append(
                    {
                        "id": patent_id,
                        "type": "PATENT",
                        "label": patent.get("title", ""),
                        "metadata": {
                            "patent_number": patent.get("patentNumber", ""),
                            "assignee": patent.get("assignee", ""),
                            "filing_date": patent.get("filingDate", ""),
                            "status": patent.get("status", ""),
                            "snippet": patent.get("snippet", ""),
                            "url": patent.get("link", ""),
                        },
                    }
                )

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
                        "weight": round(finding.confidence, 4),
                    }
                )

        # --- Concept nodes from unique tags ---
        concept_data: dict[str, dict[str, object]] = {}
        for finding in findings:
            for tag in finding.tags:
                if tag not in concept_data:
                    concept_data[tag] = {"frequency": 0, "node_id": f"concept:{tag}"}
                concept_data[tag]["frequency"] += 1  # type: ignore[operator]
        for tag, data in concept_data.items():
            nodes.append(
                {
                    "id": data["node_id"],
                    "type": "CONCEPT",
                    "label": tag,
                    "metadata": {"frequency": data["frequency"]},
                }
            )

        # --- related_to edges via bipartite projection ---
        concept_names = {tag for f in findings for tag in f.tags}
        if concept_names:
            B = nx.Graph()
            for finding in findings:
                fid = str(finding.id)
                B.add_node(fid, bipartite=0)
                for tag in finding.tags:
                    B.add_node(tag, bipartite=1)
                    B.add_edge(fid, tag)
            proj = nx.bipartite.weighted_projected_graph(B, concept_names, ratio=True)
            for tag_a, tag_b, data in proj.edges(data=True):
                edges.append(
                    {
                        "id": f"concept:{tag_a}->concept:{tag_b}",
                        "source": f"concept:{tag_a}",
                        "target": f"concept:{tag_b}",
                        "relation_type": "related_to",
                        "weight": round(data["weight"], 4),
                    }
                )

        # --- references edges: SOURCE to CONCEPT ---
        source_concepts: dict[str, set[str]] = {}
        for finding in findings:
            for source_id in finding.source_ids:
                source_key = source_nodes.get(source_id)
                if source_key is None:
                    continue
                if source_key not in source_concepts:
                    source_concepts[source_key] = set()
                for tag in finding.tags:
                    source_concepts[source_key].add(tag)
        for source_key, concept_tags in source_concepts.items():
            for tag in sorted(concept_tags):
                edges.append(
                    {
                        "id": f"{source_key}->concept:{tag}",
                        "source": source_key,
                        "target": f"concept:{tag}",
                        "relation_type": "REFERENCES",
                        "weight": 1.0,
                    }
                )

        # --- PERSON / COMPANY nodes from entity extraction ---
        if entities:
            # Dedup por nombre normalizado
            entity_by_name: dict[str, NamedEntity] = {}
            for entity in entities:
                key = entity.name.lower()
                if key not in entity_by_name:
                    entity_by_name[key] = entity

            for entity in entity_by_name.values():
                node_id = f"{'person' if entity.entity_type == EntityType.PERSON else 'company'}:{entity.name.lower().replace(' ', '_')}"
                nodes.append(
                    {
                        "id": node_id,
                        "type": entity.entity_type.value,
                        "label": entity.name,
                        "metadata": {
                            "affiliation": entity.affiliation or "",
                            "branch_type": entity.branch_type.value,
                            "confidence": entity.confidence,
                        },
                    }
                )
                # FINDING -[mentions]-> PERSON/COMPANY
                for finding in findings:
                    if any(sid in entity.source_ids for sid in finding.source_ids):
                        edges.append(
                            {
                                "id": f"finding:{finding.id}->{node_id}",
                                "source": f"finding:{finding.id}",
                                "target": node_id,
                                "relation_type": "mentions",
                                "weight": round(entity.confidence, 4),
                            }
                        )

            # COMPANY -[employs]-> PERSON  (si comparte afiliación)
            persons = [e for e in entity_by_name.values() if e.entity_type == EntityType.PERSON]
            companies = [e for e in entity_by_name.values() if e.entity_type == EntityType.COMPANY]
            for person in persons:
                if not person.affiliation:
                    continue
                for company in companies:
                    if (
                        person.affiliation.lower() in company.name.lower()
                        or company.name.lower() in person.affiliation.lower()
                    ):
                        pid = f"person:{person.name.lower().replace(' ', '_')}"
                        cid = f"company:{company.name.lower().replace(' ', '_')}"
                        edges.append(
                            {
                                "id": f"{cid}-employs->{pid}",
                                "source": cid,
                                "target": pid,
                                "relation_type": "employs",
                                "weight": 0.8,
                            }
                        )

            # COMPANY -[assigned]-> PATENT  (por assignee en metadata)
            for node in nodes:
                if node.get("type") != "PATENT":
                    continue
                assignee = str(cast(dict, node.get("metadata", {})).get("assignee", "")).lower()
                if not assignee:
                    continue
                for company in companies:
                    if company.name.lower() in assignee or assignee in company.name.lower():
                        cid = f"company:{company.name.lower().replace(' ', '_')}"
                        edges.append(
                            {
                                "id": f"{cid}-assigned->{node['id']}",
                                "source": cid,
                                "target": str(node["id"]),
                                "relation_type": "assigned",
                                "weight": 0.9,
                            }
                        )

        return GraphPayload(session_id=session_id, nodes=nodes, edges=edges)

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
    # Analítica completa (centralidad, clusters, layout, recorridos)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Helpers de búsqueda vectorial y textual
    # ------------------------------------------------------------------

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
