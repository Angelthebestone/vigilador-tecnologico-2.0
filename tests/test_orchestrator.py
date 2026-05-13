from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.orchestration.orchestrator_service import OrchestratorService
from vigilancia_multiagente.domain.models import BranchConfig, BranchResult, BranchStatus, BranchType, Finding, FinalReport, ResearchPlan, ResearchSession, SourceRef
from vigilancia_multiagente.domain.session_state import SessionStatus

from tests.conftest import FakeDatabase, FakeResult, MemorySessionRepository
from vigilancia_multiagente.infra.persistence.postgres_repositories import (
    PostgresBranchResultRepository,
    PostgresPlanRepository,
    PostgresReportRepository,
    PostgresSessionRepository,
)


@pytest.mark.asyncio
async def test_orchestrator_start_and_transition():
    repo = MemorySessionRepository()
    orchestrator = OrchestratorService(repo)

    session = await orchestrator.start_session("monitor technology")
    assert session.status == SessionStatus.CLARIFYING

    transitioned = await orchestrator.transition(session.id, SessionStatus.PLANNING)
    assert transitioned.status == SessionStatus.PLANNING
    assert transitioned.updated_at >= session.updated_at


@pytest.mark.asyncio
async def test_postgres_repositories_roundtrip_serialization():
    session_id = uuid4()
    now = datetime.now(UTC)
    source_id = uuid4()
    finding_id = uuid4()
    branch_result_id = uuid4()
    plan_id = uuid4()
    session = ResearchSession(
        id=session_id,
        created_at=now,
        updated_at=now,
        status=SessionStatus.EXECUTING,
        user_query="test query",
        scope={"geo": "global"},
    )
    plan = ResearchPlan(
        id=plan_id,
        session_id=session_id,
        version=2,
        branches=[
            BranchConfig(
                branch_type=BranchType.COMERCIAL,
                focus_queries=["commercial signal"],
                mcp_providers=["exa"],
                mcp_tool_profile="default",
                priority_weight=50,
                status=BranchStatus.RUNNING,
            )
        ],
        global_constraints={"depth_limit": 4},
        requires_approval=False,
        approved_at=now,
    )
    branch_result = BranchResult(
        id=branch_result_id,
        session_id=session_id,
        branch_type=BranchType.COMERCIAL,
        queries_executed=["commercial signal"],
        findings=[
            Finding(
                id=finding_id,
                topic="commercial",
                statement="signal detected",
                confidence=0.9,
                source_ids=[source_id],
                tags=["signal"],
            )
        ],
        sources=[
            SourceRef(
                id=source_id,
                session_id=session_id,
                url="https://example.com/signal",
                provider="exa",
                branch_type=BranchType.COMERCIAL,
                accessed_at=now,
                title="Signal",
            )
        ],
        started_at=now,
        completed_at=now,
        coverage_score=0.8,
        confidence_score=0.9,
        errors=["none"],
    )

    session_db = FakeDatabase(
        [
            FakeResult(
                row={
                    "id": str(session.id),
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "status": SessionStatus.CLARIFYING.value,
                    "user_query": session.user_query,
                    "scope": session.scope,
                    "clarification_set_id": None,
                    "approved_plan_id": None,
                    "final_report_id": None,
                    "execution_time_seconds": None,
                    "error_code": None,
                    "error_message": None,
                }
            ),
            FakeResult(
                row={
                    "id": str(session.id),
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "status": SessionStatus.PLANNING.value,
                    "user_query": session.user_query,
                    "scope": session.scope,
                    "clarification_set_id": None,
                    "approved_plan_id": None,
                    "final_report_id": None,
                    "execution_time_seconds": None,
                    "error_code": None,
                    "error_message": None,
                }
            ),
        ]
    )
    session_repo = PostgresSessionRepository(session_db)
    created = await session_repo.create(session)
    assert created.user_query == "test query"
    updated = await session_repo.update(created)
    assert updated.status == SessionStatus.PLANNING

    plan_db = FakeDatabase(
        [
            FakeResult(),
            FakeResult(
                row={
                    "id": str(plan.id),
                    "session_id": str(plan.session_id),
                    "version": plan.version,
                    "branches": [
                        {
                            "branch_type": plan.branches[0].branch_type.value,
                            "focus_queries": plan.branches[0].focus_queries,
                            "mcp_providers": plan.branches[0].mcp_providers,
                            "mcp_tool_profile": plan.branches[0].mcp_tool_profile,
                            "priority_weight": plan.branches[0].priority_weight,
                            "status": plan.branches[0].status.value,
                        }
                    ],
                    "global_constraints": plan.global_constraints,
                    "requires_approval": plan.requires_approval,
                    "approved_at": plan.approved_at,
                }
            ),
        ]
    )
    plan_repo = PostgresPlanRepository(plan_db)
    saved_plan = await plan_repo.create(plan)
    assert saved_plan.version == 2
    latest = await plan_repo.get_latest_for_session(session_id)
    assert latest is not None
    assert latest.branches[0].branch_type == BranchType.COMERCIAL

    branch_db = FakeDatabase(
        [
            FakeResult(),
            FakeResult(
                rows=[
                    {
                        "id": str(branch_result.id),
                        "session_id": str(branch_result.session_id),
                        "branch_type": branch_result.branch_type.value,
                        "queries_executed": branch_result.queries_executed,
                        "findings": [
                            {
                                "id": str(finding_id),
                                "topic": "commercial",
                                "statement": "signal detected",
                                "confidence": 0.9,
                                "source_ids": [str(source_id)],
                                "tags": ["signal"],
                            }
                        ],
                        "sources": [
                            {
                                "id": str(source_id),
                                "session_id": str(session_id),
                                "url": "https://example.com/signal",
                                "provider": "exa",
                                "branch_type": BranchType.COMERCIAL.value,
                                "accessed_at": now,
                                "title": "Signal",
                                "content_hash": None,
                            }
                        ],
                        "started_at": now,
                        "completed_at": now,
                        "coverage_score": 0.8,
                        "confidence_score": 0.9,
                        "errors": ["none"],
                    }
                ]
            ),
        ]
    )
    branch_repo = PostgresBranchResultRepository(branch_db)
    saved_result = await branch_repo.create(branch_result)
    assert saved_result.coverage_score == 0.8
    listed = await branch_repo.list_by_session(session_id)
    assert len(listed) == 1
    assert listed[0].findings[0].statement == "signal detected"

    report_db = FakeDatabase([FakeResult(), FakeResult(row={"report_markdown": '{"session_id":"' + str(session_id) + '","markdown":"# Test Report\\n\\nContent here","executive_summary":"Test","technical_section":"","commercial_section":"","risk_section":"","cross_analysis":"","recommendations":[],"total_sources_consulted":5,"total_learnings":3,"confidence_score":0.8}'})])
    report_repo = PostgresReportRepository(report_db)
    report = await report_repo.save_final_report(session_id, FinalReport(
        session_id=session_id,
        markdown="# Test Report\n\nContent here",
        executive_summary="Test",
        total_sources_consulted=5,
        total_learnings=3,
        confidence_score=0.8,
    ))
    assert report.markdown == "# Test Report\n\nContent here"
    read = await report_repo.get(session_id)
    assert read is not None
    assert read.executive_summary == "Test"
    assert read.markdown == "# Test Report\n\nContent here"

