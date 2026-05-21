from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from uuid import UUID

from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.application.governance.smart_router import (
    TOOL_QUERY_TYPES,
    SmartToolRouter,
)
from vigilancia_multiagente.application.governance.validators import PromptValidator
from vigilancia_multiagente.application.research.followup_loop import IterationResult
from vigilancia_multiagente.application.research.semantic_relations import SemanticRelation
from vigilancia_multiagente.application.research.temporal_window import resolve_temporal_window
from vigilancia_multiagente.application.routing.tool_selector import ToolSelector
from vigilancia_multiagente.domain.models import (
    BranchConfig,
    BranchResult,
    BranchType,
    ResearchSession,
)
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.provider_registry import ProviderConfig, ProviderRegistry
from vigilancia_multiagente.domain.ports.reranker import Reranker
from vigilancia_multiagente.domain.ports.scholarly_works_gateway import (
    ScholarlyWork,
    ScholarlyWorksGateway,
)
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor
from vigilancia_multiagente.domain.system_base import SystemBase

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SignalPayload:
    source_branch: BranchType
    target_branch: BranchType
    query: str
    source_url: str
    relevance: float  # 0.0-1.0


@dataclass(slots=True)
class AgentRunOutput:
    branch_result: BranchResult
    iterations: list[IterationResult]
    semantic_relations: list[SemanticRelation]
    provider_usage: list[dict[str, str | int]]


class BaseBranchAgent:
    def __init__(
        self,
        branch_type: BranchType,
        governance_loader: GovernanceContractLoader,
        provider_registry: ProviderRegistry,
        execution_client: ToolExecutor,
        embedding_gateway: EmbeddingGateway,
        minimax_client: LLMClient | None = None,
        system_base: SystemBase | None = None,
        prompt_composer: PromptComposer | None = None,
        signal_callback=None,
        tool_router: SmartToolRouter | None = None,
        event_publisher: EventPublisher | None = None,
        scholarly_works_gateway: ScholarlyWorksGateway | None = None,
        reranker: Reranker | None = None,
        # Spec 007 — pipeline steps opcionales (WS-A/B/C/D)
        source_quality_step: object | None = None,
        data_intelligence_step: object | None = None,
        deep_analysis_step: object | None = None,
        strategic_signals_step: object | None = None,
    ) -> None:
        self.branch_type = branch_type
        self._governance_loader = governance_loader
        self._provider_registry = provider_registry
        self._execution_client = execution_client
        self._embedding_gateway = embedding_gateway
        self._minimax_client = minimax_client
        self._system_base = system_base
        self._prompt_composer = prompt_composer or PromptComposer()
        self._validator = PromptValidator()
        self._directive_queue: asyncio.Queue = asyncio.Queue()
        self._preload_context: dict | None = None
        self._signal_callback = signal_callback or self._noop_signal
        self._tool_router = tool_router
        self._event_publisher = event_publisher
        self._scholarly_works_gateway = scholarly_works_gateway
        self._reranker = reranker
        self._cross_branch_hints: deque[str] = deque(maxlen=32)
        # Spec 007 — steps opcionales del pipeline de evaluacion
        self._source_quality_step = source_quality_step
        self._data_intelligence_step = data_intelligence_step
        self._deep_analysis_step = deep_analysis_step
        self._strategic_signals_step = strategic_signals_step

    def set_preload_context(self, context: dict | None) -> None:
        self._preload_context = context

    def reset_session_state(self, session_id: UUID) -> None:
        """Clear per-session mutable agent state."""
        self._preload_context = None
        while not self._directive_queue.empty():
            try:
                self._directive_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        _ = session_id  # reserved for future session-keyed caches

    async def signal_branch(self, target: BranchType, payload: SignalPayload) -> None:
        """Queue a cross-branch signal for processing by BranchCoordinator."""
        await self._signal_callback(payload)

    def _build_pipeline(self):
        from vigilancia_multiagente.application.agents.pipeline import (
            AssembleBranchResultStep,
            ComposePromptStep,
            Pipeline,
            SandboxExecutionStep,
            ToolLoopStep,
        )

        steps: list = [
            ComposePromptStep(
                prompt_composer=self._prompt_composer,
                system_base=self._system_base,
                validator=self._validator,
                cross_branch_hints=self._cross_branch_hints,
            ),
            SandboxExecutionStep(),
            ToolLoopStep(
                execution_client=self._execution_client,
                embedding_gateway=self._embedding_gateway,
                event_publisher=self._event_publisher,
                cross_branch_hints=self._cross_branch_hints,
                branch_type=self.branch_type,
                reranker=self._reranker,
                # Spec 007 T078: data_intelligence_step opcional (WS-B)
                data_intelligence_step=self._data_intelligence_step,
            ),
        ]

        # Spec 007 T058: SourceQualityStep (WS-A) antes de AssembleBranchResultStep
        if self._source_quality_step is not None:
            steps.append(self._source_quality_step)  # type: ignore[arg-type]

        steps.append(
            AssembleBranchResultStep(
                embedding_gateway=self._embedding_gateway,
                branch_type=self.branch_type,
            ),
        )

        # Spec 007 T100: DeepAnalysisStep (WS-C) post-AssembleBranchResultStep
        if self._deep_analysis_step is not None:
            steps.append(self._deep_analysis_step)  # type: ignore[arg-type]

        # Spec 007 T121: StrategicSignalsStep (WS-D) post-DeepAnalysisStep
        if self._strategic_signals_step is not None:
            steps.append(self._strategic_signals_step)  # type: ignore[arg-type]

        return Pipeline(steps)  # type: ignore[arg-type]

    async def run(
        self, session: ResearchSession, branch_config: BranchConfig, depth_limit: int
    ) -> AgentRunOutput:
        from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import (
            ToolLoopContext,
        )

        policy = self._governance_loader.load_skill_matrix()[self.branch_type]
        router = self._tool_router
        seed = branch_config.focus_queries[0] if branch_config.focus_queries else ""
        smart_order = router.select(seed) if seed and router is not None else ()
        # El conjunto disponible: lo que el router sugiere para esta query, o
        # la policy de la rama. Ya no es un guion posicional — ToolSelector
        # elige dentro de él por señal en cada iteración.
        available_tools = tuple(smart_order or policy.tool_order)
        query_type = router.classify(seed) if seed and router is not None else "general"
        tool_selector = ToolSelector(available_tools, TOOL_QUERY_TYPES)
        branch_overlay = self._governance_loader.load_branch_overlay(self.branch_type)
        temporal = resolve_temporal_window(self.branch_type)
        seed_query = branch_config.focus_queries[0]
        self._provider_registry.validate_ready(available_tools)
        provider_names = branch_config.mcp_providers or list(available_tools)
        providers = self._resolve_providers(provider_names, policy)
        if not providers:
            raise RuntimeError(f"No MCP providers configured for {self.branch_type.value}")

        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=branch_overlay,
            depth_limit=depth_limit,
        )
        ctx.tool_selector = tool_selector
        ctx.query_type = query_type
        ctx.temporal = temporal
        ctx.seed_query = seed_query
        ctx.providers = providers
        return await self._build_pipeline().run(ctx)

    # ── Sandbox MCP tools ─────────────────────────────────────────────────

    async def execute_code(self, code: str, timeout: int = 120) -> dict:
        from vigilancia_multiagente.application.agents import sandbox_tools

        return await sandbox_tools.execute_code(
            self._execution_client, self._provider_registry, code, timeout
        )

    async def list_sandbox_libraries(self) -> dict:
        from vigilancia_multiagente.application.agents import sandbox_tools

        return await sandbox_tools.list_sandbox_libraries(
            self._execution_client, self._provider_registry
        )

    async def visualize_data(self, data: dict, plot_type: str, format: str = "png") -> dict:
        from vigilancia_multiagente.application.agents import sandbox_tools

        return await sandbox_tools.visualize_data(
            self._execution_client, self._provider_registry, data, plot_type, format
        )

    # ── Datos estructurados (OpenAlex) ────────────────────────────────────

    async def fetch_scholarly_works(
        self, query: str, limit: int = 10
    ) -> list[ScholarlyWork]:
        """Datos bibliométricos duros (citas, instituciones, año).

        Si no se inyectó un :class:`ScholarlyWorksGateway`, devuelve [] —
        la rama no debe romperse cuando no hay datos bibliométricos.
        """
        if self._scholarly_works_gateway is None:
            return []
        return await self._scholarly_works_gateway.search(query, limit=limit)

    # ── Signals ───────────────────────────────────────────────────────────

    async def signal_gap_detected(self, description: str, data: dict | None = None) -> None:
        payload = SignalPayload(
            source_branch=self.branch_type,
            target_branch=self.branch_type,
            query=description,
            source_url="",
            relevance=0.8,
        )
        await self._signal_callback(payload)

    async def receive_directive(self, directive: dict) -> None:
        await self._directive_queue.put(directive)
        hint = directive.get("query") or directive.get("focus")
        if isinstance(hint, str) and hint:
            self._cross_branch_hints.append(hint)

    def _resolve_providers(
        self,
        provider_names: list[str],
        policy,
    ) -> list[ProviderConfig]:
        providers: list[ProviderConfig] = []
        allowed_tools = set(policy.allowed_tools)
        for provider_name in provider_names:
            provider = self._provider_registry.get(provider_name)
            if any(tool in allowed_tools for tool in provider.enabled_tools):
                providers.append(provider)
        return providers

    @staticmethod
    async def _noop_signal(payload):
        pass  # No coordinator available (testing mode)
