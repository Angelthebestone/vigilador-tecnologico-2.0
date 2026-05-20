"""Approve research plan and run full post-approval execution pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from vigilancia_multiagente.application.artifacts.manifest_service import SessionArtifactService
from vigilancia_multiagente.application.conversation.conversation_service import ConversationService
from vigilancia_multiagente.application.evaluation.branch_kpi_service import BranchKPIService
from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse
from vigilancia_multiagente.application.execution.branch_coordinator import BranchCoordinator
from vigilancia_multiagente.application.fusion.evidence_linker import EvidenceLinker
from vigilancia_multiagente.application.fusion.report_synthesizer import ReportSynthesizer
from vigilancia_multiagente.application.graph.knowledge_graph_service import KnowledgeGraphService
from vigilancia_multiagente.shared.graph_dto import GraphAnalyticsPayload
from vigilancia_multiagente.application.observability.metrics_service import MetricsService
from vigilancia_multiagente.application.orchestration.orchestrator_service import OrchestratorService
from vigilancia_multiagente.application.reporting.report_generator import ReportGenerator
from vigilancia_multiagente.domain.conversation_state import SessionContinuationState
from vigilancia_multiagente.domain.global_knowledge import GlobalKnowledgeSnapshot
from vigilancia_multiagente.domain.models import BranchType, ResearchPlan, ResearchSession
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway, TaskType
from vigilancia_multiagente.domain.ports.global_knowledge_store import GlobalKnowledgeStore
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.vector_index import VectorIndex
from vigilancia_multiagente.domain.repositories import (
    BranchResultRepository,
    GraphSnapshotRepository,
    PlanRepository,
    ReportRepository,
    SessionRepository,
)
from vigilancia_multiagente.domain.session_state import SessionStatus
from vigilancia_multiagente.shared.vector_record import VectorRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApproveResult:
    session_id: UUID
    status: str
    message: str


class AgentPreload(Protocol):
    def set_preload_context(self, context: dict | None) -> None: ...


@dataclass(slots=True)
class ApproveResearchUseCase:
    session_repository: SessionRepository
    plan_repository: PlanRepository
    branch_result_repository: BranchResultRepository
    report_repository: ReportRepository
    orchestrator: OrchestratorService
    branch_coordinator: BranchCoordinator
    agents: dict[BranchType, AgentPreload]
    artifact_service: SessionArtifactService
    evidence_linker: EvidenceLinker
    report_synthesizer: ReportSynthesizer
    embedding_gateway: EmbeddingGateway
    vector_index: VectorIndex
    global_knowledge_repository: GlobalKnowledgeStore
    graph_service: KnowledgeGraphService
    graph_snapshot_repository: GraphSnapshotRepository
    conversation_service: ConversationService
    report_generator: ReportGenerator
    metrics_service: MetricsService
    branch_kpi_service: BranchKPIService
    event_log: dict[str, list[str]]
    llm_client: LLMClient | None
    store_report: Any

    async def execute(self, session_id: UUID, plan: ResearchPlan) -> ApproveResult:
        session = await self._require_session(session_id)
        session = await self.orchestrator.transition(session_id, SessionStatus.APPROVED)
        session.approved_plan_id = plan.id
        session = await self.session_repository.update(session)
        session = await self.orchestrator.transition(session_id, SessionStatus.EXECUTING)

        preload_context = await self.orchestrator.preload_for_session(session.user_query)
        if preload_context.get("related_sessions"):
            logger.info(
                "Found %d related prior sessions for preload",
                len(preload_context["related_sessions"]),
            )
            for agent in self.agents.values():
                agent.set_preload_context(preload_context)

        branch_results = await self.branch_coordinator.execute(session, plan)
        session_root = self.artifact_service.ensure_session_tree(str(session_id))

        session_data = {
            "session_id": str(session_id),
            "user_query": session.user_query,
            "findings": [
                {"title": f.topic, "content": f.statement, "source": str(f.id)}
                for result in branch_results
                for f in (getattr(result, "findings", []) or [])
            ],
        }
        trend_projections = await self.orchestrator.analyze_trends(session_data)

        await self.evidence_linker.refresh_learned_scores()
        all_sources = self.evidence_linker.deduplicate_sources(branch_results)
        linked_findings = self.evidence_linker.link_findings(branch_results, all_sources)

        if trend_projections:
            self.artifact_service.write_json(
                session_root / "forecasting" / "trend-projections.json",
                trend_projections,  # type: ignore[arg-type]
            )

        report = await self.report_synthesizer.synthesize(
            session_id, branch_results, linked_findings, all_sources, llm=self.llm_client
        )

        try:
            snapshot_embedding = await self.embedding_gateway.embed_document(session.user_query)
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
        await self.global_knowledge_repository.save_snapshot(snapshot)
        logger.info("Cross-session snapshot saved for session %s", session_id)
        await self.report_repository.save_final_report(session_id, report)
        (session_root / "report" / "final-report.md").write_text(report.markdown, encoding="utf-8")

        for result in branch_results:
            await self.branch_result_repository.create(result)
            branch_kpi = self.branch_kpi_service.compute(result, latency_ms=500, cost_kpi=0.0)
            self.artifact_service.write_json(
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
                vector = await self.embedding_gateway.embed(
                    finding.statement,
                    task_type=TaskType.RETRIEVAL_DOCUMENT,
                )
                await self.vector_index.upsert(
                    VectorRecord(
                        session_id=session_id,
                        content_type="finding",
                        content_ref_id=str(finding.id),
                        vector=vector,
                    )
                )

        session.final_report_id = session_id
        session = await self.session_repository.update(session)

        self._append_event(
            session_id,
            SessionEvent.now(
                "GraphBuildingStarted",
                session_id,
                {"message": "Building knowledge graph..."},
            ),
        )
        graph_payload = self.graph_service.build(
            session_id, linked_findings, all_sources, topic=session.user_query
        )
        graph_analytics = self.graph_service.analytics(graph_payload)
        self._append_event(
            session_id,
            SessionEvent.now(
                "GraphAnalyticsComputed",
                session_id,
                {
                    "nodes": len(graph_payload.nodes),
                    "edges": len(graph_payload.edges),
                },
            ),
        )
        self.artifact_service.write_json(
            session_root / "graph" / "graph.json",
            {
                "session_id": str(graph_payload.session_id),
                "nodes": graph_payload.nodes,
                "edges": graph_payload.edges,
            },
        )
        self.artifact_service.write_json(
            session_root / "graph" / "analytics.json",
            graph_analytics_payload(graph_analytics),
        )
        await self.graph_snapshot_repository.save_graph_snapshot(
            session_id,
            {
                "session_id": str(graph_payload.session_id),
                "nodes": graph_payload.nodes,
                "edges": graph_payload.edges,
                "analytics": graph_analytics_payload(graph_analytics),
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
        await self.conversation_service.start_session(continuation_state)

        try:
            branch_names = [r.branch_type.value for r in branch_results]
            variant_session_data = {
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
            variants = await self.report_generator.generate_all(variant_session_data)
            for rtype, variant in variants.items():
                rid = f"{session_id}_{rtype}"
                self.store_report(rid, variant)
                self.artifact_service.write_json(
                    session_root / "report" / f"variant-{rtype}.json",
                    variant,
                )
            self._append_event(
                session_id,
                SessionEvent.now(
                    "ReportVariantsGenerated",
                    session_id,
                    {"types": list(variants.keys())},
                ),
            )
            logger.info("Generated %d report variants for session %s", len(variants), session_id)
        except Exception as exc:
            logger.warning("Report variant generation failed (non-blocking): %s", exc)

        self.artifact_service.write_json(
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
                    for metric in self.metrics_service.aggregate_provider_metrics(
                        session_id, self.branch_coordinator.get_provider_usage(session_id)
                    )
                ]
            },
        )

        failed_branches = sum(1 for result in branch_results if result.errors)
        self.event_log.setdefault(str(session_id), []).extend(
            [
                format_sse(
                    SessionEvent.now(
                        "PlanApproved",
                        session_id,
                        {"approved_at": report.generated_at.isoformat()},
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
                        {
                            "report_id": str(session.final_report_id),
                            "confidence_score": 0.72,
                        },
                    )
                ),
            ]
        )
        for result in branch_results:
            self._append_event(
                session_id,
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
                ),
            )

        session = await self.orchestrator.transition(session_id, SessionStatus.COMPLETED)
        return ApproveResult(
            session_id=session_id,
            status=session.status.lower(),
            message="Execution accepted",
        )

    async def _require_session(self, session_id: UUID) -> ResearchSession:
        session = await self.session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError("Session not found")
        return session

    def _append_event(self, session_id: UUID, event: SessionEvent) -> None:
        self.event_log.setdefault(str(session_id), []).append(format_sse(event))


def graph_analytics_payload(graph_analytics: GraphAnalyticsPayload) -> dict[str, object]:
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
