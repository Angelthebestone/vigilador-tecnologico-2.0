"""Adapter de linaje de ideas via OpenAlex API.

Implementa IdeaLineageTracer Protocol. Navega referenced_works de OpenAlex
hasta llegar a hojas y detecta circularidad via set membership.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

import httpx

from vigilancia_multiagente.domain.evaluation_entities import IdeaLineage
from vigilancia_multiagente.domain.models import SourceRef
from vigilancia_multiagente.domain.ports.idea_lineage import IdeaLineageTracer

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openalex.org/works"
_MAX_DEPTH = 5
_DEFAULT_TIMEOUT = 20.0


class OpenAlexIdeaLineageTracer(IdeaLineageTracer):
    """Navega citaciones OpenAlex para rastrear linaje de ideas."""

    def __init__(self, polite_mailto: str | None = None) -> None:
        self._mailto = polite_mailto

    async def trace(
        self,
        idea: str,
        sources: list[SourceRef],
    ) -> IdeaLineage:
        seed_dois = [
            s.url.replace("https://doi.org/", "")
            for s in sources
            if s.url and "doi.org" in s.url
        ]

        discovered: list[UUID] = []
        visited: set[str] = set()
        circular = False

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            to_visit: list[tuple[str, int]] = [
                (doi, 0) for doi in seed_dois[:3]
            ]

            while to_visit:
                doi, depth = to_visit.pop(0)
                if doi in visited:
                    circular = True
                    continue
                visited.add(doi)

                work_data = await self._fetch_work(client, doi)
                if work_data is None:
                    continue

                work_id = work_data.get("id", "")
                title = work_data.get("title") or work_data.get("display_name", "")
                if title:
                    found_id = uuid4()
                    discovered.append(found_id)

                if depth < _MAX_DEPTH:
                    refs = work_data.get("referenced_works", [])
                    for ref_url in refs:
                        if isinstance(ref_url, str):
                            ref_doi = ref_url.split("/")[-1] if "/" in ref_url else ref_url
                            if ref_doi not in visited:
                                to_visit.append((ref_doi, depth + 1))

        seminal = discovered[-1] if discovered else (seed_dois[0] if seed_dois else uuid4())
        if isinstance(seminal, str):
            seminal_uuid = uuid4()
        else:
            seminal_uuid = seminal

        return IdeaLineage(
            idea=idea,
            seminal_publication_id=seminal_uuid,
            citation_chain=discovered,
            circularity_detected=circular,
        )

    async def _fetch_work(
        self, client: httpx.AsyncClient, doi: str
    ) -> dict | None:
        try:
            params: dict[str, str] = {}
            if self._mailto:
                params["mailto"] = self._mailto
            url = f"{_BASE_URL}/doi:{doi}"
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("OpenAlex fetch failed for %s: %s", doi, exc)
            return None
