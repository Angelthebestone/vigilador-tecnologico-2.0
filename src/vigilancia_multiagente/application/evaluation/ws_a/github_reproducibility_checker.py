"""GithubBasedReproducibilityChecker — spec 007 T054.

Inspecciona URLs en un Finding para detectar repositorios publicos,
datos abiertos y entornos reproducibles (Dockerfile, .nix, environment.yml).
"""

from __future__ import annotations

import logging
import re

import httpx

from vigilancia_multiagente.domain.evaluation_entities import ReproducibilityScore
from vigilancia_multiagente.domain.models import Finding
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
)

logger = logging.getLogger(__name__)

_GITHUB_URL_RE = re.compile(r"https?://github\.com/[^/\s]+/[^/\s]+")
_README_FILES = ("README.md", "README.rst", "README.txt")
_REPRO_DOCKER = ("Dockerfile", "docker-compose.yml", "Dockerfile.*")
_REPRO_NIX = ("shell.nix", "default.nix", "flake.nix")
_REPRO_CONDA = ("environment.yml", "environment.yaml", "requirements.txt")


class GithubBasedReproducibilityChecker:
    def __init__(
        self,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)
        self._errors = errors_sink

    async def close(self) -> None:
        await self._client.aclose()

    async def score(self, finding: Finding) -> ReproducibilityScore:
        github_urls = _extract_github_urls(finding)
        if not github_urls:
            return ReproducibilityScore(
                finding_id=finding.id,
                has_public_repo=False,
                has_open_data=False,
                has_reproducible_env=False,
                score=0.0,
            )
        repo_url = github_urls[0].rstrip("/")
        api_repo_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/")
        has_repo = await self._check_repo_exists(api_repo_url)
        if not has_repo:
            return ReproducibilityScore(
                finding_id=finding.id,
                has_public_repo=False,
                has_open_data=False,
                has_reproducible_env=False,
                score=0.0,
            )
        has_open_data = await self._check_open_data(api_repo_url)
        has_repro_env = await self._check_reproducible_env(api_repo_url, repo_url)
        score = _compute_score(has_repo, has_open_data, has_repro_env)
        return ReproducibilityScore(
            finding_id=finding.id,
            has_public_repo=has_repo,
            has_open_data=has_open_data,
            has_reproducible_env=has_repro_env,
            score=score,
        )

    async def _check_repo_exists(self, api_url: str) -> bool:
        try:
            response = await self._client.get(api_url)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def _check_open_data(self, api_url: str) -> bool:
        data_patterns = ("data/", "dataset", "datasets")
        try:
            response = await self._client.get(f"{api_url}/contents/")
            if response.status_code != 200:
                return False
            items = response.json()
            if isinstance(items, list):
                for item in items:
                    name = (item.get("name") or "").lower()
                    if any(p in name for p in data_patterns):
                        return True
            return False
        except (httpx.HTTPError, ValueError):
            return False

    async def _check_reproducible_env(self, api_url: str, raw_url: str) -> bool:
        patterns = _REPRO_DOCKER + _REPRO_NIX + _REPRO_CONDA
        for filename in patterns:
            try:
                resp = await self._client.get(f"{api_url}/contents/{filename}")
                if resp.status_code == 200:
                    return True
            except httpx.HTTPError:
                continue
        if _README_FILES:
            try:
                resp = await self._client.get(f"{api_url}/readme")
                if resp.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
        return False


def _extract_github_urls(finding: Finding) -> list[str]:
    urls: set[str] = set()
    for source_id in finding.source_ids:
        urls.add(str(source_id))
    for tag in finding.tags:
        for match in _GITHUB_URL_RE.findall(tag):
            urls.add(match)
    for match in _GITHUB_URL_RE.findall(finding.statement):
        urls.add(match)
    return sorted(urls)


def _compute_score(has_repo: bool, has_data: bool, has_env: bool) -> float:
    if not has_repo:
        return 0.0
    score = 0.4
    if has_data:
        score += 0.3
    if has_env:
        score += 0.3
    return round(score, 2)
