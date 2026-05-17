import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from vigilancia_multiagente.application.forecasting.trend_forecaster import TrendForecasterService
from vigilancia_multiagente.domain.models import ResearchPlan, ResearchSession
from vigilancia_multiagente.domain.repositories import SessionRepository
from vigilancia_multiagente.domain.session_state import SessionStatus, ensure_transition

logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(
        self,
        session_repository: SessionRepository,
        cross_session_service=None,
        trend_forecaster: TrendForecasterService | None = None,
        source_scorer=None,
        report_generator=None,
    ) -> None:
        self._session_repository = session_repository
        self._cross_session_service = cross_session_service
        self.trend_forecaster = trend_forecaster
        self.source_scorer = source_scorer
        self.report_generator = report_generator

    async def start_session(
        self, user_query: str, scope: dict[str, str] | None = None
    ) -> ResearchSession:
        now = datetime.now(UTC)
        session = ResearchSession(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            status=SessionStatus.CLARIFYING,
            user_query=user_query,
            scope=scope,
        )
        return await self._session_repository.create(session)

    async def transition(self, session_id: UUID, target: SessionStatus) -> ResearchSession:
        session = await self._session_repository.get_by_id(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")
        ensure_transition(session.status, target)
        session.status = target
        session.updated_at = datetime.now(UTC)
        return await self._session_repository.update(session)

    async def execute_research(
        self, session: ResearchSession, plan: ResearchPlan, branch_coordinator
    ) -> list:
        signal_queue: asyncio.Queue = asyncio.Queue()
        depth_limit = int(plan.global_constraints.get("depth_limit", 3))

        branch_tasks = [
            asyncio.create_task(branch_coordinator._run_branch(session, branch, depth_limit))
            for branch in plan.branches
        ]

        branch_coordinator._signal_async_queue = signal_queue

        consumer_task = asyncio.create_task(
            branch_coordinator._signal_consumer_loop(signal_queue, branch_tasks)
        )

        outputs = await asyncio.gather(*branch_tasks, consumer_task, return_exceptions=True)

        results = []
        for output in outputs[: len(plan.branches)]:
            if isinstance(output, BaseException):
                continue
            if hasattr(output, "branch_result"):
                results.append(output.branch_result)

        return results

    async def preload_for_session(self, query: str) -> dict:
        if self._cross_session_service is None:
            return {}
        preload_context = await self._cross_session_service.preload_session(query)
        if preload_context.get("related_sessions"):
            logger.info("Found %d related prior sessions", len(preload_context["related_sessions"]))
        return preload_context

    async def analyze_trends(self, session_data: dict) -> list[dict]:
        if not self.trend_forecaster:
            return []
        try:
            projections = await self.trend_forecaster.analyze(session_data)
            trending_data = [p for p in projections if p.data_quality != "insufficient"]
            logger.info(f"Generated {len(trending_data)} trend projections")
            return [p.__dict__ for p in trending_data]
        except Exception as e:
            logger.warning(f"Trend forecasting failed (non-blocking): {e}")
            return []

    async def cross_reference_findings(self, session_data: dict) -> None:
        if not self.source_scorer:
            return
        try:
            findings_list = session_data.get("findings", [])
            for i, a in enumerate(findings_list):
                for b in findings_list[i + 1 :]:
                    claim_a = a.get("claim")
                    claim_b = b.get("claim")
                    if not claim_a or not claim_b:
                        continue
                    if self._claims_match(claim_a, claim_b):
                        await self.source_scorer.record_confirmation(
                            a.get("source", ""), b.get("source", "")
                        )
                    elif self._claims_contradict(claim_a, claim_b):
                        await self.source_scorer.record_contradiction(
                            a.get("source", ""), b.get("source", "")
                        )
            logger.info(
                "Source scoring: cross-referenced findings for confirmations/contradictions"
            )
        except Exception as e:
            logger.warning(f"Source scoring failed (non-blocking): {e}")

    @staticmethod
    def _claims_match(claim_a: str, claim_b: str) -> bool:
        overlap = len(set(claim_a.lower().split()) & set(claim_b.lower().split()))
        return overlap >= 3

    @staticmethod
    def _claims_contradict(claim_a: str, claim_b: str) -> bool:
        contradictions = {
            "not",
            "never",
            "no",
            "cannot",
            "doesn't",
            "don't",
            "won't",
            "isn't",
            "aren't",
        }
        words_a = set(claim_a.lower().split())
        words_b = set(claim_b.lower().split())
        return bool(words_a & contradictions) != bool(words_b & contradictions)
