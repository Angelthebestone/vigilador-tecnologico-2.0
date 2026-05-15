from __future__ import annotations

import json
from uuid import NAMESPACE_URL, uuid5
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.domain.models import (
    BranchConfig,
    BranchResult,
    BranchStatus,
    BranchType,
    FinalReport,
    Finding,
    Recommendation,
    ResearchPlan,
    ResearchSession,
    SourceRef,
)
from vigilancia_multiagente.domain.repositories import (
    BranchResultRepository,
    GraphSnapshotRepository,
    PlanRepository,
    ReportRepository,
    SessionTelemetryRepository,
    SessionRepository,
)
from vigilancia_multiagente.domain.session_state import SessionStatus
from vigilancia_multiagente.infra.db.connection import Database


class PostgresSessionRepository(SessionRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, session: ResearchSession) -> ResearchSession:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    """
                    INSERT INTO research_sessions (
                        id, created_at, updated_at, status, user_query, scope,
                        clarification_set_id, approved_plan_id, final_report_id,
                        execution_time_seconds, error_code, error_message
                    ) VALUES (
                        :id, :created_at, :updated_at, :status, :user_query, CAST(:scope AS jsonb),
                        :clarification_set_id, :approved_plan_id, :final_report_id,
                        :execution_time_seconds, :error_code, :error_message
                    )
                    RETURNING *
                    """
                ),
                _session_params(session),
            )
            await db.commit()
            return _session_from_row(result.mappings().one())

    async def get_by_id(self, session_id: UUID) -> ResearchSession | None:
        async with self._database.session() as db:
            result = await db.execute(
                text("SELECT * FROM research_sessions WHERE id = :session_id"),
                {"session_id": str(session_id)},
            )
            row = result.mappings().one_or_none()
            return None if row is None else _session_from_row(row)

    async def update(self, session: ResearchSession) -> ResearchSession:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    """
                    UPDATE research_sessions
                    SET created_at = :created_at,
                        updated_at = :updated_at,
                        status = :status,
                        user_query = :user_query,
                        scope = CAST(:scope AS jsonb),
                        clarification_set_id = :clarification_set_id,
                        approved_plan_id = :approved_plan_id,
                        final_report_id = :final_report_id,
                        execution_time_seconds = :execution_time_seconds,
                        error_code = :error_code,
                        error_message = :error_message
                    WHERE id = :id
                    RETURNING *
                    """
                ),
                _session_params(session),
            )
            await db.commit()
            row = result.mappings().one_or_none()
            if row is None:
                raise KeyError(f"Session not found: {session.id}")
            return _session_from_row(row)


class PostgresPlanRepository(PlanRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, plan: ResearchPlan) -> ResearchPlan:
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO research_plans (
                        id, session_id, version, branches, global_constraints,
                        requires_approval, approved_at
                    ) VALUES (
                        :id, :session_id, :version, CAST(:branches AS jsonb), CAST(:global_constraints AS jsonb),
                        :requires_approval, :approved_at
                    )
                    """
                ),
                _plan_params(plan),
            )
            await db.commit()
            return plan

    async def get_latest_for_session(self, session_id: UUID) -> ResearchPlan | None:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    """
                    SELECT * FROM research_plans
                    WHERE session_id = :session_id
                    ORDER BY version DESC, approved_at DESC NULLS LAST
                    LIMIT 1
                    """
                ),
                {"session_id": str(session_id)},
            )
            row = result.mappings().one_or_none()
            return None if row is None else _plan_from_row(row)


class PostgresBranchResultRepository(BranchResultRepository, SessionTelemetryRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, result: BranchResult) -> BranchResult:
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO branch_results (
                        id, session_id, branch_type, queries_executed, findings, sources,
                        started_at, completed_at, coverage_score, confidence_score, errors
                    ) VALUES (
                        :id, :session_id, :branch_type, CAST(:queries_executed AS jsonb),
                        CAST(:findings AS jsonb), CAST(:sources AS jsonb),
                        :started_at, :completed_at, :coverage_score, :confidence_score, CAST(:errors AS jsonb)
                    )
                    """
                ),
                _branch_result_params(result),
            )
            await db.commit()
            return result

    async def list_by_session(self, session_id: UUID) -> Sequence[BranchResult]:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    """
                    SELECT * FROM branch_results
                    WHERE session_id = :session_id
                    ORDER BY completed_at DESC NULLS LAST, started_at DESC NULLS LAST
                    """
                ),
                {"session_id": str(session_id)},
            )
            rows = result.mappings().all()
            return tuple(_branch_result_from_row(row) for row in rows)

    async def append_iteration_records(self, session_id: UUID, records: Sequence[dict[str, object]]) -> None:
        if not records:
            return
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO iteration_records (id, session_id, branch_type, payload)
                    VALUES (:id, :session_id, :branch_type, CAST(:payload AS jsonb))
                    """
                ),
                [
                    {
                        "id": str(record["id"]),
                        "session_id": str(session_id),
                        "branch_type": str(record["branch_type"]),
                        "payload": _json_dump(record),
                    }
                    for record in records
                ],
            )
            await db.commit()

    async def append_semantic_relations(self, session_id: UUID, records: Sequence[dict[str, object]]) -> None:
        if not records:
            return
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO semantic_relations (id, session_id, payload)
                    VALUES (:id, :session_id, CAST(:payload AS jsonb))
                    """
                ),
                [
                    {
                        "id": str(
                            uuid5(
                                NAMESPACE_URL,
                                f"{session_id}:{record['source_iteration_id']}:{record['target_iteration_id']}:{record['relation_type']}",
                            )
                        ),
                        "session_id": str(session_id),
                        "payload": _json_dump(record),
                    }
                    for record in records
                ],
            )
            await db.commit()

    async def append_provider_telemetry(self, session_id: UUID, records: Sequence[dict[str, object]]) -> None:
        if not records:
            return
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO provider_telemetry (id, session_id, payload)
                    VALUES (:id, :session_id, CAST(:payload AS jsonb))
                    """
                ),
                [
                    {
                        "id": str(uuid5(NAMESPACE_URL, f"{session_id}:{index}:{record.get('provider')}:{record.get('tool')}")),
                        "session_id": str(session_id),
                        "payload": _json_dump(record),
                    }
                    for index, record in enumerate(records, start=1)
                ],
            )
            await db.commit()


class PostgresReportRepository(ReportRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def save_final_report(self, session_id: UUID, report: FinalReport) -> FinalReport:
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO research_reports (session_id, report_markdown)
                    VALUES (:session_id, :report_markdown)
                    ON CONFLICT (session_id)
                    DO UPDATE SET report_markdown = EXCLUDED.report_markdown,
                                  generated_at = NOW()
                    """
                ),
                {"session_id": str(session_id), "report_markdown": _json_dump(_final_report_to_dict(report))},
            )
            await db.commit()
            return report

    async def get(self, session_id: UUID) -> FinalReport | None:
        async with self._database.session() as db:
            result = await db.execute(
                text("SELECT report_markdown FROM research_reports WHERE session_id = :session_id"),
                {"session_id": str(session_id)},
            )
            row = result.first()
            if row is None:
                return None
            data = _json_load(row[0])
            if not isinstance(data, dict):
                return None
            return _final_report_from_dict(data)


class PostgresGraphSnapshotRepository(GraphSnapshotRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def save_graph_snapshot(self, session_id: UUID, snapshot: dict[str, object]) -> dict[str, object]:
        async with self._database.session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO graph_snapshots (session_id, nodes, edges, analytics)
                    VALUES (:session_id, CAST(:nodes AS jsonb), CAST(:edges AS jsonb), CAST(:analytics AS jsonb))
                    ON CONFLICT (session_id)
                    DO UPDATE SET nodes = EXCLUDED.nodes,
                                  edges = EXCLUDED.edges,
                                  analytics = EXCLUDED.analytics,
                                  updated_at = NOW()
                    """
                ),
                {
                    "session_id": str(session_id),
                    "nodes": _json_dump(snapshot.get("nodes", [])),
                    "edges": _json_dump(snapshot.get("edges", [])),
                    "analytics": _json_dump(snapshot.get("analytics", {})),
                },
            )
            await db.commit()
        return snapshot

    async def get_graph_snapshot(self, session_id: UUID) -> dict[str, object] | None:
        async with self._database.session() as db:
            result = await db.execute(
                text("SELECT session_id, nodes, edges, analytics FROM graph_snapshots WHERE session_id = :session_id"),
                {"session_id": str(session_id)},
            )
            row = result.mappings().one_or_none()
            if row is None:
                return None
            return {
                "session_id": str(row["session_id"]),
                "nodes": _json_load_list(row.get("nodes")),
                "edges": _json_load_list(row.get("edges")),
                "analytics": _json_load_dict(row.get("analytics")) or {},
            }


def _session_params(session: ResearchSession) -> dict[str, object]:
    return {
        "id": str(session.id),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "status": session.status.value,
        "user_query": session.user_query,
        "scope": _json_dump(session.scope) if session.scope is not None else None,
        "clarification_set_id": str(session.clarification_set_id) if session.clarification_set_id else None,
        "approved_plan_id": str(session.approved_plan_id) if session.approved_plan_id else None,
        "final_report_id": str(session.final_report_id) if session.final_report_id else None,
        "execution_time_seconds": session.execution_time_seconds,
        "error_code": session.error_code,
        "error_message": session.error_message,
    }


def _session_from_row(row: dict[str, object]) -> ResearchSession:
    return ResearchSession(
        id=UUID(str(row["id"])),
        created_at=_ensure_datetime(row["created_at"]),
        updated_at=_ensure_datetime(row["updated_at"]),
        status=SessionStatus(str(row["status"])),
        user_query=str(row["user_query"]),
        scope=_json_load_dict(row.get("scope")),
        clarification_set_id=_ensure_uuid(row.get("clarification_set_id")),
        approved_plan_id=_ensure_uuid(row.get("approved_plan_id")),
        final_report_id=_ensure_uuid(row.get("final_report_id")),
        execution_time_seconds=_optional_float(row.get("execution_time_seconds")),
        error_code=row.get("error_code"),
        error_message=row.get("error_message"),
    )


def _plan_params(plan: ResearchPlan) -> dict[str, object]:
    return {
        "id": str(plan.id),
        "session_id": str(plan.session_id),
        "version": plan.version,
        "branches": _json_dump([_branch_to_dict(branch) for branch in plan.branches]),
        "global_constraints": _json_dump(plan.global_constraints),
        "requires_approval": plan.requires_approval,
        "approved_at": plan.approved_at,
    }


def _plan_from_row(row: dict[str, object]) -> ResearchPlan:
    branches_payload = _json_load_list(row["branches"])
    return ResearchPlan(
        id=UUID(str(row["id"])),
        session_id=UUID(str(row["session_id"])),
        version=int(row["version"]),
        branches=[_branch_from_dict(payload) for payload in branches_payload],
        global_constraints=_json_load_dict(row.get("global_constraints")) or {},
        requires_approval=bool(row["requires_approval"]),
        approved_at=_optional_datetime(row.get("approved_at")),
    )


def _branch_result_params(result: BranchResult) -> dict[str, object]:
    return {
        "id": str(result.id),
        "session_id": str(result.session_id),
        "branch_type": result.branch_type.value,
        "queries_executed": _json_dump(result.queries_executed),
        "findings": _json_dump([_finding_to_dict(finding) for finding in result.findings]),
        "sources": _json_dump([_source_to_dict(source) for source in result.sources]),
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "coverage_score": result.coverage_score,
        "confidence_score": result.confidence_score,
        "errors": _json_dump(result.errors),
    }


def _branch_result_from_row(row: dict[str, object]) -> BranchResult:
    return BranchResult(
        id=UUID(str(row["id"])),
        session_id=UUID(str(row["session_id"])),
        branch_type=BranchType(str(row["branch_type"])),
        queries_executed=[str(item) for item in _json_load_list(row["queries_executed"])],
        findings=[_finding_from_dict(item) for item in _json_load_list(row["findings"])],
        sources=[_source_from_dict(item) for item in _json_load_list(row["sources"])],
        started_at=_optional_datetime(row.get("started_at")),
        completed_at=_optional_datetime(row.get("completed_at")),
        coverage_score=_optional_float(row.get("coverage_score")),
        confidence_score=_optional_float(row.get("confidence_score")),
        errors=[str(item) for item in _json_load_list(row.get("errors"))],
    )


def _branch_to_dict(branch: BranchConfig) -> dict[str, object]:
    return {
        "branch_type": branch.branch_type.value,
        "focus_queries": list(branch.focus_queries),
        "mcp_providers": list(branch.mcp_providers),
        "mcp_tool_profile": branch.mcp_tool_profile,
        "priority_weight": branch.priority_weight,
        "status": branch.status.value,
    }


def _branch_from_dict(payload: dict[str, object]) -> BranchConfig:
    priority = payload.get("priority_weight")
    return BranchConfig(
        branch_type=BranchType(str(payload["branch_type"])),
        focus_queries=list(payload.get("focus_queries", [])),
        mcp_providers=list(payload.get("mcp_providers", [])),
        mcp_tool_profile=payload.get("mcp_tool_profile"),
        priority_weight=int(priority) if priority is not None else None,
        status=BranchStatus(payload["status"]),
    )


def _finding_to_dict(finding: Finding) -> dict[str, object]:
    return {
        "id": str(finding.id),
        "topic": finding.topic,
        "statement": finding.statement,
        "confidence": finding.confidence,
        "source_ids": [str(source_id) for source_id in finding.source_ids],
        "tags": list(finding.tags),
    }


def _finding_from_dict(payload: dict[str, object]) -> Finding:
    return Finding(
        id=UUID(str(payload["id"])),
        topic=str(payload["topic"]),
        statement=str(payload["statement"]),
        confidence=float(payload["confidence"]),
        source_ids=[UUID(str(source_id)) for source_id in payload.get("source_ids", [])],
        tags=[str(tag) for tag in payload.get("tags", [])],
    )


def _source_to_dict(source: SourceRef) -> dict[str, object]:
    return {
        "id": str(source.id),
        "session_id": str(source.session_id),
        "url": source.url,
        "provider": source.provider,
        "branch_type": source.branch_type.value,
        "accessed_at": source.accessed_at,
        "title": source.title,
        "content_hash": source.content_hash,
    }


def _source_from_dict(payload: dict[str, object]) -> SourceRef:
    return SourceRef(
        id=UUID(str(payload["id"])),
        session_id=UUID(str(payload["session_id"])),
        url=str(payload["url"]),
        provider=str(payload["provider"]),
        branch_type=BranchType(str(payload["branch_type"])),
        accessed_at=_ensure_datetime(payload["accessed_at"]),
        title=payload.get("title"),
        content_hash=payload.get("content_hash"),
    )


def _json_dump(value: object) -> str:
    return json.dumps(_encode_json(value), ensure_ascii=False)


def _json_load_dict(value: object | None) -> dict[str, object] | None:
    if value is None:
        return None
    parsed = _json_load(value)
    if not isinstance(parsed, dict):
        raise TypeError("Expected JSON object")
    return parsed


def _json_load_list(value: object | None) -> list[object]:
    if value is None:
        return []
    parsed = _json_load(value)
    if not isinstance(parsed, list):
        raise TypeError("Expected JSON array")
    return parsed


def _json_load(value: object) -> object:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _encode_json(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _encode_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode_json(item) for item in value]
    if isinstance(value, tuple):
        return [_encode_json(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (BranchType, BranchStatus, SessionStatus)):
        return value.value
    return value


def _ensure_datetime(value: object | None) -> datetime:
    if value is None:
        raise ValueError("datetime value is required")
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _optional_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    return _ensure_datetime(value)


def _ensure_uuid(value: object | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _final_report_to_dict(report: FinalReport) -> dict[str, object]:
    return {
        "session_id": str(report.session_id),
        "generated_at": report.generated_at.isoformat() if isinstance(report.generated_at, datetime) else report.generated_at,
        "markdown": report.markdown,
        "executive_summary": report.executive_summary,
        "technical_section": report.technical_section,
        "commercial_section": report.commercial_section,
        "risk_section": report.risk_section,
        "cross_analysis": report.cross_analysis,
        "recommendations": [
            {"text": r.text, "priority": r.priority, "based_on": r.based_on}
            for r in report.recommendations
        ],
        "all_sources": [_source_to_dict(s) for s in report.all_sources],
        "total_sources_consulted": report.total_sources_consulted,
        "total_learnings": report.total_learnings,
        "confidence_score": report.confidence_score,
    }


def _final_report_from_dict(data: dict[str, object]) -> FinalReport:
    return FinalReport(
        session_id=UUID(str(data["session_id"])),
        generated_at=_ensure_datetime(data["generated_at"]) if isinstance(data.get("generated_at"), str) else data.get("generated_at"),
        markdown=data.get("markdown", ""),
        executive_summary=data.get("executive_summary", ""),
        technical_section=data.get("technical_section", ""),
        commercial_section=data.get("commercial_section", ""),
        risk_section=data.get("risk_section", ""),
        cross_analysis=data.get("cross_analysis", ""),
        recommendations=[
            Recommendation(text=str(r["text"]), priority=str(r.get("priority", "medium")), based_on=[str(b) for b in r.get("based_on", [])])
            for r in (data.get("recommendations") or [])
        ],
        all_sources=[_source_from_dict(s) for s in (data.get("all_sources") or [])],
        total_sources_consulted=int(data.get("total_sources_consulted", 0)),
        total_learnings=int(data.get("total_learnings", 0)),
        confidence_score=float(data.get("confidence_score", 0.0)),
    )
