from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from vigilancia_multiagente.application.extraction.entity_extractor import extract_from_payloads
from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.application.governance.smart_router import TOOL_QUERY_TYPES
from vigilancia_multiagente.application.governance.validators import PromptValidator
from vigilancia_multiagente.application.research.followup_loop import (
    IterationResult,
    run_followup_loop,
)
from vigilancia_multiagente.application.research.followup_strategist import (
    FollowupStrategist,
    StrategistContext,
)
from vigilancia_multiagente.application.research.saturation import SaturationTracker
from vigilancia_multiagente.application.research.semantic_relations import (
    IterationEmbedding,
    SemanticRelation,
    build_relations,
)
from vigilancia_multiagente.application.research.temporal_window import resolve_temporal_window
from vigilancia_multiagente.application.routing.tool_selector import (
    SelectionContext,
    ToolSelector,
)
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
        self._cross_branch_hints: deque[str] = deque(maxlen=32)
        self._reranker: Any = None

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

        seed = branch_config.focus_queries[0] if branch_config.focus_queries else ""
        smart_order = smart_router.select(seed) if seed else ()
        # El conjunto disponible: lo que el router sugiere para esta query, o
        # la policy de la rama. Ya no es un guion posicional — ToolSelector
        # elige dentro de él por señal en cada iteración.
        available_tools = tuple(smart_order or policy.tool_order)
        query_type = smart_router.classify(seed) if seed else "general"
        tool_selector = ToolSelector(available_tools, TOOL_QUERY_TYPES)
        branch_overlay = self._governance_loader.load_branch_overlay(self.branch_type)
        temporal = resolve_temporal_window(self.branch_type)
        seed_query = branch_config.focus_queries[0]
        self._provider_registry.validate_ready(available_tools)
        provider_names = branch_config.mcp_providers or list(available_tools)
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
                cross_branch_context=list(self._cross_branch_hints) or None,
            )
            self._validator.validate_composition(
                self._system_base, branch_overlay, session.user_query
            )

        executions: list[ToolExecutionResult] = []
        query_payloads: list[dict[str, object]] = []
        strategist = FollowupStrategist()
        explored_terms: set[str] = {seed_query}
        # Estado de selección entre iteraciones: la tool previa habilita la
        # cadena forzada (MiniMax+PDF) y evita repeticiones; la sugerencia
        # viene del next_query del payload anterior.
        last_tool: str | None = None
        suggested_tool: str | None = None

        async def execute(query: str, index: int) -> tuple[bool, str | None]:
            nonlocal last_tool, suggested_tool
            tool_name = tool_selector.select(
                SelectionContext(
                    iteration_index=index,
                    query_type=query_type,
                    last_tool=last_tool,
                    suggested_tool=suggested_tool,
                )
            )
            last_tool = tool_name
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
            await self._rerank_payload_results(payload, query)
            executions.append(execution)
            query_payloads.append(payload)
            confidence = float(payload.get("confidence", 0.0))
            mcp_suggestion = payload.get("next_query")
            # Señal opcional del proveedor: qué tool conviene a continuación
            # (p.ej. tras search_papers sugiere download_paper). El selector
            # la respeta si está en el conjunto disponible.
            nxt = payload.get("next_tool")
            suggested_tool = nxt if isinstance(nxt, str) else None
            needs_follow_up = bool(
                payload.get("needs_follow_up", index < depth_limit and confidence < 0.8)
            )
            explored_terms.add(query)
            if not needs_follow_up:
                return False, None

            entities = payload.get("entities")
            discovered = [str(e) for e in entities] if isinstance(entities, list) else []
            strategist_query = strategist.propose(
                StrategistContext(
                    branch_type=self.branch_type.value,
                    seed_query=seed_query,
                    discovered_entities=discovered,
                    explored_terms=explored_terms,
                    cross_branch_hints=list(self._cross_branch_hints),
                ),
                mcp_suggestion=str(mcp_suggestion) if isinstance(mcp_suggestion, str) else None,
            )
            return True, strategist_query

        tracker = SaturationTracker(self._embedding_gateway.embed_document)

        def _iteration_text(idx: int) -> str:
            payload = query_payloads[idx - 1]
            return (
                f"{payload.get('title', '')}\n"
                f"{payload.get('summary') or payload.get('statement') or ''}"
            ).strip()

        iterations = await run_followup_loop(
            branch_type=self.branch_type.value,
            seed_query=seed_query,
            depth_limit=depth_limit,
            execute=execute,
            is_saturated=lambda index: tracker.is_saturated(index, _iteration_text(index)),
        )

        # Reutiliza los vectores que el tracker ya calculó durante el loop;
        # solo embebe las iteraciones que no se evaluaron para saturación.
        embeddings: list[IterationEmbedding] = []
        if len(iterations) >= 2:
            missing = [
                idx for idx, _ in enumerate(iterations, start=1) if tracker.vector_for(idx) is None
            ]
            filled: dict[int, list[float]] = {}
            if missing:
                missing_vectors = await self._embedding_gateway.embed_documents(
                    [f"{iterations[idx - 1].query}\n{_iteration_text(idx)}" for idx in missing]
                )
                filled = dict(zip(missing, missing_vectors, strict=True))
            embeddings = [
                IterationEmbedding(
                    iteration_id=iteration.id,
                    vector=tracker.vector_for(idx) or filled[idx],
                )
                for idx, iteration in enumerate(iterations, start=1)
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
        provider_usage: list[dict[str, str | int]] = [
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

    # ── Datos estructurados (OpenAlex) ────────────────────────────────────

    async def fetch_scholarly_works(self, query: str, limit: int = 10) -> list[dict]:
        """Datos bibliométricos duros (citas, instituciones, año) vía OpenAlex.

        Resiliente: si OpenAlex no responde devuelve [] (no rompe la rama).
        """
        from vigilancia_multiagente.infra.openalex.openalex_client import (
            OpenAlexClient,
            OpenAlexError,
        )

        client = OpenAlexClient()
        try:
            works = await client.search_works(query, per_page=limit)
        except OpenAlexError:
            return []
        finally:
            await client.close()
        return [
            {
                "title": w.title,
                "year": w.publication_year,
                "citations": w.cited_by_count,
                "doi": w.doi,
                "institutions": w.institutions,
                "concepts": w.concepts,
            }
            for w in works
        ]

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
        hint = directive.get("query") or directive.get("focus")
        if isinstance(hint, str) and hint:
            self._cross_branch_hints.append(hint)

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
        return float(cast(float, value)) if value is not None else None

    @staticmethod
    def _require_text(payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if value is None:
            raise RuntimeError(f"Tool response missing required {key}")
        return str(value)

    async def _rerank_payload_results(self, payload: dict, query: str) -> None:
        """Filtra basura y reordena por relevancia los resultados crudos de un
        MCP, si los trae como lista. In-place y resiliente: cualquier fallo
        deja el payload intacto (no rompe el pipeline)."""
        results = payload.get("results")
        if not isinstance(results, list) or len(results) < 3:
            return

        # Descartar SEO-spam / paywalls vacíos ANTES de rerankear: no malgastar
        # embeddings reordenando contenido sin señal.
        try:
            from vigilancia_multiagente.application.research.source_quality_gate import (
                SourceQualityGate,
            )

            gate = SourceQualityGate()
            filtered = [
                r
                for r in results
                if not isinstance(r, dict)
                or gate.accept(
                    str(r.get("url", "")),
                    str(r.get("content") or r.get("summary") or r.get("snippet") or ""),
                )
            ]
            if filtered and len(filtered) < len(results):
                results = filtered
                payload["results"] = filtered
        except Exception:
            pass

        if len(results) < 3:
            return
        texts = [
            f"{r.get('title', '')} {r.get('summary') or r.get('snippet') or ''}".strip()
            if isinstance(r, dict)
            else str(r)
            for r in results
        ]
        try:
            if self._reranker is None:
                from vigilancia_multiagente.infra.reranking.semantic_reranker import (
                    SemanticReranker,
                )

                self._reranker = SemanticReranker(self._embedding_gateway)
            ranked = await self._reranker.rerank(query, texts)
        except Exception:
            return
        if ranked:
            payload["results"] = [results[item.index] for item in ranked]

    @staticmethod
    async def _noop_signal(payload):
        pass  # No coordinator available (testing mode)
