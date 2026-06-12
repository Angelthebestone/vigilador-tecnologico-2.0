"""Build knowledge graph structures from findings and sources."""

from __future__ import annotations

from typing import cast
from uuid import UUID

import networkx as nx

from vigilancia_multiagente.domain.models import (
    EntityType,
    Finding,
    NamedEntity,
    SourceRef,
)
from vigilancia_multiagente.shared.graph_dto import GraphPayload


class GraphBuilder:
    """Constructs a knowledge graph (nodes + edges) from research artifacts.

    SRP: This class ONLY builds the graph. It does NOT analyse it.
    """

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

        # --- SOURCE nodes ---
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

        # --- FINDING nodes + FINDING→SOURCE edges ---
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

        # --- CONCEPT nodes from unique tags ---
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

        # --- CONCEPT ↔ CONCEPT edges via bipartite projection ---
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

        # --- SOURCE → CONCEPT edges ---
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
                type_prefix = "person" if entity.entity_type == EntityType.PERSON else "company"
                node_id = f"{type_prefix}:{entity.name.lower().replace(' ', '_')}"
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
