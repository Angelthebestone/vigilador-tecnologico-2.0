import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from vigilancia_multiagente.application.agents.base import BaseBranchAgent, SignalPayload
from vigilancia_multiagente.application.events.sse_publisher import SessionEvent, format_sse
from vigilancia_multiagente.application.planning.plan_builder import (
    DEFAULT_PROVIDERS as _DEFAULT_PROVIDERS,
)
from vigilancia_multiagente.domain.models import (
    BranchConfig,
    BranchResult,
    BranchType,
    ResearchPlan,
    ResearchSession,
)
from vigilancia_multiagente.domain.ports.event_publisher import EventPublisher
from vigilancia_multiagente.domain.repositories import SessionTelemetryRepository

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    type: str
    source_branch: str
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    iteration: int = 0


@dataclass
class ReplanAction:
    trigger_signal: Signal
    target_branch: str
    directive: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    iteration: int = 0


MAX_REPLANS_PER_SESSION = 5


class BranchCoordinator:
    def __init__(
        self,
        agents: dict[BranchType, BaseBranchAgent],
        telemetry_repository: SessionTelemetryRepository | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._agents = agents
        self._telemetry_repository = telemetry_repository
        self._event_publisher = event_publisher
        self._iterations_by_session: dict[UUID, list[dict[str, str | int | bool | None]]] = {}
        self._relations_by_session: dict[UUID, list[dict[str, str | float]]] = {}
        self._provider_usage_by_session: dict[UUID, list[dict[str, str | int]]] = {}
        self._signal_queue: list[SignalPayload] = []
        self._signals_by_session: dict[UUID, list[dict[str, str | float]]] = {}
        self._sub_results_by_session: dict[UUID, list[BranchResult]] = {}
        self._signal_async_queue: asyncio.Queue | None = None

    async def execute(self, session: ResearchSession, plan: ResearchPlan) -> list[BranchResult]:
        depth_limit = int(plan.global_constraints.get("depth_limit", 3))
        signal_queue: asyncio.Queue = asyncio.Queue()
        self._signal_async_queue = signal_queue
        branch_tasks = [
            asyncio.create_task(self._run_branch(session, branch, depth_limit))
            for branch in plan.branches
        ]
        consumer_task = asyncio.create_task(self._signal_consumer_loop(signal_queue, branch_tasks))
        outputs = await asyncio.gather(*branch_tasks, consumer_task, return_exceptions=True)  # pyright: ignore
        results: list[BranchResult] = []
        for idx, output in enumerate(outputs):
            if output is None:
                continue  # consumer_task result, skip
            if isinstance(output, BaseException):
                branch_type = plan.branches[idx].branch_type
                logger.warning("Branch %s failed: %s", branch_type, output)
                results.append(
                    BranchResult(
                        id=uuid4(),
                        session_id=session.id,
                        branch_type=branch_type,
                        queries_executed=[],
                        findings=[],
                        sources=[],
                        started_at=datetime.now(UTC),
                        completed_at=datetime.now(UTC),
                        errors=[str(output)],
                    )
                )
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
                await self._telemetry_repository.append_provider_telemetry(
                    session.id, output.provider_usage
                )
        await self._process_cross_signals(session, plan)
        results.extend(self._sub_results_by_session.pop(session.id, []))
        return results

    async def _run_branch(
        self,
        session: ResearchSession,
        branch: BranchConfig,
        depth_limit: int,
    ):
        agent = self._agents[branch.branch_type]
        session_key = str(session.id)
        if self._event_publisher is not None:
            await self._event_publisher.publish(
                session.id,
                format_sse(
                    SessionEvent.now(
                        "BranchStarted",
                        session.id,
                        {
                            "branch": branch.branch_type.value,
                            "started_at": datetime.now().isoformat(),
                        },
                    )
                ),
            )
        try:
            result = await agent.run(session, branch, depth_limit)
            if self._event_publisher is not None:
                await self._event_publisher.publish(
                    session.id,
                    format_sse(
                        SessionEvent.now(
                            "BranchCompleted",
                            session.id,
                            {
                                "branch": branch.branch_type.value,
                                "findings_count": len(result.branch_result.findings),
                                "sources_count": len(result.branch_result.sources),
                            },
                        )
                    ),
                )
            return result
        except Exception as e:
            if self._event_publisher is not None:
                await self._event_publisher.publish(
                    session.id,
                    format_sse(
                        SessionEvent.now(
                            "BranchFailed",
                            session.id,
                            {
                                "branch": branch.branch_type.value,
                                "error": str(e),
                            },
                        )
                    ),
                )
            raise

    def queue_signal(self, signal: SignalPayload) -> None:
        """Add a cross-branch signal to the processing queue."""
        self._signal_queue.append(signal)

    async def emit_signal(self, signal: Signal) -> None:
        """Push a reactive signal for mid-execution processing."""
        if self._signal_async_queue is not None:
            await self._signal_async_queue.put(signal)

    async def _process_cross_signals(self, session: ResearchSession, plan: ResearchPlan) -> None:
        """Process queued signals and spawn sub-executions."""
        while self._signal_queue:
            signal = self._signal_queue.pop(0)
            agent = self._agents[signal.target_branch]
            sub_branch = BranchConfig(
                branch_type=signal.target_branch,
                focus_queries=[signal.query],
                mcp_providers=list(_DEFAULT_PROVIDERS.get(signal.target_branch, [])),
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
                self._sub_results_by_session.setdefault(session.id, []).append(
                    output.branch_result
                )
                signal_record["sub_executed"] = True
            except Exception as exc:
                logger.warning("Cross-signal sub-execution failed: %s", exc)
            self._signals_by_session.setdefault(session.id, []).append(signal_record)

    # ── Reactive Planner ───────────────────────────────────────────────────

    async def _signal_consumer_loop(
        self, signal_queue: asyncio.Queue, branch_futures: list[asyncio.Task]
    ) -> None:
        pending = set(branch_futures)
        replan_count = 0

        while pending and replan_count < MAX_REPLANS_PER_SESSION:
            signal_get = asyncio.create_task(signal_queue.get())
            done, _ = await asyncio.wait(
                pending | {signal_get},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if signal_get in done:
                signal: Signal = signal_get.result()
                await self._dispatch_signal(signal, pending)
                replan_count += 1

            done_branches = {t for t in done if t is not signal_get}
            pending -= done_branches

            if not signal_get.done():
                signal_get.cancel()

    async def _dispatch_signal(self, signal: Signal, active_futures: set[asyncio.Task]) -> None:
        handlers = {
            "gap_detected": self._handle_gap_detected,
            "high_value_finding": self._handle_high_value_finding,
            "data_ready": self._handle_data_ready,
            "error": self._handle_branch_error,
        }
        handler = handlers.get(signal.type)
        if handler:
            await handler(signal, active_futures)

    async def _handle_gap_detected(self, signal: Signal, active_futures: set[asyncio.Task]) -> None:
        gap_description = signal.payload.get("description", "")
        suggested_query = signal.payload.get("suggested_query", "")
        target_branch = self._find_best_branch_for_gap(signal)

        if target_branch:
            directive = {
                "action": "search",
                "query": suggested_query or gap_description,
                "focus": signal.payload.get("focus", "exploratory"),
                "source_branch": signal.source_branch,
            }
            action = ReplanAction(
                trigger_signal=signal,
                target_branch=target_branch,
                directive=directive,
            )
            logger.info(json.dumps(action.__dict__, default=str))
            await self._route_new_directive(target_branch, directive)

    async def _handle_high_value_finding(
        self, signal: Signal, active_futures: set[asyncio.Task]
    ) -> None:
        notification = {
            "type": "cross_branch_notification",
            "finding": signal.payload.get("finding", ""),
            "source_branch": signal.source_branch,
            "relevance": signal.payload.get("relevance", "high"),
        }
        logger.info(
            "High-value finding from %s: %s", signal.source_branch, notification["finding"][:100]
        )

    async def _handle_data_ready(self, signal: Signal, active_futures: set[asyncio.Task]) -> None:
        logger.info("Data ready signal from %s: %s", signal.source_branch, signal.payload)

    async def _handle_branch_error(self, signal: Signal, active_futures: set[asyncio.Task]) -> None:
        logger.warning(
            "Branch error from %s: %s", signal.source_branch, signal.payload.get("error", "")
        )

    async def _route_new_directive(self, branch_name: str, directive: dict) -> None:
        logger.info("Replan: routing directive to %s: %s", branch_name, directive)
        branch_type = BranchType(branch_name)
        if branch_type in self._agents:
            branch = self._agents[branch_type]
            await branch.receive_directive(directive)

    def _find_best_branch_for_gap(self, signal: Signal) -> str | None:
        source = signal.source_branch
        all_branches = [bt.value for bt in BranchType]
        available = [b for b in all_branches if b != source]
        if not available:
            return None
        gap_focus = signal.payload.get("focus", "")
        gap_lower = gap_focus.lower()
        if "legal" in gap_lower or "patent" in gap_lower:
            preferred = BranchType.PI_NORMATIVA.value
        elif "competitor" in gap_lower or "market" in gap_lower:
            preferred = BranchType.COMPETITIVO.value
        elif "risk" in gap_lower or "threat" in gap_lower:
            preferred = BranchType.RIESGO.value
        elif "commercial" in gap_lower or "business" in gap_lower:
            preferred = BranchType.COMERCIAL.value
        elif "advance" in gap_lower or "research" in gap_lower:
            preferred = BranchType.AVANCES.value
        else:
            preferred = BranchType.OPORTUNIDADES.value
        return preferred if preferred in available else available[0]

    def get_iterations(self, session_id: UUID) -> list[dict[str, str | int | bool | None]]:
        return self._iterations_by_session.get(session_id, [])

    def get_relations(self, session_id: UUID) -> list[dict[str, str | float]]:
        return self._relations_by_session.get(session_id, [])

    def get_provider_usage(self, session_id: UUID) -> list[dict[str, str | int]]:
        return self._provider_usage_by_session.get(session_id, [])

    def get_signals(self, session_id: UUID) -> list[dict[str, str | float]]:
        return self._signals_by_session.get(session_id, [])
