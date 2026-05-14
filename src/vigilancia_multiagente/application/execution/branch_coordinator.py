import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from vigilancia_multiagente.application.agents.base import BaseBranchAgent, SignalPayload
from vigilancia_multiagente.application.planning.plan_builder import DEFAULT_PROVIDERS as _DEFAULT_PROVIDERS
from vigilancia_multiagente.domain.models import BranchConfig, BranchResult, BranchType, ResearchPlan, ResearchSession
from vigilancia_multiagente.domain.repositories import SessionTelemetryRepository

logger = logging.getLogger(__name__)


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
        self._signal_queue: list[SignalPayload] = []
        self._signals_by_session: dict[UUID, list[dict[str, str | float]]] = {}
        self._sub_results: list[BranchResult] = []

    async def execute(self, session: ResearchSession, plan: ResearchPlan) -> list[BranchResult]:
        depth_limit = int(plan.global_constraints.get("depth_limit", 3))
        coroutines = [self._run_branch(session, branch, depth_limit) for branch in plan.branches]
        outputs = await asyncio.gather(*coroutines, return_exceptions=True)
        results: list[BranchResult] = []
        for idx, output in enumerate(outputs):
            if isinstance(output, Exception):
                branch_type = plan.branches[idx].branch_type
                logger.warning("Branch %s failed: %s", branch_type, output)
                results.append(BranchResult(
                    id=uuid4(),
                    session_id=session.id,
                    branch_type=branch_type,
                    queries_executed=[],
                    findings=[],
                    sources=[],
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                    errors=[str(output)],
                ))
                continue
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
        await self._process_cross_signals(session, plan)
        results.extend(self._sub_results)
        self._sub_results.clear()
        return results

    async def _run_branch(
        self,
        session: ResearchSession,
        branch: BranchConfig,
        depth_limit: int,
    ):
        from vigilancia_multiagente.api.dependencies import event_log
        from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse

        agent = self._agents[branch.branch_type]
        event_log[str(session.id)].append(format_sse(SessionEvent.now("BranchStarted", session.id, {
            "branch": branch.branch_type.value,
            "started_at": datetime.now().isoformat(),
        })))
        try:
            result = await agent.run(session, branch, depth_limit)
            event_log[str(session.id)].append(format_sse(SessionEvent.now("BranchCompleted", session.id, {
                "branch": branch.branch_type.value,
                "findings_count": len(result.branch_result.findings),
                "sources_count": len(result.branch_result.sources),
            })))
            return result
        except Exception as e:
            event_log[str(session.id)].append(format_sse(SessionEvent.now("BranchFailed", session.id, {
                "branch": branch.branch_type.value,
                "error": str(e),
            })))
            raise

    def queue_signal(self, signal: SignalPayload) -> None:
        """Add a cross-branch signal to the processing queue."""
        self._signal_queue.append(signal)

    async def _process_cross_signals(self, session: ResearchSession, plan: ResearchPlan) -> None:
        """Process queued signals and spawn sub-executions."""
        while self._signal_queue:
            signal = self._signal_queue.pop(0)
            agent = self._agents[signal.target_branch]
            sub_branch = BranchConfig(
                branch_type=signal.target_branch,
                focus_queries=[signal.query],
                mcp_providers=list(
                    _DEFAULT_PROVIDERS.get(signal.target_branch, [])
                ),
            )
            signal_record: dict[str, str | float | bool] = {
                "source": signal.source_branch.value,
                "target": signal.target_branch.value,
                "query": signal.query,
                "source_url": signal.source_url,
                "relevance": signal.relevance,
                "sub_executed": False,
            }
            try:
                output = await agent.run(session, sub_branch, depth_limit=2)
                self._sub_results.append(output.branch_result)
                signal_record["sub_executed"] = True
            except Exception as exc:
                logger.warning("Cross-signal sub-execution failed: %s", exc)
            self._signals_by_session.setdefault(session.id, []).append(signal_record)

    def get_iterations(self, session_id: UUID) -> list[dict[str, str | int | bool | None]]:
        return self._iterations_by_session.get(session_id, [])

    def get_relations(self, session_id: UUID) -> list[dict[str, str | float]]:
        return self._relations_by_session.get(session_id, [])

    def get_provider_usage(self, session_id: UUID) -> list[dict[str, str | int]]:
        return self._provider_usage_by_session.get(session_id, [])

    def get_signals(self, session_id: UUID) -> list[dict[str, str | float]]:
        return self._signals_by_session.get(session_id, [])

