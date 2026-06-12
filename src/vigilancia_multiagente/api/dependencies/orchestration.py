"""Orchestration services — orchestrator, coordinator, approve use case."""

from __future__ import annotations

from typing import Any, cast

from vigilancia_multiagente.application.execution.branch_coordinator import BranchCoordinator
from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService
from vigilancia_multiagente.application.orchestration.approve_research_usecase import (
    ApproveResearchUseCase,
)
from vigilancia_multiagente.application.orchestration.orchestrator_service import (
    OrchestratorService,
)
from vigilancia_multiagente.application.research.ad_hoc_tools_service import (
    AdHocResearchToolsService,
)
from vigilancia_multiagente.application.research.document_conversion_service import (
    DocumentConversionService,
)
from vigilancia_multiagente.domain.ports.markitdown_port import MarkitdownPort
from vigilancia_multiagente.infra.mcp.markitdown_mcp import MarkitdownProvider
from vigilancia_multiagente.infra.persistence.postgres_repositories import (
    PostgresGraphSnapshotRepository,
)


def build_orchestration_services(
    s: dict[str, Any],
    g: dict[str, Any],
    e: dict[str, Any],
    agents: dict[str, Any],
) -> dict[str, Any]:
    """Orchestrator, coordinator, approve use case — the top-level flow."""
    o: dict[str, Any] = {}
    ad_hoc = AdHocResearchToolsService(s["execution_client"], s["provider_registry"])
    o["ad_hoc_research_tools"] = ad_hoc
    _markitdown_provider = MarkitdownProvider(
        execution_client=s["markitdown_execution_client"],
        provider_registry=s["provider_registry"],
    )
    o["document_conversion_service"] = DocumentConversionService(
        cast(MarkitdownPort, _markitdown_provider),
    )
    o["trend_forecaster"] = TrendForecasterService()
    o["branch_coordinator"] = BranchCoordinator(
        agents["agents"],
        s["branch_result_repository"],
        event_publisher=e["event_publisher"],
    )
    o["orchestrator"] = OrchestratorService(
        s["session_repository"],
        e["cross_session_service"],
        report_generator=e["report_generator"],
        trend_forecaster=o["trend_forecaster"],
        source_scorer=g["source_scorer_service"],
    )

    from vigilancia_multiagente.api.routes.reports import store_report

    o["graph_snapshot_repository"] = PostgresGraphSnapshotRepository(s["database"])
    o["approve_research_usecase"] = ApproveResearchUseCase(
        session_repository=s["session_repository"],
        plan_repository=s["plan_repository"],
        branch_result_repository=s["branch_result_repository"],
        report_repository=s["report_repository"],
        orchestrator=o["orchestrator"],
        branch_coordinator=o["branch_coordinator"],
        agents=agents["agents"],
        artifact_service=e["artifact_service"],
        evidence_linker=e["evidence_linker"],
        report_synthesizer=e["report_synthesizer"],
        embedding_gateway=s["embedding_gateway"],
        vector_index=s["vector_index"],
        global_knowledge_repository=e["global_knowledge_repository"],
        graph_service=e["graph_service"],
        graph_snapshot_repository=o["graph_snapshot_repository"],
        conversation_service=e["conversation_service"],
        report_generator=e["report_generator"],
        metrics_service=e["metrics_service"],
        branch_kpi_service=e["branch_kpi_service"],
        event_log=e["event_log"],
        llm_client=s["llm_client"],
        store_report=store_report,
    )
    return o
