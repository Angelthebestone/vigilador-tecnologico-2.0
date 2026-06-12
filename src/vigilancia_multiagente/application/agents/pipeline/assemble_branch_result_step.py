from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from vigilancia_multiagente.application.agents.base import AgentRunOutput
from vigilancia_multiagente.application.agents.pipeline.base_step import PipelineStep
from vigilancia_multiagente.application.agents.pipeline.tool_loop_step import ToolLoopContext
from vigilancia_multiagente.application.extraction.entity_extractor import extract_from_payloads
from vigilancia_multiagente.domain.models import BranchResult, BranchType, Finding, SourceRef
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway


def _optional_text(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


def _optional_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    return float(cast(float, value)) if value is not None else None


def _require_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise RuntimeError(f"Tool response missing required {key}")
    return str(value)


class AssembleBranchResultStep(PipelineStep[ToolLoopContext, AgentRunOutput]):
    def __init__(
        self,
        embedding_gateway: EmbeddingGateway,
        branch_type: BranchType,
    ) -> None:
        self._embedding_gateway = embedding_gateway
        self._branch_type = branch_type

    async def execute(self, context: ToolLoopContext) -> AgentRunOutput:
        ctx = context
        session = ctx.session
        branch_overlay = ctx.branch_overlay
        seed_query = ctx.seed_query
        temporal = ctx.temporal
        if temporal is None:
            raise RuntimeError("temporal window not configured on pipeline context")
        iterations = ctx.iterations
        executions = ctx.executions
        query_payloads = ctx.query_payloads
        semantic_relations = ctx.semantic_relations

        last_payload = query_payloads[-1]
        last_execution = executions[-1]
        source = SourceRef(
            id=uuid4(),
            session_id=session.id,
            url=_require_text(last_payload, "url"),
            title=_optional_text(last_payload, "title") or _optional_text(last_payload, "summary"),
            provider=last_execution.provider,
            branch_type=self._branch_type,
            accessed_at=datetime.now(UTC),
            content_hash=_optional_text(last_payload, "content_hash"),
        )
        finding = Finding(
            id=uuid4(),
            topic=f"{self._branch_type.value.lower()}-signals",
            statement=_optional_text(last_payload, "summary")
            or _optional_text(last_payload, "statement")
            or seed_query,
            confidence=_optional_float(last_payload, "confidence") or 0.7,
            source_ids=[source.id],
            tags=[branch_overlay.version, temporal.basis],
        )
        entities = extract_from_payloads(query_payloads, self._branch_type, [source.id])
        result = BranchResult(
            id=uuid4(),
            session_id=session.id,
            branch_type=self._branch_type,
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
                "latency_ms": int(_optional_float(payload, "latency_ms") or 0),
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
