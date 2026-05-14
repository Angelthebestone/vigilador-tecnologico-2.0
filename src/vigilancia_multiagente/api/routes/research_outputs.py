import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from vigilancia_multiagente.application.evaluation.obsolescence_detector import ObsolescenceDetector

from vigilancia_multiagente.api.dependencies import (
    branch_coordinator,
    branch_result_repository,
    embedding_gateway,
    evidence_linker,
    event_log,
    execution_client,
    graph_snapshot_repository,
    graph_service,
    metrics_service,
    provider_registry,
    report_repository,
    serper_client,
    session_repository,
    vector_index,
)

from vigilancia_multiagente.application.evaluation.hype_detector import HypeDetector
from vigilancia_multiagente.application.fusion.decision_assistant import DecisionAssistant
from vigilancia_multiagente.application.graph.knowledge_graph_service import GraphPayload
from vigilancia_multiagente.infra.embeddings.gemini_gateway import TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research")


@router.get("/{session_id}/report")
async def get_report(session_id: UUID) -> dict[str, object]:
    report = await report_repository.get(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "session_id": str(session_id),
        "executive_summary": report.executive_summary,
        "technical_section": report.technical_section,
        "commercial_section": report.commercial_section,
        "risk_section": report.risk_section,
        "cross_analysis": report.cross_analysis,
        "recommendations": [
            {"text": r.text, "priority": r.priority, "based_on": r.based_on}
            for r in report.recommendations
        ],
        "total_sources_consulted": report.total_sources_consulted,
        "total_learnings": report.total_learnings,
        "confidence_score": report.confidence_score,
        "generated_at": report.generated_at.isoformat() if hasattr(report.generated_at, "isoformat") else report.generated_at,
    }


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
    return await _graph_payload_for_session(session_id)


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
    return await _analytics_for_session(session_id)


@router.post("/{session_id}/graph/path")
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


@router.post("/{session_id}/decision")
async def decision_analysis(session_id: UUID, question: str = Query(...)) -> dict:
    assistant = DecisionAssistant()
    branch_results = await branch_result_repository.list_by_session(session_id)
    report = await assistant.analyze(question, branch_results)
    return {"session_id": str(session_id), "report": report}


async def _graph_for_session(session_id: UUID) -> GraphPayload:
    snapshot = await graph_snapshot_repository.get_graph_snapshot(session_id)
    if snapshot is not None:
        return _graph_from_snapshot(session_id, snapshot)
    return await _build_graph_for_session(session_id)


async def _build_graph_for_session(session_id: UUID) -> GraphPayload:
    results = await branch_result_repository.list_by_session(session_id)
    findings = [finding for result in results for finding in result.findings]
    sources = evidence_linker.deduplicate_sources(list(results))

    topic: str | None = None
    patents: list[dict] = []
    try:
        session = await session_repository.get_by_id(session_id)
        if session is not None:
            topic = session.user_query
        if serper_client is not None and topic:
            patent_result = await serper_client.search_patents(topic)
            patents = patent_result.items
    except Exception as exc:
        logger.warning("Failed for session %s: %s", session_id, exc)

    return graph_service.build(session_id, findings, sources, topic=topic, patents=patents)


async def _graph_payload_for_session(session_id: UUID) -> dict[str, object]:
    snapshot = await graph_snapshot_repository.get_graph_snapshot(session_id)
    if snapshot is not None:
        analytics = snapshot.get("analytics")
        return {
            "session_id": str(session_id),
            "nodes": list(snapshot.get("nodes", [])),
            "edges": list(snapshot.get("edges", [])),
            "analytics": analytics if isinstance(analytics, dict) else {},
        }
    return _graph_payload(await _build_graph_for_session(session_id))


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


async def _analytics_for_session(session_id: UUID) -> dict[str, object]:
    snapshot = await graph_snapshot_repository.get_graph_snapshot(session_id)
    if snapshot is not None:
        analytics = snapshot.get("analytics")
        if isinstance(analytics, dict) and analytics:
            return analytics
    graph = await _graph_for_session(session_id)
    return _analytics_payload(graph_service.analytics(graph))


def _graph_from_snapshot(session_id: UUID, snapshot: dict[str, object]) -> GraphPayload:
    raw_session_id = snapshot.get("session_id", session_id)
    return GraphPayload(
        session_id=UUID(str(raw_session_id)),
        nodes=list(snapshot.get("nodes", [])),
        edges=list(snapshot.get("edges", [])),
    )


@router.post("/{session_id}/obsolescence")
async def analyze_obsolescence(session_id: UUID, tech: str = Query(...)) -> dict:
    detector = ObsolescenceDetector()

    brave_results: list | None = None
    exa_results: list | None = None

    try:
        brave_provider = provider_registry.get("brave")
        brave_resp = await execution_client.execute_tool(
            brave_provider, "brave_news_search", {"query": tech}
        )
        brave_results = brave_resp.payload.get("results", [])
    except Exception as exc:
        logger.warning("Failed for session %s: %s", session_id, exc)
        brave_results = None

    try:
        exa_provider = provider_registry.get("exa")
        exa_resp = await execution_client.execute_tool(
            exa_provider, "web_search_advanced_exa", {"query": tech}
        )
        exa_results = exa_resp.payload.get("results", [])
    except Exception as exc:
        logger.warning("Failed for session %s: %s", session_id, exc)
        exa_results = None

    result = await detector.analyze(tech, brave_news_results=brave_results, exa_company_results=exa_results)
    return {"session_id": str(session_id), "tech": tech, "result": result}


@router.post("/{session_id}/hype-analysis")
async def hype_analysis(session_id: UUID, tech: str = Query(...)) -> dict:
    arxiv_results = await _tool_results("arxiv", "search_papers", {"query": tech})
    exa_results = await _tool_results("exa", "web_search_advanced_exa", {"query": f"{tech} startups companies funding"})
    firecrawl_results = await _tool_results("firecrawl", "firecrawl_scrape", {"url": tech})
    serper_results = None
    if serper_client is not None:
        try:
            serper_results = (await serper_client.search_patents(tech)).items
        except Exception as exc:
            logger.warning("Serper patents failed for session %s: %s", session_id, exc)

    if all(result is None for result in (arxiv_results, exa_results, firecrawl_results, serper_results)):
        raise HTTPException(status_code=501, detail="Hype analysis providers are not available")

    detector = HypeDetector()
    report = await detector.analyze(
        tech,
        arxiv_papers=arxiv_results,
        exa_companies=exa_results,
        firecrawl_prototypes=firecrawl_results,
        serper_patents=serper_results,
    )
    return {"session_id": str(session_id), "report": report}


def _source_payload(source) -> dict[str, object]:
    return {
        "id": str(source.id),
        "url": source.url,
        "title": source.title,
        "provider": source.provider,
        "branch_type": source.branch_type.value.lower(),
        "accessed_at": source.accessed_at.isoformat(),
    }


@router.get("/{session_id}/graph/ecosystem")
async def get_ecosystem(session_id: UUID, seed: str = Query(..., min_length=1), depth: int = Query(2, ge=1, le=5)) -> dict[str, object]:
    """Discover technology ecosystem from a seed term."""
    from vigilancia_multiagente.api.dependencies import graph_service
    graph = await _graph_for_session(session_id)
    ecosystem = graph_service.discover_ecosystem(seed, graph, depth=depth)
    return {"session_id": str(session_id), "seed": seed, "depth": depth, "ecosystem": ecosystem}


@router.get("/{session_id}/graph/search-cross-session")
async def search_cross_session(
    session_id: UUID,
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
) -> dict[str, object]:
    """Search findings across ALL sessions (not just current)."""
    query_vector = await embedding_gateway.embed(query, task_type=TaskType.RETRIEVAL_QUERY)
    vector_records = await vector_index.list_by_session(None, limit=limit * 20)
    results = await graph_service.search_across_sessions(
        query, query_vector, vector_records, limit=limit,
    )
    return {"session_id": str(session_id), "query": query, "limit": limit, "results": results}


async def _tool_results(provider_name: str, tool_name: str, arguments: dict[str, object]) -> list | None:
    try:
        provider = provider_registry.get(provider_name)
        response = await execution_client.execute_tool(provider, tool_name, arguments)
    except Exception as exc:
        logger.warning("%s:%s failed: %s", provider_name, tool_name, exc)
        return None
    payload = response.payload
    for key in ("results", "items", "organic", "papers", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []
