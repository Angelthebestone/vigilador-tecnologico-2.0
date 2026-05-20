"""Shared DTOs for knowledge graph payloads."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from vigilancia_multiagente.domain.models import GraphCentrality, GraphCluster


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
