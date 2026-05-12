from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from vigilancia_multiagente.api.dependencies import (
    branch_coordinator,
    branch_result_repository,
    embedding_gateway,
    evidence_linker,
    event_log,
    graph_service,
    metrics_service,
    report_repository,
    vector_index,
)

from vigilancia_multiagente.infra.embeddings.gemini_gateway import TaskType

router = APIRouter(prefix="/research")


@router.get("/{session_id}/report")
async def get_report(session_id: UUID) -> dict[str, str]:
    report = await report_repository.get(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"session_id": str(session_id), "report": report}


@router.get("/{session_id}/sources")
async def get_sources(session_id: UUID) -> dict[str, object]:
    results = await branch_result_repository.list_by_session(session_id)
    sources = evidence_linker.deduplicate_sources(list(results))
    return {
        "session_id": str(session_id),
        "total": len(sources),
        "items": [_source_payload(source) for source in sources],
    }


@router.get("/{session_id}/providers")
async def get_providers(session_id: UUID) -> dict[str, object]:
    metrics = metrics_service.aggregate_provider_metrics(session_id, branch_coordinator.get_provider_usage(session_id))
    return {
        "session_id": str(session_id),
        "providers": [
            {
                "name": metric.provider_name,
                "transport": "http",
                "status": "active",
                "avg_latency_ms": metric.avg_latency_ms,
                "error_rate": metric.error_rate,
                "retry_rate": metric.retry_rate,
                "latency_buckets": metric.latency_buckets,
            }
            for metric in metrics
        ],
    }


@router.get("/{session_id}/stream")
async def stream_session(session_id: UUID) -> PlainTextResponse:
    events = event_log.get(str(session_id), [])
    return PlainTextResponse("\n".join(events), media_type="text/event-stream")


@router.get("/{session_id}/graph")
async def get_graph(session_id: UUID) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    return _graph_payload(graph)


@router.get("/{session_id}/graph/nodes")
async def get_graph_nodes(session_id: UUID) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    return {"session_id": str(session_id), "total": len(graph.nodes), "items": graph.nodes}


@router.get("/{session_id}/graph/edges")
async def get_graph_edges(session_id: UUID) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    return {"session_id": str(session_id), "total": len(graph.edges), "items": graph.edges}


@router.get("/{session_id}/graph/analytics")
async def get_graph_analytics(session_id: UUID) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    analytics = graph_service.analytics(graph)
    return _analytics_payload(analytics)


@router.get("/{session_id}/graph/path")
async def get_graph_path(session_id: UUID, source_node_id: str = Query(...), target_node_id: str = Query(...)) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    path = graph_service.shortest_path(graph, source_node_id, target_node_id)
    if not path.node_ids:
        raise HTTPException(status_code=404, detail="Path not found")
    return {
        "session_id": str(session_id),
        "source_node_id": path.source_node_id,
        "target_node_id": path.target_node_id,
        "node_ids": path.node_ids,
        "edge_ids": path.edge_ids,
        "total_cost": path.total_cost,
    }


@router.get("/{session_id}/graph/search")
async def search_graph(session_id: UUID, query: str = Query(..., min_length=1)) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    query_vector = await embedding_gateway.embed(query, task_type=TaskType.RETRIEVAL_QUERY)
    vectors = await vector_index.list_by_session(session_id)
    hits = graph_service.search(
        graph,
        query,
        query_vector=query_vector,
        vector_records=[
            {"content_ref_id": record.content_ref_id, "vector": record.vector}
            for record in vectors
        ],
    )
    return {
        "session_id": str(session_id),
        "query": query,
        "total": len(hits),
        "items": [
            {
                "node_id": hit.node_id,
                "label": hit.label,
                "score": hit.score,
                "explanation": hit.explanation,
            }
            for hit in hits
        ],
    }


@router.get("/{session_id}/graph/{node_id}/sources")
async def get_node_sources(session_id: UUID, node_id: str) -> dict[str, object]:
    graph = await _graph_for_session(session_id)
    return {"session_id": str(session_id), "node_id": node_id, "source_node_ids": graph_service.sources_for_node(node_id, graph)}


async def _graph_for_session(session_id: UUID):
    results = await branch_result_repository.list_by_session(session_id)
    findings = [finding for result in results for finding in result.findings]
    sources = evidence_linker.deduplicate_sources(list(results))
    return graph_service.build(session_id, findings, sources)


def _graph_payload(graph) -> dict[str, object]:
    analytics = graph_service.analytics(graph)
    return {
        "session_id": str(graph.session_id),
        "nodes": graph.nodes,
        "edges": graph.edges,
        "analytics": _analytics_payload(analytics),
    }


def _analytics_payload(analytics) -> dict[str, object]:
    return {
        "session_id": str(analytics.session_id),
        "node_count": analytics.node_count,
        "edge_count": analytics.edge_count,
        "centrality": [
            {
                "node_id": item.node_id,
                "degree": item.degree,
                "betweenness": item.betweenness,
                "pagerank": item.pagerank,
            }
            for item in analytics.centrality
        ],
        "clusters": [
            {"cluster_id": item.cluster_id, "node_ids": item.node_ids, "score": item.score}
            for item in analytics.clusters
        ],
        "layout": analytics.layout,
        "traversals": analytics.traversals,
    }


def _source_payload(source) -> dict[str, object]:
    return {
        "id": str(source.id),
        "url": source.url,
        "title": source.title,
        "provider": source.provider,
        "branch_type": source.branch_type.value.lower(),
        "accessed_at": source.accessed_at.isoformat(),
    }
