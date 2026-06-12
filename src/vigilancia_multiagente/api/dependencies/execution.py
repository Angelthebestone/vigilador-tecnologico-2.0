"""Execution services — source scorer, linker, synthesizer, KPIs, memory, reports."""

from __future__ import annotations

from typing import Any, cast

from vigilancia_multiagente.application.artifacts.manifest_service import SessionArtifactService
from vigilancia_multiagente.application.clarification.clarification_service import (
    ClarificationService,
)
from vigilancia_multiagente.application.conversation.conversation_service import ConversationService
from vigilancia_multiagente.application.evaluation.branch_kpi_service import BranchKPIService
from vigilancia_multiagente.application.evaluation.golden_cases_runner import GoldenCasesRunner
from vigilancia_multiagente.application.evaluation.prompt_regression_service import (
    PromptRegressionService,
)
from vigilancia_multiagente.application.evaluation.source_scorer import (
    SourceScorer,
)
from vigilancia_multiagente.application.fusion.evidence_linker import EvidenceLinker
from vigilancia_multiagente.application.fusion.report_synthesizer import ReportSynthesizer
from vigilancia_multiagente.application.graph.knowledge_graph_service import KnowledgeGraphService
from vigilancia_multiagente.application.memory.cross_session_service import CrossSessionService
from vigilancia_multiagente.application.observability.metrics_service import MetricsService
from vigilancia_multiagente.application.planning.plan_builder import PlanBuilder
from vigilancia_multiagente.application.reporting.report_generator import ReportGenerator
from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher
from vigilancia_multiagente.domain.ports.global_knowledge_store import GlobalKnowledgeStore
from vigilancia_multiagente.infra.events.in_memory_event_publisher import InMemoryEventPublisher
from vigilancia_multiagente.infra.persistence.global_knowledge_repository import (
    GlobalKnowledgeRepository,
)

from .assurance import build_assurance_services
from .data_intelligence import build_data_intelligence_services
from .deep_analysis import build_deep_analysis_services
from .source_quality import build_source_quality_services
from .strategic_signals import build_strategic_signals_services


def build_execution_services(s: dict[str, Any], g: dict[str, Any]) -> dict[str, Any]:
    """Source scorer, linker, synthesizer, KPIs, memory, reports."""
    e: dict[str, Any] = {}
    e["clarification_service"] = ClarificationService(prompt_loader=s["prompt_loader"])
    e["plan_builder"] = PlanBuilder(prompt_loader=s["prompt_loader"])
    source_scorer = SourceScorer()
    e["source_scorer"] = source_scorer
    e["evidence_linker"] = EvidenceLinker(
        source_scorer=source_scorer,
        trust_repository=g["source_trust_repository"],
    )
    event_log: dict[str, list[str]] = {}
    e["event_log"] = event_log
    event_publisher: EventPublisher = InMemoryEventPublisher(event_log)
    e["event_publisher"] = event_publisher
    assurance_services = build_assurance_services(s, e)
    e["report_assurance_errors"] = assurance_services["errors_sink"]
    e["report_quality_gate"] = assurance_services["gate"]
    e["isotonic_calibrator"] = assurance_services["calibrator"]

    sq_services = build_source_quality_services(s, g, e)
    e["source_quality_step"] = sq_services["source_quality_step"]

    di_services = build_data_intelligence_services(s, g, e)
    e["data_intelligence_step"] = di_services["data_intelligence_step"]

    da_services = build_deep_analysis_services(s, g, e)
    e["deep_analysis_step"] = da_services["deep_analysis_step"]

    ss_services = build_strategic_signals_services(s, g, e)
    e["strategic_signals_step"] = ss_services["strategic_signals_step"]

    if assurance_services["calibrator"] is not None:
        from vigilancia_multiagente.application.evaluation.hype_detector import (
            set_isotonic_calibrator,
        )

        set_isotonic_calibrator(assurance_services["calibrator"])
    e["report_synthesizer"] = ReportSynthesizer(
        event_publisher=event_publisher,
        source_scorer=source_scorer,
        prompt_loader=s["prompt_loader"],
        report_quality_gate=assurance_services["gate"],
        report_assurance_errors=assurance_services["errors_sink"],
    )
    e["graph_service"] = KnowledgeGraphService()
    e["metrics_service"] = MetricsService()
    e["branch_kpi_service"] = BranchKPIService()
    e["prompt_regression_service"] = PromptRegressionService()
    e["golden_cases_runner"] = GoldenCasesRunner()
    e["artifact_service"] = SessionArtifactService()
    e["conversation_service"] = ConversationService()
    e["global_knowledge_repository"] = cast(
        GlobalKnowledgeStore,
        GlobalKnowledgeRepository(s["database"]),
    )
    e["cross_session_service"] = CrossSessionService(
        e["global_knowledge_repository"],
        s["embedding_gateway"],
    )
    e["report_generator"] = ReportGenerator()
    return e
