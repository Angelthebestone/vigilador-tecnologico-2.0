from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from vigilancia_multiagente.domain.models import (
    BranchResult,
    FinalReport,
    ResearchPlan,
    ResearchSession,
)


class SessionRepository(Protocol):
    async def create(self, session: ResearchSession) -> ResearchSession: ...

    async def get_by_id(self, session_id: UUID) -> ResearchSession | None: ...

    async def update(self, session: ResearchSession) -> ResearchSession: ...

    async def delete(self, session_id: UUID) -> None: ...


class PlanRepository(Protocol):
    async def create(self, plan: ResearchPlan) -> ResearchPlan: ...

    async def get_latest_for_session(self, session_id: UUID) -> ResearchPlan | None: ...


class BranchResultRepository(Protocol):
    async def create(self, result: BranchResult) -> BranchResult: ...

    async def list_by_session(self, session_id: UUID) -> Sequence[BranchResult]: ...


class SessionTelemetryRepository(Protocol):
    async def append_iteration_records(
        self, session_id: UUID, records: Sequence[dict[str, object]]
    ) -> None: ...

    async def append_semantic_relations(
        self, session_id: UUID, records: Sequence[dict[str, object]]
    ) -> None: ...

    async def append_provider_telemetry(
        self, session_id: UUID, records: Sequence[dict[str, object]]
    ) -> None: ...


class GraphSnapshotRepository(Protocol):
    async def save_graph_snapshot(
        self, session_id: UUID, snapshot: dict[str, object]
    ) -> dict[str, object]: ...

    async def get_graph_snapshot(self, session_id: UUID) -> dict[str, object] | None: ...


class ReportRepository(Protocol):
    async def save_final_report(self, session_id: UUID, report: FinalReport) -> FinalReport: ...

    async def get(self, session_id: UUID) -> FinalReport | None: ...
