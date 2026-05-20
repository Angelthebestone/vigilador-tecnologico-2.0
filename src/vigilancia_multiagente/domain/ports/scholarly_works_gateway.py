"""Bibliographic / scholarly works gateway port.

Abstracts access to bibliometric databases (OpenAlex, Crossref, etc.) that
return structured data — citations, institutions, year, concepts — that web
scraping cannot reliably extract.
"""

from __future__ import annotations

from typing import Protocol, TypedDict


class ScholarlyWork(TypedDict):
    title: str
    year: int | None
    citations: int
    doi: str | None
    institutions: list[str]
    concepts: list[str]


class ScholarlyWorksGateway(Protocol):
    """Search a bibliographic database for scholarly works on a topic.

    Resilient by contract: returns ``[]`` on network/upstream error rather
    than raising — branch agents must not break when bibliometric data is
    unavailable.
    """

    async def search(self, query: str, limit: int = 10) -> list[ScholarlyWork]: ...
