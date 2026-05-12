from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable
from uuid import UUID, uuid4


@dataclass(slots=True)
class IterationResult:
    id: UUID
    branch_type: str
    iteration_index: int
    query: str
    query_type: str
    needs_follow_up: bool
    next_query: str | None
    stop_reason: str | None
    started_at: datetime
    completed_at: datetime


ExecutionFn = Callable[[str, int], Awaitable[tuple[bool, str | None]]]


async def run_followup_loop(
    branch_type: str,
    seed_query: str,
    depth_limit: int,
    execute: ExecutionFn,
) -> list[IterationResult]:
    if depth_limit < 1:
        raise ValueError("depth_limit must be >= 1")
    results: list[IterationResult] = []
    current_query = seed_query
    for index in range(1, depth_limit + 1):
        started_at = datetime.now(UTC)
        needs_follow_up, next_query = await execute(current_query, index)
        completed_at = datetime.now(UTC)
        stop_reason = None
        if not needs_follow_up:
            stop_reason = "NO_FOLLOW_UP"
        elif index == depth_limit:
            stop_reason = "DEPTH_LIMIT"
        results.append(
            IterationResult(
                id=uuid4(),
                branch_type=branch_type,
                iteration_index=index,
                query=current_query,
                query_type="SEED" if index == 1 else "FOLLOW_UP",
                needs_follow_up=needs_follow_up,
                next_query=next_query,
                stop_reason=stop_reason,
                started_at=started_at,
                completed_at=completed_at,
            )
        )
        if stop_reason is not None:
            break
        current_query = next_query or current_query
    return results

