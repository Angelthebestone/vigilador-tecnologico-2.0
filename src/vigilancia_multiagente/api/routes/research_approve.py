import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vigilancia_multiagente.api.dependencies import (
    agents,
    artifact_service,
    branch_coordinator,
    branch_kpi_service,
    branch_result_repository,
    conversation_service,
    embedding_gateway,
    event_log,
    evidence_linker,
    global_knowledge_repository,
    graph_service,
    graph_snapshot_repository,
    metrics_service,
    minimax_client,
    orchestrator,
    plan_repository,
    report_generator,
    report_repository,
    report_synthesizer,
    session_repository,
    vector_index,
)
from vigilancia_multiagente.api.routes.reports import store_report
from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse
from vigilancia_multiagente.domain.conversation_state import SessionContinuationState
from vigilancia_multiagente.domain.global_knowledge import GlobalKnowledgeSnapshot
from vigilancia_multiagente.domain.models import BranchConfig, BranchType, ResearchPlan
from vigilancia_multiagente.domain.session_state import SessionStatus
from vigilancia_multiagente.infra.embeddings.gemini_gateway import TaskType
from vigilancia_multiagente.infra.persistence.vector_index import VectorRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research")


class ApproveRequest(BaseModel):
    approved: bool


class ModifyPlanRequest(BaseModel):
    branch_type: BranchType | None = None
    focus_queries: list[str] | None = None
    mcp_providers: list[str] | None = None
    mcp_tool_profile: str | None = None
    priority_weight: int | None = None
    global_constraints: dict[str, object] | None = None


@router.post("/{session_id}/approve")
async def approve_plan(session_id: UUID, payload: ApproveRequest) -> dict[str, object]:
    session = await session_repository.get_by_id(session_id)
    if session is None:
        raise KeyError(f"Session not found: {session_id}")
    if not payload.approved:
        return {
            "session_id": str(session_id),
            "status": "rejected",
            "message": "Plan was not approved",
        }

    plan = await plan_repository.get_latest_for_session(session_id)
    if plan is None:
        raise KeyError(f"Plan not found for session: {session_id}")

    session = await orchestrator.transition(session_id, SessionStatus.APPROVED)
    session.approved_plan_id = plan.id
    session = await session_repository.update(session)
    session = await orchestrator.transition(session_id, SessionStatus.EXECUTING)

    preload_context = await orchestrator.preload_for_session(session.user_query)
    if preload_context.get("related_sessions"):
        logger.info(
            "Found %d related prior sessions for preload", len(preload_context["related_sessions"])
        )
        for agent in agents.values():
            agent.set_preload_context(preload_context)

    branch_results = await branch_coordinator.execute(session, plan)
    session_root = artifact_service.ensure_session_tree(str(session_id))

    # Build session_data for trend forecasting and other post-processing
    session_data = {
        "session_id": str(session_id),
        "user_query": session.user_query,
        "findings": [
            {"title": f.topic, "content": f.statement, "source": str(f.id)}
            for result in branch_results
            for f in (getattr(result, "findings", []) or [])
        ],
    }
    trend_projections = await orchestrator.analyze_trends(session_data)

    all_sources = evidence_linker.deduplicate_sources(branch_results)
    linked_findings = evidence_linker.link_findings(branch_results, all_sources)

    if trend_projections:
        artifact_service.write_json(
            session_root / "forecasting" / "trend-projections.json",
            trend_projections,
        )

    report = await report_synthesizer.synthesize(
        session_id, branch_results, linked_findings, all_sources, llm=minimax_client
    )

    try:
        snapshot_embedding = await embedding_gateway.embed_document(session.user_query)
    except Exception:
        snapshot_embedding = None
    extracted_entities = []
    for result in branch_results:
        for finding in result.findings:
            extracted_entities.append(
                {
                    "name": finding.topic,
                    "type": "concept",
                    "mentions": len(finding.source_ids),
                }
            )
    source_scores = {}
    for result in branch_results:
        for source in result.sources:
            source_scores[str(source.id)] = source.confidence
    snapshot = GlobalKnowledgeSnapshot(
        session_id=session_id,
        query_summary=session.user_query,
        embeddings=snapshot_embedding,
        entities=extracted_entities,
        source_scores=source_scores,
    )
    await global_knowledge_repository.save_snapshot(snapshot)
    logger.info("Cross-session snapshot saved for session %s", session_id)
    await report_repository.save_final_report(session_id, report)
    (session_root / "report" / "final-report.md").write_text(report.markdown, encoding="utf-8")

    for result in branch_results:
        await branch_result_repository.create(result)
        branch_kpi = branch_kpi_service.compute(result, latency_ms=500, cost_kpi=0.0)
        artifact_service.write_json(
            session_root / "metrics" / f"{result.branch_type.value.lower()}-kpis.json",
            {
                "branch_type": branch_kpi.branch_type.value,
                "coverage_kpi": branch_kpi.coverage_kpi,
                "precision_kpi": branch_kpi.precision_kpi,
                "latency_ms_kpi": branch_kpi.latency_ms_kpi,
                "cost_kpi": branch_kpi.cost_kpi,
            },
        )
        for finding in result.findings:
            vector = await embedding_gateway.embed(
                finding.statement,
                task_type=TaskType.RETRIEVAL_DOCUMENT,
            )
            await vector_index.upsert(
                VectorRecord(
                    session_id=session_id,
                    content_type="finding",
                    content_ref_id=str(finding.id),
                    vector=vector,
                )
            )

    session.final_report_id = session_id
    session = await session_repository.update(session)
    event_log[str(session_id)].append(
        format_sse(
            SessionEvent.now(
                "GraphBuildingStarted",
                session_id,
                {
                    "message": "Building knowledge graph...",
                },
            )
        )
    )
    graph_payload = graph_service.build(
        session_id, linked_findings, all_sources, topic=session.user_query
    )
    graph_analytics = graph_service.analytics(graph_payload)
    event_log[str(session_id)].append(
        format_sse(
            SessionEvent.now(
                "GraphAnalyticsComputed",
                session_id,
                {
                    "nodes": len(graph_payload.nodes),
                    "edges": len(graph_payload.edges),
                },
            )
        )
    )
    artifact_service.write_json(
        session_root / "graph" / "graph.json",
        {
            "session_id": str(graph_payload.session_id),
            "nodes": graph_payload.nodes,
            "edges": graph_payload.edges,
        },
    )
    artifact_service.write_json(
        session_root / "graph" / "analytics.json",
        _graph_analytics_payload(graph_analytics),
    )
    await graph_snapshot_repository.save_graph_snapshot(
        session_id,
        {
            "session_id": str(graph_payload.session_id),
            "nodes": graph_payload.nodes,
            "edges": graph_payload.edges,
            "analytics": _graph_analytics_payload(graph_analytics),
        },
    )

    all_findings = []
    for result in branch_results:
        for finding in result.findings:
            all_findings.append(
                {
                    "id": str(finding.id),
                    "title": finding.topic,
                    "content": finding.statement,
                    "summary": "",
                    "source": str(finding.source_ids[0]) if finding.source_ids else "",
                    "branch_type": result.branch_type.value,
                }
            )

    continuation_state = SessionContinuationState(
        session_id=session_id,
        research_graph={
            "nodes": graph_payload.nodes,
            "edges": graph_payload.edges,
        },
        findings_list=all_findings,
        source_registry=source_scores,
    )
    await conversation_service.start_session(continuation_state)

    # Generate multi-stakeholder report variants (non-blocking)
    try:
        branch_names = [r.branch_type.value for r in branch_results]
        session_data = {
            "query": session.user_query,
            "branches": branch_names,
            "sources": [
                {"name": s.title or str(s.id), "score": s.confidence}
                for r in branch_results
                for s in r.sources
            ],
            "findings": [
                {"id": str(f.id), "statement": f.statement, "topic": f.topic}
                for r in branch_results
                for f in r.findings
            ],
        }
        variants = await report_generator.generate_all(session_data)
        for rtype, variant in variants.items():
            rid = f"{session_id}_{rtype}"
            store_report(rid, variant)
            artifact_service.write_json(
                session_root / "report" / f"variant-{rtype}.json",
                variant,
            )
        event_log[str(session_id)].append(
            format_sse(
                SessionEvent.now(
                    "ReportVariantsGenerated",
                    session_id,
                    {
                        "types": list(variants.keys()),
                    },
                )
            )
        )
        logger.info("Generated %d report variants for session %s", len(variants), session_id)
    except Exception as exc:
        logger.warning("Report variant generation failed (non-blocking): %s", exc)

    artifact_service.write_json(
        session_root / "metrics" / "provider-metrics.json",
        {
            "providers": [
                {
                    "name": metric.provider_name,
                    "avg_latency_ms": metric.avg_latency_ms,
                    "error_rate": metric.error_rate,
                    "retry_rate": metric.retry_rate,
                    "latency_buckets": metric.latency_buckets,
                }
                for metric in metrics_service.aggregate_provider_metrics(
                    session_id, branch_coordinator.get_provider_usage(session_id)
                )
            ]
        },
    )
    failed_branches = sum(1 for result in branch_results if result.errors)
    event_log.setdefault(str(session_id), []).extend(
        [
            format_sse(
                SessionEvent.now(
                    "PlanApproved", session_id, {"approved_at": report.generated_at.isoformat()}
                )
            ),
            format_sse(
                SessionEvent.now(
                    "AllBranchesCompleted",
                    session_id,
                    {
                        "completed_branches": len(branch_results) - failed_branches,
                        "failed_branches": failed_branches,
                    },
                )
            ),
            format_sse(
                SessionEvent.now(
                    "ReportGenerated",
                    session_id,
                    {"report_id": str(session.final_report_id), "confidence_score": 0.72},
                )
            ),
        ]
    )
    for result in branch_results:
        event_log[str(session_id)].append(
            format_sse(
                SessionEvent.now(
                    "EvaluationComputed",
                    session_id,
                    {
                        "branch_type": result.branch_type.value,
                        "coverage_kpi": result.coverage_score or 0.0,
                        "precision_kpi": result.confidence_score or 0.0,
                        "latency_ms_kpi": 500,
                        "cost_kpi": 0.0,
                    },
                )
            )
        )

    session = await orchestrator.transition(session_id, SessionStatus.COMPLETED)

    return {
        "session_id": str(session_id),
        "status": session.status.lower(),
        "message": "Execution accepted",
    }


@router.post("/{session_id}/modify")
async def modify_plan(session_id: UUID, payload: ModifyPlanRequest) -> dict[str, object]:
    session = await session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    plan = await plan_repository.get_latest_for_session(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    updated_branches: list[BranchConfig] = []
    branch_updated = payload.branch_type is None
    for branch in plan.branches:
        if payload.branch_type is not None and branch.branch_type != payload.branch_type:
            updated_branches.append(branch)
            continue
        branch_updated = True
        updated_branches.append(
            BranchConfig(
                branch_type=branch.branch_type,
                focus_queries=payload.focus_queries or branch.focus_queries,
                mcp_providers=payload.mcp_providers or branch.mcp_providers,
                mcp_tool_profile=payload.mcp_tool_profile
                if payload.mcp_tool_profile is not None
                else branch.mcp_tool_profile,
                priority_weight=payload.priority_weight
                if payload.priority_weight is not None
                else branch.priority_weight,
                status=branch.status,
            )
        )
    if not branch_updated:
        raise HTTPException(status_code=404, detail="Branch not found in plan")

    modified_plan = ResearchPlan(
        id=uuid4(),
        session_id=session_id,
        version=plan.version + 1,
        branches=updated_branches,
        global_constraints={**plan.global_constraints, **(payload.global_constraints or {})},
        requires_approval=True,
        approved_at=None,
    )
    await plan_repository.create(modified_plan)
    return {
        "session_id": str(session_id),
        "status": "planning",
        "requires_approval": True,
        "plan": _plan_payload(modified_plan),
    }


def _plan_payload(plan: ResearchPlan) -> dict[str, object]:
    return {
        "id": str(plan.id),
        "version": plan.version,
        "system_base_version": plan.system_base_version,
        "requires_approval": plan.requires_approval,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "global_constraints": plan.global_constraints,
        "branches": [
            {
                "branch_type": branch.branch_type.value.lower(),
                "focus_queries": branch.focus_queries,
                "mcp_providers": branch.mcp_providers,
                "mcp_tool_profile": branch.mcp_tool_profile,
                "priority_weight": branch.priority_weight,
                "status": branch.status.value.lower(),
                "overlay_ref": branch.overlay_ref,
            }
            for branch in plan.branches
        ],
    }


def _graph_analytics_payload(graph_analytics: object) -> dict[str, object]:
    return {
        "session_id": str(graph_analytics.session_id),
        "node_count": graph_analytics.node_count,
        "edge_count": graph_analytics.edge_count,
        "centrality": [
            {
                "node_id": item.node_id,
                "degree": item.degree,
                "betweenness": item.betweenness,
                "pagerank": item.pagerank,
            }
            for item in graph_analytics.centrality
        ],
        "clusters": [
            {"cluster_id": item.cluster_id, "node_ids": item.node_ids, "score": item.score}
            for item in graph_analytics.clusters
        ],
        "layout": graph_analytics.layout,
        "traversals": graph_analytics.traversals,
    }
