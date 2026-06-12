"""Tests OpenAlexAuthorReputationGateway — spec 007 T061."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from vigilancia_multiagente.infra.openalex.openalex_author_gateway import (
    OpenAlexAuthorReputationGateway,
)


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def mock_author_response() -> dict:
    return {
        "id": "https://openalex.org/A123456789",
        "display_name": "Jane Test Author",
        "cited_by_count": 1500,
        "summary_stats": {"h_index": 28, "i10_index": 40},
        "last_known_institutions": [{"display_name": "MIT", "ror": "https://ror.org/03yrm5c26"}],
        "concepts": [
            {"display_name": "Artificial Intelligence", "score": 0.95},
            {"display_name": "Machine Learning", "score": 0.88},
        ],
    }


@pytest.mark.asyncio
async def test_lookup_returns_author_reputation(mock_author_response: dict) -> None:
    gateway = OpenAlexAuthorReputationGateway()

    with patch.object(gateway._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(json_data=mock_author_response)

        result = await gateway.lookup("A123456789")

    assert result is not None
    assert result.display_name == "Jane Test Author"
    assert result.h_index == 28
    assert result.total_citations == 1500
    assert result.primary_affiliation == "MIT"
    assert "Artificial Intelligence" in result.domain_weights
    await gateway.close()


@pytest.mark.asyncio
async def test_lookup_returns_none_on_http_error() -> None:
    gateway = OpenAlexAuthorReputationGateway()

    with patch.object(gateway._client, "get", new_callable=AsyncMock) as mock_get:
        err_resp = _mock_response(status_code=404)
        err_resp.raise_for_status.side_effect = httpx.HTTPError("HTTP 404")
        mock_get.return_value = err_resp

        result = await gateway.lookup("A999999")

    assert result is None
    await gateway.close()


@pytest.mark.asyncio
async def test_search_by_name_returns_list() -> None:
    gateway = OpenAlexAuthorReputationGateway()

    with patch.object(gateway._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(
            json_data={
                "results": [
                    {
                        "id": "https://openalex.org/A1",
                        "display_name": "Author One",
                        "cited_by_count": 500,
                        "summary_stats": {"h_index": 15},
                        "concepts": [],
                    }
                ]
            }
        )

        results = await gateway.search_by_name("Author One")

    assert len(results) == 1
    assert results[0].display_name == "Author One"
    await gateway.close()


@pytest.mark.asyncio
async def test_search_by_name_returns_empty_on_error() -> None:
    gateway = OpenAlexAuthorReputationGateway()

    with patch.object(gateway._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        results = await gateway.search_by_name("Unknown")

    assert results == []
    await gateway.close()
