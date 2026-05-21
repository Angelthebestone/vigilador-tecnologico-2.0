"""OpenAlexAuthorReputationGateway — spec 007 T050.

Consulta reputacion de autores via OpenAlex Authors API con polite pool
(cuando VT_OPENALEX_EMAIL esta configurado). Fallo -> None + StepError.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.evaluation_entities import (
    AffiliationType,
    AuthorReputation,
)
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)

logger = logging.getLogger(__name__)

_AUTHORS_BASE_URL = "https://api.openalex.org/authors"


class OpenAlexAuthorReputationGateway:
    def __init__(
        self,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(timeout=20.0)
        self._mailto = settings.openalex_email
        self._errors = errors_sink

    async def close(self) -> None:
        await self._client.aclose()

    async def lookup(self, author_id: str) -> AuthorReputation | None:
        url = f"{_AUTHORS_BASE_URL}/{author_id}"
        params: dict[str, str | int] = {}
        if self._mailto:
            params["mailto"] = self._mailto
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return _parse_author(data, author_id)
        except httpx.HTTPError as exc:
            self._record_error(exc, context={"author_id": author_id, "action": "lookup"})
            return None

    async def search_by_name(self, name: str, limit: int = 5) -> list[AuthorReputation]:
        params: dict[str, str | int] = {"search": name, "per-page": min(limit, 50)}
        if self._mailto:
            params["mailto"] = self._mailto
        try:
            response = await self._client.get(_AUTHORS_BASE_URL, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            results = data.get("results", [])
            return [_parse_author(item, str(item.get("id", ""))) for item in results[:limit]]
        except httpx.HTTPError as exc:
            self._record_error(exc, context={"name": name, "action": "search"})
            return []

    async def refresh(self, author_id: str) -> AuthorReputation:
        result = await self.lookup(author_id)
        if result is None:
            return AuthorReputation(
                author_id=author_id,
                display_name="",
                h_index=0,
                total_citations=0,
                retraction_count=0,
                primary_affiliation=None,
                affiliation_type=AffiliationType.INDEPENDENT,
                last_refreshed=datetime.now(UTC),
            )
        return result

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_A,
                step_name="OpenAlexAuthorReputationGateway",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _parse_author(data: dict[str, Any], author_id: str) -> AuthorReputation:
    display_name = str(data.get("display_name", data.get("name", "")))
    h_index = int(data.get("summary_stats", {}).get("h_index", 0))
    total_citations = int(data.get("cited_by_count", 0))
    affiliations = data.get("last_known_institutions", []) or data.get("affiliations", [])
    primary_affiliation: str | None = None
    affiliation_type = AffiliationType.INDEPENDENT
    if affiliations:
        inst = affiliations[0]
        if isinstance(inst, dict):
            primary_affiliation = str(inst.get("display_name") or inst.get("name", ""))
            ror = inst.get("ror")
            if ror:
                affiliation_type = _infer_affiliation_type(ror)
    domain_weights: dict[str, float] = {}
    concepts = data.get("concepts", [])
    for c in concepts[:8]:
        name = c.get("display_name") or c.get("name", "")
        score = float(c.get("score", 0))
        if name:
            domain_weights[name] = score
    return AuthorReputation(
        author_id=author_id,
        display_name=display_name,
        h_index=h_index,
        total_citations=total_citations,
        retraction_count=0,
        primary_affiliation=primary_affiliation,
        affiliation_type=affiliation_type,
        domain_weights=domain_weights,
        last_refreshed=datetime.now(UTC),
    )


def _infer_affiliation_type(ror: str) -> AffiliationType:
    ror_lower = ror.lower()
    if any(edu in ror_lower for edu in (".edu", "education", "university", "college")):
        return AffiliationType.ACADEMIC
    if any(gov in ror_lower for gov in (".gov", "government", "ministry")):
        return AffiliationType.GOVERNMENT
    if any(corp in ror_lower for corp in (".com", "corp", "inc.", "ltd", "gmbh")):
        return AffiliationType.INDUSTRY
    return AffiliationType.INDEPENDENT
