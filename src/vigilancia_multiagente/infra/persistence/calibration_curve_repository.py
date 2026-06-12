"""PostgresCalibrationCurveRepository — spec 007 T020.

Persiste curvas de calibracion isotonica y permite activar una version unica
(`is_active`). El indice parcial `calibration_curve_one_active_idx` garantiza
que solo exista una curva activa simultaneamente.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text

from vigilancia_multiagente.domain.evaluation_entities import CalibrationCurve
from vigilancia_multiagente.infra.db.connection import Database


class PostgresCalibrationCurveRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def save(self, curve: CalibrationCurve) -> None:
        async with self._database.session() as db:
            await db.execute(
                text(
                    "INSERT INTO calibration_curve"
                    " (id, model_version, created_at, samples_count, mappings,"
                    "  is_active) VALUES (:id, :model_version, :created_at,"
                    "  :samples_count, CAST(:mappings AS JSONB), FALSE)"
                    " ON CONFLICT (model_version) DO NOTHING"
                ),
                {
                    "id": str(curve.id),
                    "model_version": curve.model_version,
                    "created_at": curve.created_at,
                    "samples_count": curve.samples_count,
                    "mappings": json.dumps(curve.mappings),
                },
            )
            await db.commit()

    async def activate(self, model_version: str) -> None:
        """Solo una curva queda is_active=TRUE; el indice parcial unico garantiza la invariante."""
        async with self._database.session() as db:
            await db.execute(text("UPDATE calibration_curve SET is_active = FALSE"))
            await db.execute(
                text(
                    "UPDATE calibration_curve SET is_active = TRUE"
                    " WHERE model_version = :model_version"
                ),
                {"model_version": model_version},
            )
            await db.commit()

    async def active(self) -> CalibrationCurve | None:
        async with self._database.session() as db:
            result = await db.execute(
                text(
                    "SELECT id, model_version, created_at, samples_count, mappings"
                    " FROM calibration_curve WHERE is_active = TRUE LIMIT 1"
                )
            )
            row = result.first()
            return _row_to_curve(tuple(row)) if row else None


def _row_to_curve(row: tuple[object, ...]) -> CalibrationCurve:
    raw_mappings = row[4]
    mappings_data = (
        raw_mappings
        if isinstance(raw_mappings, list)
        else json.loads(str(raw_mappings) if raw_mappings else "[]")
    )
    return CalibrationCurve(
        id=UUID(str(row[0])),
        model_version=str(row[1]),
        created_at=cast(datetime, row[2]),
        samples_count=int(cast(int, row[3])),
        mappings=[
            (float(item[0]), float(item[1])) for item in cast(list[list[float]], mappings_data)
        ],
    )
