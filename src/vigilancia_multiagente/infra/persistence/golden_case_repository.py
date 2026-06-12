"""PostgresGoldenCaseRepository — spec 007 T019.

Persiste golden cases (tabla `golden_case`) y sus ejecuciones historicas
(`golden_case_run`). Sirve a `GoldenCaseRunner` (WS-E) y al calibrador
isotonico que entrena con los deltas de cada run.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.domain.evaluation_entities import (
    ExpectedFinding,
    GoldenCase,
    GoldenCasePriority,
    GoldenCaseRun,
)
from vigilancia_multiagente.infra.db.connection import Database


class PostgresGoldenCaseRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_active(self) -> list[GoldenCase]:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT id, name, description, seed_query, expected_findings,"
                    " expected_confidence, priority FROM golden_case"
                    " WHERE is_active = TRUE ORDER BY priority, name"
                )
            )
            return [_row_to_case(tuple(row)) for row in result.fetchall()]

    async def record_run(self, run: GoldenCaseRun) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO golden_case_run"
                    " (id, case_id, run_at, success, actual_confidence,"
                    "  delta_vs_expected, failure_details)"
                    " VALUES (:id, :case_id, :run_at, :success,"
                    "         :actual_confidence, :delta, :failure_details)"
                ),
                {
                    "id": str(run.id),
                    "case_id": str(run.case_id),
                    "run_at": run.run_at,
                    "success": run.success,
                    "actual_confidence": run.actual_confidence,
                    "delta": run.delta_vs_expected,
                    "failure_details": run.failure_details,
                },
            )
            await db.commit()

    async def recent_runs(self, case_id: UUID, limit: int = 20) -> list[GoldenCaseRun]:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT id, case_id, run_at, success, actual_confidence,"
                    " delta_vs_expected, failure_details FROM golden_case_run"
                    " WHERE case_id = :case_id ORDER BY run_at DESC LIMIT :limit"
                ),
                {"case_id": str(case_id), "limit": limit},
            )
            return [_row_to_run(tuple(row)) for row in result.fetchall()]


def _row_to_case(row: tuple[object, ...]) -> GoldenCase:
    raw_findings = row[4]
    findings_data = (
        raw_findings
        if isinstance(raw_findings, list)
        else json.loads(str(raw_findings) if raw_findings else "[]")
    )
    return GoldenCase(
        id=UUID(str(row[0])),
        name=str(row[1]),
        description=str(row[2] or ""),
        seed_query=str(row[3]),
        expected_findings=[
            ExpectedFinding(
                topic=str(item.get("topic", "")),
                statement=str(item.get("statement", "")),
                confidence_min=float(cast(float, item.get("confidence_min", 0.0))),
                confidence_max=float(cast(float, item.get("confidence_max", 1.0))),
            )
            for item in cast(list[dict[str, object]], findings_data)
        ],
        expected_confidence=float(cast(float, row[5])),
        priority=GoldenCasePriority(str(row[6])),
    )


def _row_to_run(row: tuple[object, ...]) -> GoldenCaseRun:
    return GoldenCaseRun(
        id=UUID(str(row[0])),
        case_id=UUID(str(row[1])),
        run_at=cast(datetime, row[2]),
        success=bool(row[3]),
        actual_confidence=float(cast(float, row[4])),
        delta_vs_expected=float(cast(float, row[5])),
        failure_details=str(row[6]) if row[6] is not None else None,
    )
