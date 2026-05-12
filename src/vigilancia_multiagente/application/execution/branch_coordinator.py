import asyncio
from uuid import UUID

from vigilancia_multiagente.application.agents.base import BaseBranchAgent
from vigilancia_multiagente.domain.models import BranchConfig, BranchResult, BranchType, ResearchPlan, ResearchSession
from vigilancia_multiagente.domain.repositories import SessionTelemetryRepository


class BranchCoordinator:
    def __init__(
        self,
        agents: dict[BranchType, BaseBranchAgent],
        telemetry_repository: SessionTelemetryRepository | None = None,
    ) -> None:
        self._agents = agents
        self._telemetry_repository = telemetry_repository
        self._iterations_by_session: dict[UUID, list[dict[str, str | int | bool | None]]] = {}
        self._relations_by_session: dict[UUID, list[dict[str, str | float]]] = {}
        self._provider_usage_by_session: dict[UUID, list[dict[str, str | int]]] = {}

    async def execute(self, session: ResearchSession, plan: ResearchPlan) -> list[BranchResult]:
        depth_limit = int(plan.global_constraints.get("depth_limit", 3))
        coroutines = [self._run_branch(session, branch, depth_limit) for branch in plan.branches]
        outputs = await asyncio.gather(*coroutines)
        results: list[BranchResult] = []
        for output in outputs:
            result = output.branch_result
            results.append(result)
            self._iterations_by_session.setdefault(session.id, []).extend(
                [
                    {
                        "id": str(item.id),
                        "branch_type": item.branch_type,
                        "iteration_index": item.iteration_index,
                        "query": item.query,
                        "query_type": item.query_type,
                        "needs_follow_up": item.needs_follow_up,
                        "stop_reason": item.stop_reason,
                    }
                    for item in output.iterations
                ]
            )
            self._relations_by_session.setdefault(session.id, []).extend(
                [
                    {
                        "source_iteration_id": str(item.source_iteration_id),
                        "target_iteration_id": str(item.target_iteration_id),
                        "relation_type": item.relation_type,
                        "similarity_score": item.similarity_score,
                    }
                    for item in output.semantic_relations
                ]
            )
            self._provider_usage_by_session.setdefault(session.id, []).extend(output.provider_usage)
            if self._telemetry_repository is not None:
                await self._telemetry_repository.append_iteration_records(
                    session.id,
                    [
                        {
                            "id": item.id,
                            "branch_type": item.branch_type,
                            "iteration_index": item.iteration_index,
                            "query": item.query,
                            "query_type": item.query_type,
                            "needs_follow_up": item.needs_follow_up,
                            "next_query": item.next_query,
                            "stop_reason": item.stop_reason,
                            "started_at": item.started_at,
                            "completed_at": item.completed_at,
                        }
                        for item in output.iterations
                    ],
                )
                await self._telemetry_repository.append_semantic_relations(
                    session.id,
                    [
                        {
                            "source_iteration_id": item.source_iteration_id,
                            "target_iteration_id": item.target_iteration_id,
                            "relation_type": item.relation_type,
                            "similarity_score": item.similarity_score,
                        }
                        for item in output.semantic_relations
                    ],
                )
                await self._telemetry_repository.append_provider_telemetry(session.id, output.provider_usage)
        return results

    async def _run_branch(
        self,
        session: ResearchSession,
        branch: BranchConfig,
        depth_limit: int,
    ):
        agent = self._agents[branch.branch_type]
        return await agent.run(session, branch, depth_limit)

    def get_iterations(self, session_id: UUID) -> list[dict[str, str | int | bool | None]]:
        return self._iterations_by_session.get(session_id, [])

    def get_relations(self, session_id: UUID) -> list[dict[str, str | float]]:
        return self._relations_by_session.get(session_id, [])

    def get_provider_usage(self, session_id: UUID) -> list[dict[str, str | int]]:
        return self._provider_usage_by_session.get(session_id, [])

