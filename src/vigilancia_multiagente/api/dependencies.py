from pathlib import Path

from vigilancia_multiagente.application.agents.avances_agent import AvancesAgent
from vigilancia_multiagente.application.agents.comercial_agent import ComercialAgent
from vigilancia_multiagente.application.agents.competitivo_agent import CompetitivoAgent
from vigilancia_multiagente.application.agents.oportunidades_agent import OportunidadesAgent
from vigilancia_multiagente.application.agents.pi_normativa_agent import PiNormativaAgent
from vigilancia_multiagente.application.agents.riesgo_agent import RiesgoAgent
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
from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer
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
from vigilancia_multiagente.application.orchestration.orchestrator_service import (
    OrchestratorService,
)
from vigilancia_multiagente.application.planning.plan_builder import PlanBuilder
from vigilancia_multiagente.application.reporting.report_generator import ReportGenerator
from vigilancia_multiagente.application.routing.source_scorer import SourceScorerService
from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.system_base import SystemBase
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.mcp.execution_client import MCPExecutionClient
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
from vigilancia_multiagente.infra.persistence.vector_index import PostgresVectorIndex
settings = get_settings()

session_repository = PostgresSessionRepository(database)
plan_repository = PostgresPlanRepository(database)
branch_result_repository = PostgresBranchResultRepository(database)
report_repository = PostgresReportRepository(database)
vector_index = PostgresVectorIndex(database)
embedding_gateway = GeminiEmbeddingGateway()
minimax_client = MiniMaxClient()
execution_client = MCPExecutionClient()
markitdown_execution_client = MCPExecutionClient()
playwright_execution_client = MCPExecutionClient()
provider_registry = MCPProviderRegistry()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
provider_registry.load_manifest(
    PROJECT_ROOT / "src/vigilancia_multiagente/infra/mcp/mcp-providers.json"
)
provider_registry.ensure_standard_providers(settings)
provider_registry.validate_ready(
    (
        "tavily_search",
        "tavily_extract",
        "web_search_exa",
        "web_search_advanced_exa",
        "read_url",
        "guess_datetime_url",
        "brave_web_search",
        "brave_news_search",
        "firecrawl_scrape",
        "search_google_scholar_key_words",
        "search_papers",
        "fetch",
        "execute_code",
        "list_libraries",
        "visualize",
        "convert_to_markdown",
        "browser_navigate",
        "browser_snapshot",
        "browser_screenshot",
        "browser_click",
        "browser_type",
        "browser_select_option",
        "browser_hover",
        "browser_tabs",
        "browser_network_requests",
        "browser_network_request",
        "understand_image",
    )
)

clarification_service = ClarificationService()
plan_builder = PlanBuilder()
# source_trust_repository alimenta el scoring aprendido (cross-session). Se
# crea aquí, antes del linker, para inyectarlo y que EvidenceLinker pueda
# refrescar la reputación de dominio desde la tabla source_trust.
source_trust_repository = SourceTrustRepository(database)
source_scorer = SourceScorer()
evidence_linker = EvidenceLinker(
    source_scorer=source_scorer, trust_repository=source_trust_repository
)
report_synthesizer = ReportSynthesizer()
graph_service = KnowledgeGraphService()
metrics_service = MetricsService()
branch_kpi_service = BranchKPIService()
prompt_regression_service = PromptRegressionService()
golden_cases_runner = GoldenCasesRunner()
artifact_service = SessionArtifactService()

conversation_service = ConversationService()

# Backend Intelligence v3 services
# source_scorer / source_trust_repository ya se crearon arriba (antes del
# evidence_linker) para poder inyectar el scoring aprendido en la fusión.
source_scorer_service = SourceScorerService(repository=source_trust_repository)
mcp_cache = MCPSmartCache()
smart_router = SmartToolRouter(source_scorer=source_scorer_service)
contracts_root = PROJECT_ROOT / "specs/002-vigilancia-multiagente/contracts"
governance_loader = GovernanceContractLoader(contracts_root)
graph_snapshot_repository = PostgresGraphSnapshotRepository(database)

# System Base (Phase 3 rollout — canonical global agent rules)
# Wired at startup; gated by VT_SYSTEM_BASE_ENABLED feature flag.
# When disabled, system_base=None → agents fall back to old PromptContract path.
system_base_loader = SystemBaseLoader(contracts_root)
system_base: SystemBase | None = None
if settings.system_base_enabled:
    try:
        system_base = system_base_loader.load()
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Failed to load system base: %s", exc)

prompt_composer = PromptComposer()

agents = {
    BranchType.AVANCES: AvancesAgent(
        governance_loader,
        provider_registry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base=system_base,
        prompt_composer=prompt_composer,
    ),
    BranchType.COMERCIAL: ComercialAgent(
        governance_loader,
        provider_registry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base=system_base,
        prompt_composer=prompt_composer,
    ),
    BranchType.RIESGO: RiesgoAgent(
        governance_loader,
        provider_registry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base=system_base,
        prompt_composer=prompt_composer,
    ),
    BranchType.PI_NORMATIVA: PiNormativaAgent(
        governance_loader,
        provider_registry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base=system_base,
        prompt_composer=prompt_composer,
    ),
    BranchType.COMPETITIVO: CompetitivoAgent(
        governance_loader,
        provider_registry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base=system_base,
        prompt_composer=prompt_composer,
    ),
    BranchType.OPORTUNIDADES: OportunidadesAgent(
        governance_loader,
        provider_registry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base=system_base,
        prompt_composer=prompt_composer,
    ),
}

global_knowledge_repository = GlobalKnowledgeRepository(database)
cross_session_service = CrossSessionService(global_knowledge_repository, embedding_gateway)

report_generator = ReportGenerator()
branch_coordinator = BranchCoordinator(agents, branch_result_repository)


trend_forecaster = TrendForecasterService()
orchestrator = OrchestratorService(
    session_repository,
    cross_session_service,
    report_generator=report_generator,
    trend_forecaster=trend_forecaster,
    source_scorer=source_scorer_service,
)
event_log: dict[str, list[str]] = {}  # fmt: skip
