"""Tests GithubBasedReproducibilityChecker — spec 007 T064."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_a.github_reproducibility_checker import (
    GithubBasedReproducibilityChecker,
)
from vigilancia_multiagente.domain.models import Finding


def _make_finding(statement: str = "", tags: list[str] | None = None) -> Finding:
    return Finding(
        id=uuid4(),
        topic="Test topic",
        statement=statement,
        confidence=0.8,
        source_ids=[],
        tags=tags or [],
    )


@pytest.mark.asyncio
async def test_no_github_url_returns_zero() -> None:
    checker = GithubBasedReproducibilityChecker()
    finding = _make_finding(statement="This is a regular paper without repos")

    score = await checker.score(finding)

    assert score.has_public_repo is False
    assert score.score == 0.0
    await checker.close()


@pytest.mark.asyncio
async def test_repo_exists_with_all_features() -> None:
    checker = GithubBasedReproducibilityChecker()
    finding = _make_finding(
        statement="Our code is at https://github.com/user/repo",
        tags=["Dockerfile", "data/"],
    )

    with (
        patch.object(checker._client, "get", new_callable=AsyncMock) as mock_get,
    ):
        async def mock_response(url: str, **kwargs):
            del kwargs
            resp = AsyncMock()
            if "repos/user/repo" in url and "/contents/" not in url:
                resp.status_code = 200
                resp.json.return_value = {"name": "repo"}
            elif "/contents/" in url and "data" not in url and "Dockerfile" not in url:
                resp.status_code = 404
            elif "/contents/data/" in url or "dataset" in url:
                resp.status_code = 200
                resp.json.return_value = []
            elif "Dockerfile" in url or "environment" in url or "/readme" in url:
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        mock_get.side_effect = mock_response

        score = await checker.score(finding)

    assert score.has_public_repo is True
    assert score.score > 0.0
    await checker.close()


@pytest.mark.asyncio
async def test_repo_exists_but_no_env() -> None:
    checker = GithubBasedReproducibilityChecker()
    finding = _make_finding(
        statement="Code at https://github.com/user/minimal"
    )

    with patch.object(checker._client, "get", new_callable=AsyncMock) as mock_get:
        async def mock_response(url: str, **kwargs):
            del kwargs
            resp = AsyncMock()
            resp.status_code = 200
            resp.json.return_value = {"name": "minimal"}
            # Only the repo check URL returns 200; all others (contents, readme) return 404
            if url.rstrip("/") == "https://api.github.com/repos/user/minimal":
                resp.status_code = 200
                resp.json.return_value = {"name": "minimal"}
            elif "contents" in url or "readme" in url:
                resp.status_code = 404
            return resp

        mock_get.side_effect = mock_response

        score = await checker.score(finding)

    assert score.has_public_repo is True
    assert score.score == 0.4
    await checker.close()


@pytest.mark.asyncio
async def test_repo_not_found() -> None:
    checker = GithubBasedReproducibilityChecker()
    finding = _make_finding(
        statement="https://github.com/ghost/deleted-repo"
    )

    with patch.object(checker._client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        score = await checker.score(finding)

    assert score.has_public_repo is False
    assert score.score == 0.0
    await checker.close()
