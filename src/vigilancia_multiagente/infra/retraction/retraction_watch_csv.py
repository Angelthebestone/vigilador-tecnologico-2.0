"""RetractionWatchCSVAdapter — spec 007 T053.

Monitor de retractaciones via CSV de Retraction Watch.
Mantiene un cache en memoria con timestamp de ultima sincronizacion.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.evaluation_entities import RetractionRecord
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)

logger = logging.getLogger(__name__)


class RetractionWatchCSVAdapter:
    def __init__(
        self,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        settings = get_settings()
        self._csv_url = settings.retraction_watch_csv_url
        self._cache: dict[str, RetractionRecord] = {}
        self._last_sync: datetime | None = None
        self._client = httpx.AsyncClient(timeout=60.0)
        self._errors = errors_sink

    async def close(self) -> None:
        await self._client.aclose()

    async def is_retracted(self, doi: str) -> RetractionRecord | None:
        if self._last_sync is None:
            await self.daily_sync()
        return self._cache.get(_clean_doi(doi))

    async def daily_sync(self) -> int:
        if self._csv_url is None:
            logger.info("RETRACTION_WATCH_CSV_URL not configured; sync skipped")
            return 0
        try:
            response = await self._client.get(self._csv_url)
            response.raise_for_status()
            content = response.text
            reader = csv.DictReader(io.StringIO(content))
            new_count = 0
            for row in reader:
                doi = _clean_doi(row.get("OriginalPaperDOI") or row.get("doi") or "")
                if not doi:
                    continue
                if doi not in self._cache:
                    record = _row_to_retraction(row, doi)
                    self._cache[doi] = record
                    new_count += 1
            self._last_sync = datetime.now(UTC)
            logger.info("RetractionWatch sync: %d new records (cache=%d)", new_count, len(self._cache))
            return new_count
        except httpx.HTTPError as exc:
            logger.warning("RetractionWatch CSV download failed: %s", exc)
            self._record_error(exc)
            return 0

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_A,
                step_name="RetractionWatchCSVAdapter.daily_sync",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _clean_doi(raw: str) -> str:
    doi = raw.strip().lower()
    doi = doi.removeprefix("https://doi.org/").removeprefix("doi:")
    return doi.strip()


def _row_to_retraction(row: dict[str, Any], doi: str) -> RetractionRecord:
    raw_date = row.get("RetractionDate") or row.get("retraction_date") or ""
    retracted_at = datetime.now(UTC)
    if raw_date.strip():
        try:
            retracted_at = datetime.fromisoformat(raw_date.strip())
            if retracted_at.tzinfo is None:
                retracted_at = retracted_at.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            pass
    reason = row.get("RetractionNature") or row.get("reason") or row.get("Notes") or ""
    return RetractionRecord(
        source_doi=doi,
        retracted_at=retracted_at,
        reason=str(reason),
    )
