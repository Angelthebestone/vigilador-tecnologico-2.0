"""T127: Test OpenAlexIdeaLineageTracer.

Cadena de citas con circularidad. Mocks httpx para evitar llamadas reales.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from vigilancia_multiagente.domain.models import BranchType, SourceRef
from vigilancia_multiagente.infra.openalex.openalex_idea_lineage import (
    OpenAlexIdeaLineageTracer,
)


def _mock_response(data: dict) -> MagicMock:
    """Create a mock httpx response with sync .json() and .raise_for_status()."""
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def tracer():
    return OpenAlexIdeaLineageTracer(polite_mailto="test@test.com")


@pytest.fixture
def sources_with_dois():
    now = __import__("datetime").datetime.now()
    return [
        SourceRef(
            id=uuid4(),
            session_id=uuid4(),
            url="https://doi.org/10.1234/test.2024.001",
            provider="openalex",
            branch_type=BranchType.AVANCES,
            accessed_at=now,
            title="Seminal paper",
        ),
        SourceRef(
            id=uuid4(),
            session_id=uuid4(),
            url="https://doi.org/10.1234/test.2024.002",
            provider="openalex",
            branch_type=BranchType.AVANCES,
            accessed_at=now,
            title="Follow-up paper",
        ),
    ]


@pytest.mark.asyncio
async def test_trace_lineage_with_mock(tracer, sources_with_dois):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_instance

        async def mock_get(url, **kwargs):
            if "10.1234/test.2024.001" in str(url):
                return _mock_response({
                    "id": "https://openalex.org/W001",
                    "title": "Seminal paper",
                    "display_name": "Seminal paper",
                    "referenced_works": ["https://doi.org/10.1234/test.2024.000"],
                })
            elif "10.1234/test.2024.002" in str(url):
                return _mock_response({
                    "id": "https://openalex.org/W002",
                    "title": "Follow-up paper",
                    "display_name": "Follow-up paper",
                    "referenced_works": [
                        "https://doi.org/10.1234/test.2024.001",
                        "https://doi.org/10.1234/test.2024.003",
                    ],
                })
            else:
                return _mock_response({
                    "id": "https://openalex.org/W000",
                    "title": "Root paper",
                    "display_name": "Root paper",
                    "referenced_works": [],
                })

        mock_instance.get = mock_get

        lineage = await tracer.trace("AI for bio", sources_with_dois)
        assert lineage.idea == "AI for bio"
        assert len(lineage.citation_chain) > 0
        assert isinstance(lineage.seminal_publication_id, type(uuid4()))


@pytest.mark.asyncio
async def test_trace_with_circularity(tracer, sources_with_dois):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_instance

        async def mock_get(url, **kwargs):
            if "10.1234/test.2024.001" in str(url):
                return _mock_response({
                    "id": "https://openalex.org/W001",
                    "title": "Paper A",
                    "referenced_works": ["https://doi.org/10.1234/test.2024.002"],
                })
            else:
                return _mock_response({
                    "id": "https://openalex.org/W002",
                    "title": "Paper B",
                    "referenced_works": ["https://doi.org/10.1234/test.2024.001"],
                })

        mock_instance.get = mock_get

        lineage = await tracer.trace("Circular idea", sources_with_dois)
        assert lineage.circularity_detected
