"""Tests RetractionWatchCSVAdapter — spec 007 T062."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vigilancia_multiagente.infra.retraction.retraction_watch_csv import (
    RetractionWatchCSVAdapter,
)

_CSV_FIXTURE = """OriginalPaperDOI,RetractionDate,RetractionNature,Notes
10.1000/retracted1,2024-01-15,Fabrication,Fabricated data
10.1000/retracted2,2024-02-20,Plagiarism,Plagiarized content
10.1000/active,,
,,
10.1000/retracted3,2023-11-01,Unreliable,Data issues
10.1000/retracted4,2024-03-10,Fake Peer Review,Peer review manipulation
"""


def _mock_csv_response(csv_text: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = csv_text
    resp.raise_for_status.return_value = None
    return resp


@pytest.mark.asyncio
async def test_daily_sync_parses_csv() -> None:
    adapter = RetractionWatchCSVAdapter()
    adapter._csv_url = "https://example.com/retractions.csv"

    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_csv_response(_CSV_FIXTURE)

        new_count = await adapter.daily_sync()

    # 5 DOIs total: retracted1, retracted2, active, retracted3, retracted4
    # (the empty DOI line is skipped)
    assert new_count == 5
    assert len(adapter._cache) == 5
    await adapter.close()


@pytest.mark.asyncio
async def test_is_retracted_checks_cache() -> None:
    adapter = RetractionWatchCSVAdapter()
    adapter._csv_url = "https://example.com/retractions.csv"

    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_csv_response(_CSV_FIXTURE)

        await adapter.daily_sync()

    retracted = await adapter.is_retracted("10.1000/retracted1")
    assert retracted is not None
    assert retracted.source_doi == "10.1000/retracted1"
    assert "Fabrication" in retracted.reason

    not_retracted = await adapter.is_retracted("10.9999/nonexistent")
    assert not_retracted is None
    await adapter.close()


@pytest.mark.asyncio
async def test_doi_normalization() -> None:
    adapter = RetractionWatchCSVAdapter()
    adapter._csv_url = "https://example.com/retractions.csv"

    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_csv_response(_CSV_FIXTURE)

        await adapter.daily_sync()

    result = await adapter.is_retracted("https://doi.org/10.1000/retracted1")
    assert result is not None
    assert result.source_doi == "10.1000/retracted1"
    await adapter.close()


@pytest.mark.asyncio
async def test_sync_returns_zero_when_no_url() -> None:
    adapter = RetractionWatchCSVAdapter()
    adapter._csv_url = None

    count = await adapter.daily_sync()

    assert count == 0
    await adapter.close()
