"""Composition root — wire all services in dependency order."""
from __future__ import annotations

from pathlib import Path
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
from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer, SourceScorerService
from vigilancia_multiagente.application.execution.branch_coordinator import BranchCoordinator
from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService
from vigilancia_multiagente.application.fusion.evidence_linker import EvidenceLinker
from vigilancia_multiagente.application.fusion.report_synthesizer import ReportSynthesizer
from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter
from vigilancia_multiagente.application.governance.system_base_loader import SystemBaseLoader
from vigilancia_multiagente.application.graph.knowledge_graph_service import KnowledgeGraphService
from vigilancia_multiagente.application.memory.cross_session_service import CrossSessionService
from vigilancia_multiagente.application.observability.metrics_service import MetricsService
from vigilancia_multiagente.application.orchestration.approve_research_usecase import (
    ApproveResearchUseCase,
)
from vigilancia_multiagente.application.orchestration.orchestrator_service import (
    OrchestratorService,
)
from vigilancia_multiagente.application.planning.plan_builder import PlanBuilder
from vigilancia_multiagente.application.reporting.report_generator import ReportGenerator
from vigilancia_multiagente.application.research.ad_hoc_tools_service import AdHocResearchToolsService
from vigilancia_multiagente.application.research.document_conversion_service import (
    DocumentConversionService,
)
from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher
from vigilancia_multiagente.domain.ports.global_knowledge_store import GlobalKnowledgeStore
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.markitdown_port import MarkitdownPort
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader
from vigilancia_multiagente.domain.ports.provider_registry import ProviderRegistry
from vigilancia_multiagente.domain.ports.reranker import Reranker
from vigilancia_multiagente.domain.ports.scholarly_works_gateway import ScholarlyWorksGateway
from vigilancia_multiagente.domain.ports.source_trust_store import SourceTrustStore
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor
from vigilancia_multiagente.domain.ports.vector_index import VectorIndex
from vigilancia_multiagente.domain.system_base import SystemBase
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
from vigilancia_multiagente.infra.events.in_memory_event_publisher import InMemoryEventPublisher
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.mcp.execution_client import MCPExecutionClient
from vigilancia_multiagente.infra.mcp.markitdown_mcp import MarkitdownProvider
from vigilancia_multiagente.infra.mcp.mcp_cache import MCPSmartCache
from vigilancia_multiagente.infra.mcp.provider_registry import MCPProviderRegistry
from vigilancia_multiagente.infra.persistence.global_knowledge_repository import (
    GlobalKnowledgeRepository,
)
from vigilancia_multiagente.infra.persistence.postgres_repositories import (
    PostgresBranchResultRepository,
    PostgresGraphSnapshotRepository,
    PostgresPlanRepository,
    PostgresReportRepository,
    PostgresSessionRepository,
)
from vigilancia_multiagente.infra.persistence.source_trust_repository import (
    SourceTrustRepository,
)
from vigilancia_multiagente.infra.openalex.openalex_client import (
    OpenAlexScholarlyWorksGateway,
)
from vigilancia_multiagente.infra.persistence.vector_index import PostgresVectorIndex
from vigilancia_multiagente.infra.prompts.loader import FilesystemPromptLoader
from vigilancia_multiagente.infra.reranking.semantic_reranker import SemanticReranker

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ── Factory: Session / Infrastructure services ──────────────────────────
def _build_session_services() -> dict[str, Any]:
    """DB connection, repositories, MCP clients, embeddings, LLM, vector index."""
    srv: dict[str, Any] = {}
    srv["session_repository"] = PostgresSessionRepository(database)
    srv["plan_repository"] = PostgresPlanRepository(database)
    srv["branch_result_repository"] = PostgresBranchResultRepository(database)
    srv["report_repository"] = PostgresReportRepository(database)
    srv["vector_index"] = cast(VectorIndex, PostgresVectorIndex(database))
    srv["embedding_gateway"] = cast(EmbeddingGateway, GeminiEmbeddingGateway())
    srv["llm_client"] = cast(LLMClient, MiniMaxClient())
    srv["minimax_client"] = srv["llm_client"]
    mcp_cache = MCPSmartCache()
    srv["mcp_cache"] = mcp_cache
    srv["execution_client"] = cast(ToolExecutor, MCPExecutionClient(mcp_cache=mcp_cache))
    srv["markitdown_execution_client"] = MCPExecutionClient(mcp_cache=mcp_cache)
    srv["playwright_execution_client"] = MCPExecutionClient(mcp_cache=mcp_cache)
    provider_registry = MCPProviderRegistry()
    _mcp_manifest = PROJECT_ROOT / "config/mcp-providers.yaml"
    if not _mcp_manifest.exists():
        _mcp_manifest = PROJECT_ROOT / "src/vigilancia_multiagente/infra/mcp/mcp-providers.json"
    provider_registry.load_manifest(_mcp_manifest)
    provider_registry.ensure_standard_providers(settings)
    provider_registry.validate_ready(
        (
            "tavily_search", "tavily_extract", "web_search_exa",
            "web_search_advanced_exa", "read_url", "guess_datetime_url",
            "brave_web_search", "brave_news_search", "firecrawl_scrape",
            "search_google_scholar_key_words", "search_papers", "fetch",
            "execute_code", "list_libraries", "visualize", "convert_to_markdown",
            "browser_navigate", "browser_snapshot", "browser_screenshot",
            "browser_click", "browser_type", "browser_select_option",
            "browser_hover", "browser_tabs", "browser_network_requests",
            "browser_network_request", "understand_image",
        )
    )
    srv["provider_registry"] = provider_registry
    srv["prompt_loader"] = cast(PromptLoader, FilesystemPromptLoader())
    srv["scholarly_works_gateway"] = cast(
        ScholarlyWorksGateway, OpenAlexScholarlyWorksGateway()
    )
    srv["reranker"] = cast(Reranker, SemanticReranker(srv["embedding_gateway"]))
    srv["settings"] = settings
    srv["database"] = database
    srv["PROJECT_ROOT"] = PROJECT_ROOT
    return srv


# ── Factory: Governance services ────────────────────────────────────────
def _build_governance_services(s: dict[str, Any]) -> dict[str, Any]:
    """System base, prompt composer, contract loader, smart router."""
    g: dict[str, Any] = {}
    source_trust_repository = cast(SourceTrustStore, SourceTrustRepository(s["database"]))
    g["source_trust_repository"] = source_trust_repository
    source_scorer_service = SourceScorerService(repository=source_trust_repository)
    g["source_scorer_service"] = source_scorer_service
    g["smart_router"] = SmartToolRouter(source_scorer=source_scorer_service)
    contracts_root = PROJECT_ROOT / "specs/002-vigilancia-multiagente/contracts"
    g["contracts_root"] = contracts_root
    g["governance_loader"] = GovernanceContractLoader(
        contracts_root, prompt_loader=s["prompt_loader"]
    )
    g["system_base_loader"] = SystemBaseLoader(contracts_root)
    system_base: SystemBase | None = None
    if settings.system_base_enabled:
        try:
            system_base = g["system_base_loader"].load()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Failed to load system base: %s", exc)
    g["system_base"] = system_base
    g["prompt_composer"] = PromptComposer(prompt_loader=s["prompt_loader"])
    return g


# ── Factory: WS-E Output Assurance (spec 007 T029) ──────────────────────
def _build_assurance_services(
    s: dict[str, Any], e: dict[str, Any]
) -> dict[str, Any]:
    """ReportQualityGate + dependencias WS-E.

    Solo se materializa cuando `VT_EVAL_WS_E_ENABLED=true`. Cuando esta off,
    `gate` queda en `None` y `ReportSynthesizer` salta el quality gate
    preservando el comportamiento previo al spec 007.
    """
    settings_local = get_settings()
    errors_sink: list[Any] = []
    if not settings_local.eval_ws_e_enabled:
        return {"gate": None, "calibrator": None, "errors_sink": errors_sink}

    from vigilancia_multiagente.application.evaluation.audit.bias_auditor import (
        BiasAuditor,
    )
    from vigilancia_multiagente.application.evaluation.calibration.isotonic_calibrator import (
        IsotonicConfidenceCalibrator,
    )
    from vigilancia_multiagente.application.evaluation.forensic.jsonb_trace_writer import (
        JsonbForensicTraceWriter,
    )
    from vigilancia_multiagente.application.evaluation.report_quality_gate import (
        ReportQualityGate,
    )
    from vigilancia_multiagente.application.evaluation.ws_e.llm_falsification_prober import (
        LlmFalsificationProber,
    )
    from vigilancia_multiagente.application.evaluation.ws_e.llm_stakeholder_simulator import (
        LlmStakeholderSimulator,
    )
    from vigilancia_multiagente.infra.persistence.calibration_curve_repository import (
        PostgresCalibrationCurveRepository,
    )

    curve_repo = PostgresCalibrationCurveRepository(s["database"])
    calibrator = IsotonicConfidenceCalibrator(curve_repository=curve_repo)
    bias_auditor = BiasAuditor()
    forensic_writer = JsonbForensicTraceWriter()
    llm: LLMClient = s["llm_client"]
    prompt_loader: PromptLoader = s["prompt_loader"]
    stakeholder_simulator = LlmStakeholderSimulator(
        llm=llm, prompt_loader=prompt_loader, errors_sink=errors_sink
    )
    falsification_prober = LlmFalsificationProber(
        llm=llm, prompt_loader=prompt_loader, errors_sink=errors_sink
    )
    gate = ReportQualityGate(
        bias_auditor=bias_auditor,
        falsification_prober=falsification_prober,
        stakeholder_simulator=stakeholder_simulator,
        calibrator=calibrator,
        forensic_trace_writer=forensic_writer,
    )
    return {
        "gate": gate,
        "calibrator": calibrator,
        "errors_sink": errors_sink,
        "curve_repository": curve_repo,
    }


# ── Factory: Evaluation / Fusion / Memory services ──────────────────────
def _build_execution_services(s: dict[str, Any], g: dict[str, Any]) -> dict[str, Any]:
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
    assurance_services = _build_assurance_services(s, e)
    e["report_assurance_errors"] = assurance_services["errors_sink"]
    e["report_quality_gate"] = assurance_services["gate"]
    e["isotonic_calibrator"] = assurance_services["calibrator"]
    # Spec 007 T036: cablea el calibrator isotonico al HypeDetector para que
    # `buzz = max(0, substance // 2)` se reemplace por la curva empirica
    # cuando WS-E esta activo. Cuando esta off, calibrator=None y
    # HypeDetector mantiene la formula heuristica historica (fallback).
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
        GlobalKnowledgeStore, GlobalKnowledgeRepository(s["database"]),
    )
    e["cross_session_service"] = CrossSessionService(
        e["global_knowledge_repository"], s["embedding_gateway"],
    )
    e["report_generator"] = ReportGenerator()
    return e


# ── Factory: Agent services ─────────────────────────────────────────────
def _build_agent_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any],
) -> dict[str, Any]:
    """All 6 branch agents wired with governance and execution."""
    # Avoid circular import by lazy-importing agent classes inside factory
    from vigilancia_multiagente.application.agents.avances_agent import AvancesAgent
    from vigilancia_multiagente.application.agents.comercial_agent import ComercialAgent
    from vigilancia_multiagente.application.agents.competitivo_agent import CompetitivoAgent
    from vigilancia_multiagente.application.agents.oportunidades_agent import OportunidadesAgent
    from vigilancia_multiagente.application.agents.pi_normativa_agent import PiNormativaAgent
    from vigilancia_multiagente.application.agents.riesgo_agent import RiesgoAgent

    _agent_classes: dict[BranchType, type] = {
        BranchType.AVANCES: AvancesAgent,
        BranchType.COMERCIAL: ComercialAgent,
        BranchType.RIESGO: RiesgoAgent,
        BranchType.PI_NORMATIVA: PiNormativaAgent,
        BranchType.COMPETITIVO: CompetitivoAgent,
        BranchType.OPORTUNIDADES: OportunidadesAgent,
    }
    agents = {}
    for bt, cls in _agent_classes.items():
        agents[bt] = cls(
            g["governance_loader"],
            s["provider_registry"],
            s["execution_client"],
            s["embedding_gateway"],
            s["minimax_client"],
            system_base=g.get("system_base"),
            prompt_composer=g["prompt_composer"],
            tool_router=g["smart_router"],
            event_publisher=e["event_publisher"],
            scholarly_works_gateway=s["scholarly_works_gateway"],
            reranker=s["reranker"],
        )
    return {"agents": agents}


# ── Factory: Orchestration services ─────────────────────────────────────
def _build_orchestration_services(
    s: dict[str, Any], g: dict[str, Any], e: dict[str, Any], agents: dict[str, Any],
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

    # Late import: circular dependency with routes.reports
    from vigilancia_multiagente.api.routes.reports import store_report  # noqa: E402

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


# ── Composition root ────────────────────────────────────────────────────
_s = _build_session_services()
_g = _build_governance_services(_s)
_e = _build_execution_services(_s, _g)
_a = _build_agent_services(_s, _g, _e)
_o = _build_orchestration_services(_s, _g, _e, _a)

# Module-level exports (consumed by routes, tests, etc.)
settings = _s["settings"]
database = _s["database"]
session_repository = _s["session_repository"]
plan_repository = _s["plan_repository"]
branch_result_repository = _s["branch_result_repository"]
report_repository = _s["report_repository"]
vector_index = _s["vector_index"]
embedding_gateway = _s["embedding_gateway"]
llm_client = _s["llm_client"]
minimax_client = _s["minimax_client"]
execution_client = _s["execution_client"]
provider_registry = _s["provider_registry"]
mcp_cache = _s["mcp_cache"]

source_trust_repository = _g["source_trust_repository"]
source_scorer_service = _g["source_scorer_service"]
smart_router = _g["smart_router"]
governance_loader = _g["governance_loader"]
system_base_loader = _g["system_base_loader"]
system_base = _g["system_base"]
prompt_composer = _g["prompt_composer"]

clarification_service = _e["clarification_service"]
plan_builder = _e["plan_builder"]
source_scorer = _e["source_scorer"]
evidence_linker = _e["evidence_linker"]
event_log = _e["event_log"]
event_publisher = _e["event_publisher"]
report_synthesizer = _e["report_synthesizer"]
graph_service = _e["graph_service"]
metrics_service = _e["metrics_service"]
branch_kpi_service = _e["branch_kpi_service"]
prompt_regression_service = _e["prompt_regression_service"]
golden_cases_runner = _e["golden_cases_runner"]
artifact_service = _e["artifact_service"]
conversation_service = _e["conversation_service"]
global_knowledge_repository = _e["global_knowledge_repository"]
cross_session_service = _e["cross_session_service"]
report_generator = _e["report_generator"]

agents = _a["agents"]

ad_hoc_research_tools = _o["ad_hoc_research_tools"]
document_conversion_service = _o["document_conversion_service"]
trend_forecaster = _o["trend_forecaster"]
branch_coordinator = _o["branch_coordinator"]
orchestrator = _o["orchestrator"]
approve_research_usecase = _o["approve_research_usecase"]
graph_snapshot_repository = _o["graph_snapshot_repository"]
