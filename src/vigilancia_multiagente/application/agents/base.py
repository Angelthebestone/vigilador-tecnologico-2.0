from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from vigilancia_multiagente.application.extraction.entity_extractor import extract_from_payloads
from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.application.governance.validators import PromptValidator
from vigilancia_multiagente.application.research.followup_loop import (
    IterationResult,
    run_followup_loop,
)
from vigilancia_multiagente.application.research.semantic_relations import (
    IterationEmbedding,
    SemanticRelation,
    build_relations,
)
from vigilancia_multiagente.application.research.temporal_window import resolve_temporal_window
from vigilancia_multiagente.domain.models import (
    BranchConfig,
    BranchResult,
    BranchType,
    Finding,
    ResearchSession,
    SourceRef,
)
from vigilancia_multiagente.domain.system_base import SystemBase
from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.mcp.execution_client import (
    MCPExecutionClient,
    ToolExecutionResult,
)
from vigilancia_multiagente.infra.mcp.provider_registry import (
    MCPProviderConfig,
    MCPProviderRegistry,
)

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
        provider_registry: MCPProviderRegistry,
        execution_client: MCPExecutionClient,
        embedding_gateway: GeminiEmbeddingGateway,
        minimax_client: MiniMaxClient | None = None,
        system_base: SystemBase | None = None,
        prompt_composer: PromptComposer | None = None,
        signal_callback=None,
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
        self._directive_queue: asyncio.Queue | None = None
        self._preload_context: dict | None = None
        self._signal_callback = signal_callback or self._noop_signal

    def set_preload_context(self, context: dict | None) -> None:
        self._preload_context = context

    async def signal_branch(self, target: BranchType, payload: SignalPayload) -> None:
        """Queue a cross-branch signal for processing by BranchCoordinator."""
        await self._signal_callback(payload)

    async def run(
        self, session: ResearchSession, branch_config: BranchConfig, depth_limit: int
    ) -> AgentRunOutput:
        policy = self._governance_loader.load_skill_matrix()[self.branch_type]
        from vigilancia_multiagente.api.dependencies import smart_router

        smart_order = (
            smart_router.select(branch_config.focus_queries[0])
            if branch_config.focus_queries
            else ()
        )
        tool_order = smart_order or policy.tool_order
        branch_overlay = self._governance_loader.load_branch_overlay(self.branch_type)
        temporal = resolve_temporal_window(self.branch_type)
        seed_query = branch_config.focus_queries[0]
        self._provider_registry.validate_ready(tuple(tool_order))
        provider_names = branch_config.mcp_providers or list(tool_order)
        providers = self._resolve_providers(provider_names, policy)
        if not providers:
            raise RuntimeError(f"No MCP providers configured for {self.branch_type.value}")

        # Compose prompt from system base + branch overlay + user query
        composed = None
        if self._system_base is not None:
            composed = self._prompt_composer.compose(
                system_base=self._system_base,
                overlay=branch_overlay,
                user_query=session.user_query,
                branch_config=branch_config,
                policy=policy,
            )
            self._validator.validate_composition(
                self._system_base, branch_overlay, session.user_query
            )

        executions: list[ToolExecutionResult] = []
        query_payloads: list[dict[str, object]] = []

        async def execute(query: str, index: int) -> tuple[bool, str | None]:
            tool_name = policy.tool_order[min(index - 1, len(policy.tool_order) - 1)]
            provider = self._select_provider(providers, tool_name)
            started = time.perf_counter()
            execution = await self._execution_client.execute_tool(
                provider,
                tool_name,
                {
                    "query": query,
                    "branch_type": self.branch_type.value,
                    "temporal_window": temporal.as_dict(),
                    "prompt_contract_version": branch_overlay.version,
                    "system_base_version": composed.system_base_version if composed else "none",
                    "prompt_composition_id": composed.prompt_composition_id if composed else "",
                    "composed_prompt": composed.full_text if composed else query,
                    "session_id": str(session.id),
                },
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            payload = execution.payload
            payload["latency_ms"] = elapsed_ms
            executions.append(execution)
            query_payloads.append(payload)
            confidence = float(payload.get("confidence", 0.0))
            next_query = payload.get("next_query")
            needs_follow_up = bool(
                payload.get("needs_follow_up", index < depth_limit and confidence < 0.8)
            )
            if needs_follow_up and not isinstance(next_query, str):
                logger.warning("MCP tool %s missing next_query, stopping follow-up", tool_name)
                return False, None
            return needs_follow_up, str(next_query) if needs_follow_up else None

        iterations = await run_followup_loop(
            branch_type=self.branch_type.value,
            seed_query=seed_query,
            depth_limit=depth_limit,
            execute=execute,
        )

        if len(iterations) >= 2:
            embedding_texts = [
                f"{iteration.query}\n{payload.get('title', '')}\n{payload.get('summary') or payload.get('statement') or ''}"
                for iteration, payload in zip(iterations, query_payloads, strict=True)
            ]
            embedding_vectors = await self._embedding_gateway.embed_documents(embedding_texts)
        else:
            embedding_vectors = []
        embeddings = [
            IterationEmbedding(iteration_id=iteration.id, vector=vector)
            for iteration, vector in zip(iterations, embedding_vectors, strict=True)
        ]
        semantic_relations = build_relations(
            embeddings, duplicate_threshold=0.999, support_threshold=0.7
        )

        last_payload = query_payloads[-1]
        last_execution = executions[-1]
        source = SourceRef(
            id=uuid4(),
            session_id=session.id,
            url=self._require_text(last_payload, "url"),
            title=self._optional_text(last_payload, "title")
            or self._optional_text(last_payload, "summary"),
            provider=last_execution.provider,
            branch_type=self.branch_type,
            accessed_at=datetime.now(UTC),
            content_hash=self._optional_text(last_payload, "content_hash"),
        )
        finding = Finding(
            id=uuid4(),
            topic=f"{self.branch_type.value.lower()}-signals",
            statement=self._optional_text(last_payload, "summary")
            or self._optional_text(last_payload, "statement")
            or seed_query,
            confidence=self._optional_float(last_payload, "confidence") or 0.7,
            source_ids=[source.id],
            tags=[branch_overlay.version, temporal.basis],
        )
        entities = extract_from_payloads(query_payloads, self.branch_type, [source.id])
        result = BranchResult(
            id=uuid4(),
            session_id=session.id,
            branch_type=self.branch_type,
            queries_executed=[item.query for item in iterations],
            findings=[finding],
            sources=[source],
            entities=entities,
            started_at=iterations[0].started_at,
            completed_at=iterations[-1].completed_at,
            coverage_score=min(1.0, 0.55 + 0.12 * len(iterations)),
            confidence_score=finding.confidence,
            errors=[],
        )
        provider_usage = [
            {
                "provider": execution.provider,
                "tool": execution.tool_name,
                "latency_ms": int(self._optional_float(payload, "latency_ms") or 0),
                "attempt_count": execution.attempt_count,
                "result_status": execution.result_status,
            }
            for execution, payload in zip(executions, query_payloads, strict=True)
        ]
        return AgentRunOutput(
            branch_result=result,
            iterations=iterations,
            semantic_relations=semantic_relations,
            provider_usage=provider_usage,
        )

    # ── Sandbox MCP tools ─────────────────────────────────────────────────

    async def execute_code(self, code: str, timeout: int = 120) -> dict:
        provider = self._provider_registry.get("sandbox")
        execution = await self._execution_client.execute_tool(
            provider,
            "execute_code",
            {"code": code, "timeout": timeout},
        )
        return execution.payload

    async def list_sandbox_libraries(self) -> dict:
        provider = self._provider_registry.get("sandbox")
        execution = await self._execution_client.execute_tool(
            provider,
            "list_libraries",
            {},
        )
        return execution.payload

    async def visualize_data(self, data: dict, plot_type: str, format: str = "png") -> dict:
        provider = self._provider_registry.get("sandbox")
        execution = await self._execution_client.execute_tool(
            provider,
            "visualize",
            {"data": data, "plot_type": plot_type, "format": format},
        )
        return execution.payload

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
        if self._directive_queue is None:
            self._directive_queue = asyncio.Queue()
        await self._directive_queue.put(directive)

    def _resolve_providers(
        self,
        provider_names: list[str],
        policy,
    ) -> list[MCPProviderConfig]:
        providers: list[MCPProviderConfig] = []
        allowed_tools = set(policy.allowed_tools)
        for provider_name in provider_names:
            provider = self._provider_registry.get(provider_name)
            if any(tool in allowed_tools for tool in provider.enabled_tools):
                providers.append(provider)
        return providers

    def _select_provider(
        self, providers: list[MCPProviderConfig], tool_name: str
    ) -> MCPProviderConfig:
        for provider in providers:
            if tool_name in provider.enabled_tools:
                return provider
        raise RuntimeError(f"No provider exposes tool {tool_name} for {self.branch_type.value}")

    @staticmethod
    def _optional_text(payload: dict[str, object], key: str) -> str | None:
        value = payload.get(key)
        return str(value) if value is not None else None

    @staticmethod
    def _optional_float(payload: dict[str, object], key: str) -> float | None:
        value = payload.get(key)
        return float(value) if value is not None else None

    @staticmethod
    def _require_text(payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if value is None:
            raise RuntimeError(f"Tool response missing required {key}")
        return str(value)

    @staticmethod
    async def _noop_signal(payload):
        pass  # No coordinator available (testing mode)
