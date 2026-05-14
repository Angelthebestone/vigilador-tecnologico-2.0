from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VT_EMBEDDING_API_KEY", "test-embedding-key")
os.environ.setdefault("VT_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/vigilancia")

from vigilancia_multiagente.api.app import app
from vigilancia_multiagente.api import dependencies as api_dependencies
from vigilancia_multiagente.api.routes import research_approve, research_governance, research_outputs, research_start_clarify
from vigilancia_multiagente.application.artifacts.manifest_service import SessionArtifactService
from vigilancia_multiagente.application.clarification.clarification_service import ClarificationService
from vigilancia_multiagente.application.evaluation.prompt_regression_service import PromptRegressionService
from vigilancia_multiagente.application.fusion.evidence_linker import EvidenceLinker
from vigilancia_multiagente.application.graph.knowledge_graph_service import KnowledgeGraphService
from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.observability.metrics_service import MetricsService
from vigilancia_multiagente.application.orchestration.orchestrator_service import OrchestratorService
from vigilancia_multiagente.application.planning.plan_builder import PlanBuilder
from vigilancia_multiagente.domain.models import BranchResult, Finding, ResearchPlan, ResearchSession, SourceRef


class FakeResult:
    def __init__(self, row: dict[str, object] | None = None, rows: list[dict[str, object]] | None = None) -> None:
        self._row = row
        self._rows = rows or []

    def mappings(self) -> "FakeResult":
        return self

    def one(self) -> dict[str, object]:
        assert self._row is not None
        return self._row

    def one_or_none(self) -> dict[str, object] | None:
        return self._row

    def all(self) -> list[dict[str, object]]:
        return self._rows

    def first(self) -> dict[str, object] | None:
        if isinstance(self._row, dict):
            return tuple(self._row.values())
        return self._row


class FakeDBSession:
    def __init__(self, results: list[FakeResult] | None = None) -> None:
        self.results = results or []
        self.executed: list[tuple[str, dict[str, object]]] = []
        self.commits = 0

    async def execute(self, statement: object, params: dict[str, object]) -> FakeResult:
        self.executed.append((str(statement), params))
        if self.results:
            return self.results.pop(0)
        return FakeResult()

    async def commit(self) -> None:
        self.commits += 1


class FakeDatabase:
    def __init__(self, results: list[FakeResult] | None = None) -> None:
        self.session_obj = FakeDBSession(results)

    @asynccontextmanager
    async def session(self):
        yield self.session_obj


class MemorySessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[UUID, ResearchSession] = {}

    async def create(self, session: ResearchSession) -> ResearchSession:
        self.sessions[session.id] = session
        return session

    async def get_by_id(self, session_id: UUID) -> ResearchSession | None:
        return self.sessions.get(session_id)

    async def update(self, session: ResearchSession) -> ResearchSession:
        self.sessions[session.id] = session
        return session


class MemoryPlanRepository:
    def __init__(self) -> None:
        self.plans: dict[UUID, list[ResearchPlan]] = {}

    async def create(self, plan: ResearchPlan) -> ResearchPlan:
        self.plans.setdefault(plan.session_id, []).append(plan)
        return plan

    async def get_latest_for_session(self, session_id: UUID) -> ResearchPlan | None:
        plans = self.plans.get(session_id, [])
        return plans[-1] if plans else None


class MemoryBranchResultRepository:
    def __init__(self) -> None:
        self.results: dict[UUID, list[BranchResult]] = {}

    async def create(self, result: BranchResult) -> BranchResult:
        self.results.setdefault(result.session_id, []).append(result)
        return result

    async def list_by_session(self, session_id: UUID) -> tuple[BranchResult, ...]:
        return tuple(self.results.get(session_id, []))


class MemoryReportRepository:
    def __init__(self) -> None:
        self.reports: dict[UUID, str] = {}

    async def save_final_report(self, session_id: UUID, report_markdown: str) -> str:
        self.reports[session_id] = report_markdown
        return report_markdown

    async def get(self, session_id: UUID) -> str | None:
        return self.reports.get(session_id)


class MemoryGraphSnapshotRepository:
    def __init__(self) -> None:
        self.snapshots: dict[UUID, dict[str, object]] = {}

    async def save_graph_snapshot(self, session_id: UUID, snapshot: dict[str, object]) -> dict[str, object]:
        self.snapshots[session_id] = snapshot
        return snapshot

    async def get_graph_snapshot(self, session_id: UUID) -> dict[str, object] | None:
        return self.snapshots.get(session_id)


class MemoryVectorIndex:
    def __init__(self) -> None:
        self.records: list[object] = []

    async def upsert(self, record: object) -> None:
        self.records.append(record)

    async def list_by_session(self, session_id: UUID | None, limit: int | None = None) -> list[object]:
        del session_id
        records = list(self.records)
        return records[:limit] if limit is not None else records


class FakeEmbeddingGateway:
    async def embed_document(self, text: str) -> list[float]:
        return await self.embed(text)

    async def embed(self, text: str, task_type: object = None) -> list[float]:
        del task_type
        tokens = text.lower().split()
        score = float(len(tokens) or 1)
        return [score, 0.0, 0.0, 0.0]


class FakeBranchCoordinator:
    def __init__(self) -> None:
        self.iterations: dict[UUID, list[dict[str, object]]] = {}
        self.relations: dict[UUID, list[dict[str, object]]] = {}
        self.provider_usage: dict[UUID, list[dict[str, object]]] = {}

    async def execute(self, session: ResearchSession, plan: ResearchPlan) -> list[BranchResult]:
        now = datetime.now(UTC)
        results: list[BranchResult] = []
        for index, branch in enumerate(plan.branches, start=1):
            source = SourceRef(
                id=uuid4(),
                session_id=session.id,
                url=f"https://example.com/{branch.branch_type.value.lower()}",
                provider="tavily",
                branch_type=branch.branch_type,
                accessed_at=now,
                title=f"{branch.branch_type.value} source",
            )
            finding = Finding(
                id=uuid4(),
                topic=f"{branch.branch_type.value} topic",
                statement=f"{branch.branch_type.value} signal",
                confidence=0.87,
                source_ids=[source.id],
            )
            result = BranchResult(
                id=uuid4(),
                session_id=session.id,
                branch_type=branch.branch_type,
                queries_executed=[f"{branch.branch_type.value.lower()} seed query"],
                findings=[finding],
                sources=[source],
                started_at=now,
                completed_at=now,
                coverage_score=0.84,
                confidence_score=0.79,
            )
            results.append(result)
            iteration_id = uuid4()
            self.iterations.setdefault(session.id, []).append(
                {
                    "id": str(iteration_id),
                    "branch_type": branch.branch_type.value,
                    "iteration_index": index,
                    "query": f"{branch.branch_type.value.lower()} seed query",
                    "query_type": "SEED",
                    "needs_follow_up": False,
                    "next_query": None,
                    "stop_reason": "NO_FOLLOW_UP",
                    "started_at": now,
                    "completed_at": now,
                }
            )
            if index > 1:
                self.relations.setdefault(session.id, []).append(
                    {
                        "source_iteration_id": self.iterations[session.id][index - 2]["id"],
                        "target_iteration_id": str(iteration_id),
                        "relation_type": "SUPPORTS",
                        "similarity_score": 0.81,
                    }
                )
            self.provider_usage.setdefault(session.id, []).append(
                {
                    "provider": "tavily",
                    "tool": "tavily-search",
                    "latency_ms": 123,
                    "result_status": "SUCCESS",
                    "attempt_count": 1,
                }
            )
        return results

    def get_iterations(self, session_id: UUID) -> list[dict[str, object]]:
        return self.iterations.get(session_id, [])

    def get_relations(self, session_id: UUID) -> list[dict[str, object]]:
        return self.relations.get(session_id, [])

    def get_provider_usage(self, session_id: UUID) -> list[dict[str, object]]:
        return self.provider_usage.get(session_id, [])




@pytest.fixture
def memory_repositories(monkeypatch, tmp_path: Path):
    api_dependencies.event_log.clear()
    session_repo = MemorySessionRepository()
    plan_repo = MemoryPlanRepository()
    branch_repo = MemoryBranchResultRepository()
    report_repo = MemoryReportRepository()
    graph_snapshot_repo = MemoryGraphSnapshotRepository()
    vector_index = MemoryVectorIndex()
    branch_coordinator = FakeBranchCoordinator()
    artifact_service = SessionArtifactService(tmp_path / "sessions")
    orchestrator = OrchestratorService(session_repo)

    async def _noop_initialize() -> None:
        return None

    monkeypatch.setattr(api_dependencies.database, "initialize", _noop_initialize, raising=False)
    monkeypatch.setattr(research_start_clarify, "session_repository", session_repo)
    monkeypatch.setattr(research_start_clarify, "orchestrator", orchestrator)
    monkeypatch.setattr(research_start_clarify, "clarification_service", ClarificationService())
    monkeypatch.setattr(research_start_clarify, "plan_builder", PlanBuilder())
    monkeypatch.setattr(research_start_clarify, "plan_repository", plan_repo)
    monkeypatch.setattr(research_start_clarify, "event_log", api_dependencies.event_log)

    monkeypatch.setattr(research_approve, "session_repository", session_repo)
    monkeypatch.setattr(research_approve, "plan_repository", plan_repo)
    monkeypatch.setattr(research_approve, "orchestrator", orchestrator)
    monkeypatch.setattr(research_approve, "branch_coordinator", branch_coordinator)
    monkeypatch.setattr(research_approve, "branch_result_repository", branch_repo)
    monkeypatch.setattr(research_approve, "report_repository", report_repo)
    monkeypatch.setattr(research_approve, "artifact_service", artifact_service)
    monkeypatch.setattr(research_approve, "embedding_gateway", FakeEmbeddingGateway())
    monkeypatch.setattr(research_approve, "vector_index", vector_index)
    monkeypatch.setattr(research_approve, "graph_snapshot_repository", graph_snapshot_repo)
    monkeypatch.setattr(research_approve, "event_log", api_dependencies.event_log)

    monkeypatch.setattr(research_outputs, "branch_coordinator", branch_coordinator)
    monkeypatch.setattr(research_outputs, "branch_result_repository", branch_repo)
    monkeypatch.setattr(research_outputs, "report_repository", report_repo)
    monkeypatch.setattr(research_outputs, "graph_service", KnowledgeGraphService())
    monkeypatch.setattr(research_outputs, "metrics_service", MetricsService())
    monkeypatch.setattr(research_outputs, "evidence_linker", EvidenceLinker())
    monkeypatch.setattr(research_outputs, "embedding_gateway", FakeEmbeddingGateway())
    monkeypatch.setattr(research_outputs, "vector_index", vector_index)
    monkeypatch.setattr(research_outputs, "graph_snapshot_repository", graph_snapshot_repo)
    monkeypatch.setattr(research_outputs, "event_log", api_dependencies.event_log)

    monkeypatch.setattr(research_governance, "branch_coordinator", branch_coordinator)
    monkeypatch.setattr(research_governance, "branch_result_repository", branch_repo)
    monkeypatch.setattr(research_governance, "prompt_regression_service", PromptRegressionService())
    monkeypatch.setattr(research_governance, "governance_loader", GovernanceContractLoader(Path("specs/002-vigilancia-multiagente/contracts")))

    with TestClient(app) as client:
        yield {
            "client": client,
            "session_repo": session_repo,
            "plan_repo": plan_repo,
            "branch_repo": branch_repo,
            "report_repo": report_repo,
            "branch_coordinator": branch_coordinator,
            "artifact_root": artifact_service,
            "vector_index": vector_index,
            "graph_snapshot_repo": graph_snapshot_repo,
        }

