"""Real unit tests for pipeline steps using fakes.

Cada step se prueba con dependencias fake, sin base de datos real
ni API keys.  Sigue el patron de tests/conftest.py.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from vigilancia_multiagente.application.agents.base import AgentRunOutput
from vigilancia_multiagente.application.agents.pipeline.assemble_branch_result_step import (
    AssembleBranchResultStep,
)
from vigilancia_multiagente.application.agents.pipeline.compose_prompt_step import (
    ComposePromptContext,
    ComposePromptStep,
)
from vigilancia_multiagente.application.agents.pipeline.pipeline import Pipeline
from vigilancia_multiagente.application.agents.pipeline.sandbox_execution_step import (
    SandboxExecutionStep,
)
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import (
    ToolLoopContext,
    ToolLoopStep,
)
from vigilancia_multiagente.application.governance.contract_loader import AgentSkillPolicy
from vigilancia_multiagente.application.governance.prompt_composer import (
    ComposedPrompt,
)
from vigilancia_multiagente.application.research.followup_loop import IterationResult
from vigilancia_multiagente.application.research.temporal_window import TemporalWindow
from vigilancia_multiagente.application.routing.tool_selector import ToolSelector
from vigilancia_multiagente.domain.models import (
    BranchConfig,
    BranchResult,
    BranchType,
    ResearchSession,
)
from vigilancia_multiagente.domain.ports.provider_registry import ProviderConfig
from vigilancia_multiagente.domain.session_state import SessionStatus
from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase
from vigilancia_multiagente.shared.mcp_dto import ToolExecutionResult

# ═══════════════════════════════════════════════════════════════════════════════
# Fakes
# ═══════════════════════════════════════════════════════════════════════════════


class FakeToolExecutor:
    """Simula ToolExecutor sin llamadas reales a MCP.

    Retorna un resultado deterministico con confidence > 0.8 para que
    needs_follow_up=False en la primera iteracion.
    """

    def __init__(self) -> None:
        self.call_count = 0
        self.last_arguments: dict | None = None
        self.last_provider: str | None = None
        self.last_tool: str | None = None

    async def execute_tool(
        self,
        provider: ProviderConfig,
        tool_name: str,
        arguments: dict,
    ) -> ToolExecutionResult:
        self.call_count += 1
        self.last_provider = provider.name
        self.last_tool = tool_name
        self.last_arguments = arguments
        return ToolExecutionResult(
            provider=provider.name,
            tool_name=tool_name,
            payload={
                "url": "https://example.com/result",
                "title": "Test Result Title",
                "summary": "Test summary for pipeline step",
                "confidence": 0.85,
                "content_hash": "abc123",
            },
            attempt_count=1,
        )


class FakeProviderConfig:
    """Implementacion minima de ProviderConfig (protocolo)."""

    def __init__(self, name: str, enabled_tools: tuple[str, ...]) -> None:
        self.name = name
        self.enabled_tools = enabled_tools


class FakePromptComposer:
    """Composicion deterministica, sin templates reales."""

    def compose(
        self,
        system_base: SystemBase,
        overlay: BranchOverlay,
        user_query: str,
        branch_config: BranchConfig | None = None,
        policy: AgentSkillPolicy | None = None,
        cross_branch_context: list[str] | None = None,
    ) -> ComposedPrompt:
        return ComposedPrompt(
            system_base_version=system_base.version,
            branch_type=overlay.branch_type,
            user_query=user_query,
            sections={"global_rules": "test"},
            full_text=(
                f"# System Base v{system_base.version}\n\n{overlay.objective}\n\n{user_query}"
            ),
            prompt_composition_id="test-composition-id",
        )


class FakePromptValidator:
    """Validacion que nunca falla."""

    def validate_overlay(self, system_base: SystemBase, overlay: BranchOverlay) -> None:
        pass

    def validate_composition(
        self,
        system_base: SystemBase,
        overlay: BranchOverlay,
        user_query: str,
    ) -> None:
        pass


class FakePromptValidatorStrict(FakePromptValidator):
    """Validador que SIEMPRE falla en validate_composition para probar errores."""

    def validate_composition(
        self,
        system_base: SystemBase,
        overlay: BranchOverlay,
        user_query: str,
    ) -> None:
        from vigilancia_multiagente.application.governance.validators import (
            PromptValidationError,
        )

        raise PromptValidationError("Simulated validation failure")


class FakeEmbeddingGateway:
    """Embeddings deterministicos (misma dimension, valores fijos)."""

    async def embed(self, text: str, task_type: object = None) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def embed_document(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeEventPublisher:
    """Publisher no-op para tests."""

    async def publish(self, session_id: UUID, sse_message: str) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures compartidos
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def session() -> ResearchSession:
    return ResearchSession(
        id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        status=SessionStatus.DRAFT,
        user_query="test query about AI trends",
    )


@pytest.fixture
def branch_config() -> BranchConfig:
    return BranchConfig(
        branch_type=BranchType.AVANCES,
        focus_queries=["AI trends 2026"],
        mcp_providers=["test_provider"],
    )


@pytest.fixture
def policy() -> AgentSkillPolicy:
    return AgentSkillPolicy(
        branch_type=BranchType.AVANCES,
        allowed_tools=("tavily_search",),
        tool_order=("tavily_search",),
        timeout_ms_per_tool={"tavily_search": 20000},
        retry_limit_per_tool={"tavily_search": 2},
    )


@pytest.fixture
def overlay() -> BranchOverlay:
    return BranchOverlay(
        branch_type=BranchType.AVANCES,
        objective="Identify technological advances in AI",
        do_rules=("cite sources", "declare uncertainty"),
        dont_rules=("invent data",),
        version="1.0.0",
    )


@pytest.fixture
def system_base() -> SystemBase:
    return SystemBase(
        version="1.0.0",
        global_rules=("Cite sources", "Declare uncertainty"),
        safety_limits={"max_iterations": 10},
    )


@pytest.fixture
def temporal() -> TemporalWindow:
    return TemporalWindow(start_year=2021, end_year=2026, basis="test")


@pytest.fixture
def tool_selector() -> ToolSelector:
    return ToolSelector(
        available_tools=("tavily_search",),
        tool_query_types={"tavily_search": "general"},
    )


@pytest.fixture
def provider_cfg() -> FakeProviderConfig:
    return FakeProviderConfig("test_provider", ("tavily_search",))


@pytest.fixture
def fake_executor() -> FakeToolExecutor:
    return FakeToolExecutor()


@pytest.fixture
def composed() -> ComposedPrompt:
    return ComposedPrompt(
        system_base_version="1.0.0",
        branch_type=BranchType.AVANCES,
        user_query="test query",
        sections={"global_rules": "test"},
        full_text="test composed prompt",
        prompt_composition_id="test-id",
    )


@pytest.fixture
def iteration_result() -> IterationResult:
    now = datetime.now(UTC)
    return IterationResult(
        id=uuid4(),
        branch_type="AVANCES",
        iteration_index=1,
        query="AI trends 2026",
        query_type="SEED",
        needs_follow_up=False,
        next_query=None,
        stop_reason="NO_FOLLOW_UP",
        started_at=now,
        completed_at=now,
    )


@pytest.fixture
def execution_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        provider="test_provider",
        tool_name="tavily_search",
        payload={
            "url": "https://example.com/result",
            "title": "Test Title",
            "summary": "Test analysis result",
            "confidence": 0.85,
            "content_hash": "hash123",
        },
        attempt_count=1,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SandboxExecutionStep
# ═══════════════════════════════════════════════════════════════════════════════


class TestSandboxExecutionStep:
    """SandboxExecutionStep es un passthrough no-op."""

    @pytest.mark.asyncio
    async def test_passthrough_with_dummy_context(self) -> None:
        """Debe devolver el mismo objeto sin modificaciones."""
        step = SandboxExecutionStep()

        class DummyCtx:
            value = 1

        ctx = DummyCtx()
        out = await step.execute(ctx)
        assert out is ctx
        assert out.value == 1

    @pytest.mark.asyncio
    async def test_passthrough_with_tool_loop_context(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
    ) -> None:
        """Idempotente incluso con ToolLoopContext real."""
        step = SandboxExecutionStep()
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
            depth_limit=3,
        )
        out = await step.execute(ctx)
        assert out is ctx
        assert out.session is session
        assert out.branch_config is branch_config
        assert out.depth_limit == 3


# ═══════════════════════════════════════════════════════════════════════════════
# ComposePromptStep
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposePromptStep:
    """ComposePromptStep compone el prompt cuando hay system_base."""

    @pytest.mark.asyncio
    async def test_skip_composition_when_system_base_is_none(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
    ) -> None:
        """Sin system_base → no compone, y context.composed sigue siendo None."""
        step = ComposePromptStep(
            prompt_composer=FakePromptComposer(),
            system_base=None,
            validator=FakePromptValidator(),
            cross_branch_hints=deque(),
        )
        ctx = ComposePromptContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        result = await step.execute(ctx)
        assert result is ctx  # mismo objeto, no reemplazado
        assert result.composed is None  # no se compuso nada

    @pytest.mark.asyncio
    async def test_compose_prompt_when_system_base_is_set(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        system_base: SystemBase,
    ) -> None:
        """Con system_base → compone y deja composed != None."""
        step = ComposePromptStep(
            prompt_composer=FakePromptComposer(),
            system_base=system_base,
            validator=FakePromptValidator(),
            cross_branch_hints=deque(),
        )
        ctx = ComposePromptContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        result = await step.execute(ctx)
        assert result is ctx
        assert result.composed is not None
        assert isinstance(result.composed, ComposedPrompt)
        assert result.composed.system_base_version == "1.0.0"
        assert result.composed.branch_type == BranchType.AVANCES
        assert result.composed.user_query == "test query about AI trends"

    @pytest.mark.asyncio
    async def test_compose_passes_cross_branch_hints(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        system_base: SystemBase,
    ) -> None:
        """Cross-branch hints se pasan al composer."""
        hints = deque(["other branch found X", "another hint Y"], maxlen=32)
        step = ComposePromptStep(
            prompt_composer=FakePromptComposer(),
            system_base=system_base,
            validator=FakePromptValidator(),
            cross_branch_hints=hints,
        )
        ctx = ComposePromptContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        result = await step.execute(ctx)
        assert result.composed is not None
        # El FakePromptComposer ignora hints, pero el step no falla
        assert isinstance(result.composed, ComposedPrompt)

    @pytest.mark.asyncio
    async def test_validation_failure_bubbles_up(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        system_base: SystemBase,
    ) -> None:
        """Si el validador lanza, el step propaga la excepcion."""
        from vigilancia_multiagente.application.governance.validators import (
            PromptValidationError,
        )

        step = ComposePromptStep(
            prompt_composer=FakePromptComposer(),
            system_base=system_base,
            validator=FakePromptValidatorStrict(),
            cross_branch_hints=deque(),
        )
        ctx = ComposePromptContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        with pytest.raises(PromptValidationError, match="Simulated validation failure"):
            await step.execute(ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# AssembleBranchResultStep
# ═══════════════════════════════════════════════════════════════════════════════


class TestAssembleBranchResultStep:
    """Ensambla BranchResult + AgentRunOutput a partir de ToolLoopContext."""

    @pytest.mark.asyncio
    async def test_assemble_basic_output(
        self,
        session: ResearchSession,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        iteration_result: IterationResult,
        execution_result: ToolExecutionResult,
    ) -> None:
        """Debe producir AgentRunOutput con branch_result, iterations, etc."""
        step = AssembleBranchResultStep(
            embedding_gateway=FakeEmbeddingGateway(),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=BranchConfig(
                branch_type=BranchType.AVANCES,
                focus_queries=["AI trends 2026"],
                mcp_providers=["test_provider"],
            ),
            policy=AgentSkillPolicy(
                branch_type=BranchType.AVANCES,
                allowed_tools=("tavily_search",),
                tool_order=("tavily_search",),
                timeout_ms_per_tool={"tavily_search": 20000},
                retry_limit_per_tool={"tavily_search": 2},
            ),
            branch_overlay=overlay,
        )
        ctx.iterations = [iteration_result]
        ctx.executions = [execution_result]
        ctx.query_payloads = [execution_result.payload]
        ctx.semantic_relations = []
        ctx.seed_query = "AI trends 2026"
        ctx.temporal = temporal

        output = await step.execute(ctx)

        assert isinstance(output, AgentRunOutput)
        assert isinstance(output.branch_result, BranchResult)
        assert output.branch_result.branch_type == BranchType.AVANCES
        assert output.branch_result.session_id == session.id
        assert len(output.branch_result.queries_executed) == 1
        assert output.branch_result.queries_executed[0] == "AI trends 2026"

        assert len(output.iterations) == 1
        assert output.iterations[0] is iteration_result

        assert isinstance(output.semantic_relations, list)

        assert len(output.provider_usage) == 1
        assert output.provider_usage[0]["provider"] == "test_provider"
        assert output.provider_usage[0]["tool"] == "tavily_search"

    @pytest.mark.asyncio
    async def test_assemble_fails_without_temporal(
        self,
        session: ResearchSession,
        overlay: BranchOverlay,
        iteration_result: IterationResult,
        execution_result: ToolExecutionResult,
    ) -> None:
        """Si temporal es None, el step lanza RuntimeError."""
        step = AssembleBranchResultStep(
            embedding_gateway=FakeEmbeddingGateway(),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=BranchConfig(
                branch_type=BranchType.AVANCES,
                focus_queries=["AI trends 2026"],
                mcp_providers=["test_provider"],
            ),
            policy=AgentSkillPolicy(
                branch_type=BranchType.AVANCES,
                allowed_tools=("tavily_search",),
                tool_order=("tavily_search",),
                timeout_ms_per_tool={"tavily_search": 20000},
                retry_limit_per_tool={"tavily_search": 2},
            ),
            branch_overlay=overlay,
        )
        ctx.iterations = [iteration_result]
        ctx.executions = [execution_result]
        ctx.query_payloads = [execution_result.payload]
        ctx.semantic_relations = []
        ctx.seed_query = "AI trends 2026"
        ctx.temporal = None

        with pytest.raises(RuntimeError, match="temporal window not configured"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_assemble_fails_without_payloads(
        self,
        session: ResearchSession,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        iteration_result: IterationResult,
    ) -> None:
        """Sin query_payloads, al acceder a query_payloads[-1] lanza IndexError."""
        step = AssembleBranchResultStep(
            embedding_gateway=FakeEmbeddingGateway(),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=BranchConfig(
                branch_type=BranchType.AVANCES,
                focus_queries=["AI trends 2026"],
                mcp_providers=["test_provider"],
            ),
            policy=AgentSkillPolicy(
                branch_type=BranchType.AVANCES,
                allowed_tools=("tavily_search",),
                tool_order=("tavily_search",),
                timeout_ms_per_tool={"tavily_search": 20000},
                retry_limit_per_tool={"tavily_search": 2},
            ),
            branch_overlay=overlay,
        )
        ctx.iterations = [iteration_result]
        ctx.executions = []
        ctx.query_payloads = []
        ctx.semantic_relations = []
        ctx.seed_query = "AI trends 2026"
        ctx.temporal = temporal

        with pytest.raises(IndexError):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_assemble_fails_without_url_in_payload(
        self,
        session: ResearchSession,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        iteration_result: IterationResult,
    ) -> None:
        """Payload sin 'url' → RuntimeError por _require_text."""
        step = AssembleBranchResultStep(
            embedding_gateway=FakeEmbeddingGateway(),
            branch_type=BranchType.AVANCES,
        )
        bad_payload: dict = {  # type: ignore[typeddict-item]
            "title": "No URL here",
            "summary": "missing url field",
        }
        execution = ToolExecutionResult(
            provider="test_provider",
            tool_name="tavily_search",
            payload=bad_payload,
            attempt_count=1,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=BranchConfig(
                branch_type=BranchType.AVANCES,
                focus_queries=["AI trends 2026"],
                mcp_providers=["test_provider"],
            ),
            policy=AgentSkillPolicy(
                branch_type=BranchType.AVANCES,
                allowed_tools=("tavily_search",),
                tool_order=("tavily_search",),
                timeout_ms_per_tool={"tavily_search": 20000},
                retry_limit_per_tool={"tavily_search": 2},
            ),
            branch_overlay=overlay,
        )
        ctx.iterations = [iteration_result]
        ctx.executions = [execution]
        ctx.query_payloads = [bad_payload]
        ctx.semantic_relations = []
        ctx.seed_query = "AI trends 2026"
        ctx.temporal = temporal

        with pytest.raises(RuntimeError, match="missing required url"):
            await step.execute(ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipeline:
    """Pipeline ejecuta steps en orden."""

    def test_accepts_empty_steps(self) -> None:
        """Pipeline vacio no rompe."""
        pipeline = Pipeline([])
        assert pipeline._steps == []

    @pytest.mark.asyncio
    async def test_pipeline_runs_single_step(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
    ) -> None:
        """Un solo step se ejecuta y devuelve el contexto."""
        step = SandboxExecutionStep()
        pipeline = Pipeline([step])  # type: ignore[arg-type]
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        result = await pipeline.run(ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_pipeline_runs_multiple_steps(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
    ) -> None:
        """Pipeline con ComposePromptStep + SandboxExecutionStep."""
        compose_step = ComposePromptStep(
            prompt_composer=FakePromptComposer(),
            system_base=SystemBase(
                version="1.0.0",
                global_rules=("Cite sources",),
                safety_limits={"max_iterations": 10},
            ),
            validator=FakePromptValidator(),
            cross_branch_hints=deque(),
        )
        sandbox_step = SandboxExecutionStep()
        pipeline = Pipeline([compose_step, sandbox_step])  # type: ignore[arg-type]
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        result = await pipeline.run(ctx)
        # El compose_step modifico el context (composed != None), sandbox paso
        # a traves sin cambios
        assert result is ctx
        assert ctx.composed is not None
        assert isinstance(ctx.composed, ComposedPrompt)


# ═══════════════════════════════════════════════════════════════════════════════
# ToolLoopStep
# ═══════════════════════════════════════════════════════════════════════════════


class TestToolLoopStep:
    """ToolLoopStep ejecuta el bucle de herramientas con ToolLoopContext."""

    @pytest.mark.asyncio
    async def test_basic_execution(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        tool_selector: ToolSelector,
        provider_cfg: FakeProviderConfig,
    ) -> None:
        """Ejecucion basica: 1 iteracion, sin errores.

        Con depth_limit=1 y confidence=0.85 se ejecuta exactamente una
        llamada a execute_tool y el loop termina por NO_FOLLOW_UP.
        """
        executor = FakeToolExecutor()
        embedding = FakeEmbeddingGateway()
        publisher = FakeEventPublisher()

        step = ToolLoopStep(
            execution_client=executor,
            embedding_gateway=embedding,
            event_publisher=publisher,
            cross_branch_hints=deque(maxlen=32),
            branch_type=BranchType.AVANCES,
        )

        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
            depth_limit=1,
        )
        ctx.tool_selector = tool_selector
        ctx.query_type = "general"
        ctx.temporal = temporal
        ctx.seed_query = "AI trends 2026"
        ctx.providers = [provider_cfg]

        result = await step.execute(ctx)
        assert result is ctx  # mismo contexto, modificado in-place

        # Verificar que se ejecuto exactamente 1 tool
        assert executor.call_count == 1
        assert executor.last_tool == "tavily_search"

        # Verificar que se poblaron las listas del contexto
        assert len(ctx.iterations) == 1
        assert len(ctx.executions) == 1
        assert len(ctx.query_payloads) == 1

        it = ctx.iterations[0]
        assert it.iteration_index == 1
        assert it.query == "AI trends 2026"
        assert it.stop_reason == "NO_FOLLOW_UP"

        ex = ctx.executions[0]
        assert ex.provider == "test_provider"
        assert ex.tool_name == "tavily_search"

        # semantic_relations: con 1 iteracion no hay pares que comparar
        assert len(ctx.semantic_relations) == 0

    @pytest.mark.asyncio
    async def test_fails_without_tool_selector(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        provider_cfg: FakeProviderConfig,
    ) -> None:
        """Sin tool_selector → RuntimeError."""
        step = ToolLoopStep(
            execution_client=FakeToolExecutor(),
            embedding_gateway=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            cross_branch_hints=deque(maxlen=32),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        ctx.query_type = "general"
        ctx.temporal = temporal
        ctx.seed_query = "AI trends 2026"
        ctx.providers = [provider_cfg]
        # tool_selector NO se asigna → None

        with pytest.raises(RuntimeError, match="tool_selector not configured"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_fails_without_temporal(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        tool_selector: ToolSelector,
        provider_cfg: FakeProviderConfig,
    ) -> None:
        """Sin temporal → RuntimeError."""
        step = ToolLoopStep(
            execution_client=FakeToolExecutor(),
            embedding_gateway=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            cross_branch_hints=deque(maxlen=32),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        ctx.tool_selector = tool_selector
        ctx.query_type = "general"
        # temporal NO se asigna → None
        ctx.seed_query = "AI trends 2026"
        ctx.providers = [provider_cfg]

        with pytest.raises(RuntimeError, match="temporal window not configured"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_fails_without_provider_for_tool(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        tool_selector: ToolSelector,
    ) -> None:
        """Ningun provider expone la tool seleccionada → RuntimeError."""
        step = ToolLoopStep(
            execution_client=FakeToolExecutor(),
            embedding_gateway=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            cross_branch_hints=deque(maxlen=32),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
        )
        ctx.tool_selector = tool_selector
        ctx.query_type = "general"
        ctx.temporal = temporal
        ctx.seed_query = "AI trends 2026"
        # provider que NO tiene tavily_search habilitada
        ctx.providers = [
            FakeProviderConfig("other_provider", ("some_other_tool",)),
        ]

        with pytest.raises(RuntimeError, match="No provider exposes tool"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_multiple_iterations_when_needs_follow_up(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        provider_cfg: FakeProviderConfig,
    ) -> None:
        """Si el payload pide follow-up, el loop continua.

        Configuramos el FakeToolExecutor para que devuelva un payload
        con needs_follow_up=True y next_query, forzando una 2a iteracion.
        depth_limit=2 permite 2 iteraciones.
        """

        class FakeToolExecutorFollowUp(FakeToolExecutor):
            """Retorna needs_follow_up=True en la 1ra iteracion."""

            def __init__(self) -> None:
                super().__init__()
                self._first = True

            async def execute_tool(
                self,
                provider: ProviderConfig,
                tool_name: str,
                arguments: dict,
            ) -> ToolExecutionResult:
                self.call_count += 1
                self.last_provider = provider.name
                self.last_tool = tool_name
                self.last_arguments = arguments

                if self._first:
                    self._first = False
                    payload: dict = {
                        "url": "https://example.com/first",
                        "title": "First Result",
                        "summary": "First iteration finding",
                        "confidence": 0.65,
                        "needs_follow_up": True,
                        "next_query": "What about second iteration?",
                    }
                else:
                    payload = {
                        "url": "https://example.com/second",
                        "title": "Second Result",
                        "summary": "Second iteration finding",
                        "confidence": 0.90,
                        "needs_follow_up": False,
                    }

                return ToolExecutionResult(
                    provider=provider.name,
                    tool_name=tool_name,
                    payload=payload,
                    attempt_count=1,
                )

        executor = FakeToolExecutorFollowUp()
        tool_sel = ToolSelector(
            available_tools=("tavily_search",),
            tool_query_types={"tavily_search": "general"},
        )

        step = ToolLoopStep(
            execution_client=executor,
            embedding_gateway=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            cross_branch_hints=deque(maxlen=32),
            branch_type=BranchType.AVANCES,
        )

        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
            depth_limit=2,
        )
        ctx.tool_selector = tool_sel
        ctx.query_type = "general"
        ctx.temporal = temporal
        ctx.seed_query = "AI trends 2026"
        ctx.providers = [provider_cfg]

        result = await step.execute(ctx)
        assert result is ctx

        # Deberian haber 2 iteraciones
        assert executor.call_count == 2
        assert len(ctx.iterations) == 2
        assert len(ctx.executions) == 2

        # Primera iteracion: NO_FOLLOW_UP no, porque necesita follow-up
        it1 = ctx.iterations[0]
        assert it1.iteration_index == 1
        assert it1.needs_follow_up is True

        # Segunda iteracion: NO_FOLLOW_UP
        it2 = ctx.iterations[1]
        assert it2.iteration_index == 2
        assert it2.needs_follow_up is False or it2.stop_reason == "DEPTH_LIMIT"

        # Con 2 iteraciones deberia haber semantic_relations
        assert len(ctx.semantic_relations) > 0

    @pytest.mark.asyncio
    async def test_execution_uses_composed_prompt_when_available(
        self,
        session: ResearchSession,
        branch_config: BranchConfig,
        policy: AgentSkillPolicy,
        overlay: BranchOverlay,
        temporal: TemporalWindow,
        tool_selector: ToolSelector,
        provider_cfg: FakeProviderConfig,
        composed: ComposedPrompt,
    ) -> None:
        """Cuando context.composed existe, se pasa al execute_tool."""
        executor = FakeToolExecutor()
        step = ToolLoopStep(
            execution_client=executor,
            embedding_gateway=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            cross_branch_hints=deque(maxlen=32),
            branch_type=BranchType.AVANCES,
        )
        ctx = ToolLoopContext(
            session=session,
            branch_config=branch_config,
            policy=policy,
            branch_overlay=overlay,
            depth_limit=1,
            composed=composed,
        )
        ctx.tool_selector = tool_selector
        ctx.query_type = "general"
        ctx.temporal = temporal
        ctx.seed_query = "AI trends 2026"
        ctx.providers = [provider_cfg]

        await step.execute(ctx)

        assert executor.last_arguments is not None
        args = executor.last_arguments
        assert args["composed_prompt"] == composed.full_text
        assert args["prompt_contract_version"] == "1.0.0"
        assert args["system_base_version"] == "1.0.0"
        assert args["prompt_composition_id"] == "test-id"
