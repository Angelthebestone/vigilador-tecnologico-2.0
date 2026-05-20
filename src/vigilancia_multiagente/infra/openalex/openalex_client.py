"""OpenAlex REST client — datos bibliométricos duros (gratis, sin API key).

Todos los proveedores MCP del sistema son búsqueda web/scraping/papers que
devuelven texto. OpenAlex aporta datos *estructurados* que el scraping no da
de forma fiable: nº de citas, instituciones, año exacto, conceptos. Alimenta
el grafo de conocimiento, el TRL y el timeline causal con hechos en vez de
inferencias sobre texto.

API pública sin autenticación. Si `VT_OPENALEX_EMAIL` está configurado se
envía en `mailto` para entrar en el "polite pool" (más estable). Si hay
`VT_OPENALEX_API_KEY` (premium) se manda como `api_key` para límites altos.
Ambos son opcionales: sin ellos el cliente sigue funcionando.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.ports.scholarly_works_gateway import (
    ScholarlyWork as ScholarlyWorkDTO,
)

_BASE_URL = "https://api.openalex.org/works"


class OpenAlexError(Exception):
    """OpenAlex no responde o devuelve un error."""


@dataclass(slots=True, frozen=True)
class ScholarlyWork:
    title: str
    publication_year: int | None
    cited_by_count: int
    doi: str | None
    institutions: list[str]
    concepts: list[str]


class OpenAlexClient:
    """Cliente async; thread-safe vía httpx.AsyncClient."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(timeout=20.0)
        self._mailto = settings.openalex_email
        self._api_key = (
            settings.openalex_api_key.get_secret_value()
            if settings.openalex_api_key is not None
            else None
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_works(self, query: str, per_page: int = 10) -> list[ScholarlyWork]:
        """Busca trabajos académicos ordenados por nº de citas (impacto)."""
        params: dict[str, str | int] = {
            "search": query,
            "per-page": min(per_page, 50),
            "sort": "cited_by_count:desc",
        }
        if self._mailto:
            params["mailto"] = self._mailto
        if self._api_key:
            params["api_key"] = self._api_key
        try:
            response = await self._client.get(_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenAlexError(f"OpenAlex search failed: {exc}") from exc

        return [_parse_work(item) for item in data.get("results", [])]


class OpenAlexScholarlyWorksGateway:
    """Adapter implementing :class:`ScholarlyWorksGateway` against OpenAlex.

    Resilient: returns ``[]`` on OpenAlex errors so callers never break.
    """

    async def search(self, query: str, limit: int = 10) -> list[ScholarlyWorkDTO]:
        client = OpenAlexClient()
        try:
            works = await client.search_works(query, per_page=limit)
        except OpenAlexError:
            return []
        finally:
            await client.close()
        return [
            ScholarlyWorkDTO(
                title=w.title,
                year=w.publication_year,
                citations=w.cited_by_count,
                doi=w.doi,
                institutions=w.institutions,
                concepts=w.concepts,
            )
            for w in works
        ]


def _parse_work(item: dict) -> ScholarlyWork:
    institutions: list[str] = []
    for authorship in item.get("authorships", []):
        for inst in authorship.get("institutions", []):
            name = inst.get("display_name")
            if name and name not in institutions:
                institutions.append(name)
    concepts = [
        c["display_name"]
        for c in item.get("concepts", [])
        if c.get("display_name") and c.get("score", 0) >= 0.3
    ]
    return ScholarlyWork(
        title=item.get("title") or item.get("display_name") or "",
        publication_year=item.get("publication_year"),
        cited_by_count=int(item.get("cited_by_count", 0)),
        doi=item.get("doi"),
        institutions=institutions[:5],
        concepts=concepts[:8],
    )
