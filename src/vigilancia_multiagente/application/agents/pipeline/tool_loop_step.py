from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from vigilancia_multiagente.application.agents.pipeline.base_step import PipelineStep
from vigilancia_multiagente.application.agents.pipeline.compose_prompt_step import (
    ComposePromptContext,
)
from vigilancia_multiagente.application.mcp.types import ToolExecutionResult
from vigilancia_multiagente.application.research.followup_loop import (
    run_followup_loop,
)
from vigilancia_multiagente.application.research.followup_strategist import (
    FollowupStrategist,
    StrategistContext,
)
from vigilancia_multiagente.application.research.saturation import SaturationTracker
from vigilancia_multiagente.application.research.semantic_relations import (
    IterationEmbedding,
    build_relations,
)
from vigilancia_multiagente.application.research.temporal_window import TemporalWindow
from vigilancia_multiagente.application.routing.tool_selector import (
    SelectionContext,
    ToolSelector,
)
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher
from vigilancia_multiagente.domain.ports.provider_registry import ProviderConfig
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor


@dataclass(slots=True)
class ToolLoopContext(ComposePromptContext):
    depth_limit: int = 3
    iterations: list = field(default_factory=list)
    executions: list = field(default_factory=list)
    query_payloads: list = field(default_factory=list)
    semantic_relations: list = field(default_factory=list)
    provider_usage: list = field(default_factory=list)
    branch_result: object | None = None
    tool_selector: ToolSelector | None = None
    query_type: str = "general"
    temporal: TemporalWindow | None = None
    seed_query: str = ""
    providers: list[ProviderConfig] = field(default_factory=list)


class ToolLoopStep(PipelineStep[ToolLoopContext, ToolLoopContext]):
    def __init__(
        self,
        execution_client: ToolExecutor,
        embedding_gateway: EmbeddingGateway,
        event_publisher: EventPublisher | None,
        cross_branch_hints: deque[str],
        branch_type: BranchType,
    ) -> None:
        self._execution_client = execution_client
        self._embedding_gateway = embedding_gateway
        self._event_publisher = event_publisher
        self._cross_branch_hints = cross_branch_hints
        self._branch_type = branch_type
        self._reranker: Any = None

    async def execute(self, context: ToolLoopContext) -> ToolLoopContext:
        ctx = context
        session = ctx.session
        branch_overlay = ctx.branch_overlay
        depth_limit = ctx.depth_limit
        tool_selector = ctx.tool_selector
        if tool_selector is None:
            raise RuntimeError("tool_selector not configured on pipeline context")
        query_type = ctx.query_type
        temporal = ctx.temporal
        if temporal is None:
            raise RuntimeError("temporal window not configured on pipeline context")
        seed_query = ctx.seed_query
        providers = ctx.providers
        composed = ctx.composed

        executions: list[ToolExecutionResult] = []
        query_payloads: list[dict[str, object]] = []
        strategist = FollowupStrategist()
        explored_terms: set[str] = {seed_query}
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
                    "branch_type": self._branch_type.value,
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
                    branch_type=self._branch_type.value,
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
            branch_type=self._branch_type.value,
            seed_query=seed_query,
            depth_limit=depth_limit,
            execute=execute,
            is_saturated=lambda index: tracker.is_saturated(index, _iteration_text(index)),
        )

        embeddings: list[IterationEmbedding] = []
        if len(iterations) >= 2:
            missing = [
                idx
                for idx, _ in enumerate(iterations, start=1)
                if tracker.vector_for(idx) is None
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
        ctx.iterations = iterations
        ctx.executions = executions
        ctx.query_payloads = query_payloads
        ctx.semantic_relations = semantic_relations
        return ctx

    def _select_provider(
        self, providers: list[ProviderConfig], tool_name: str
    ) -> ProviderConfig:
        for provider in providers:
            if tool_name in provider.enabled_tools:
                return provider
        raise RuntimeError(f"No provider exposes tool {tool_name} for {self._branch_type.value}")

    async def _rerank_payload_results(self, payload: dict, query: str) -> None:
        results = payload.get("results")
        if not isinstance(results, list) or len(results) < 3:
            return

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
