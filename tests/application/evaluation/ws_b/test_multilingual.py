"""T088 — Pruebas de LlmMultilingualNormalizer.

SC-B04: distribucion correcta de 3 idiomas, traduccion deterministica con mock.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.ws_b.llm_multilingual import (
    LlmMultilingualNormalizer,
)
from vigilancia_multiagente.domain.models import BranchType, SourceRef

pytestmark = pytest.mark.asyncio


class MockLLMClient:
    def __init__(self) -> None:
        self.complete = AsyncMock()

    def set_response(self, content: str) -> None:
        self.complete.return_value = {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def llm_client() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def normalizer(llm_client) -> LlmMultilingualNormalizer:
    return LlmMultilingualNormalizer(llm_client)


async def test_detect_language(normalizer, llm_client):
    llm_client.set_response('{"language": "es", "confidence": 0.95}')
    lang = await normalizer.detect_language("Hola mundo")
    assert lang == "es"


async def test_detect_language_fallback(normalizer, llm_client):
    llm_client.complete.side_effect = Exception("LLM failed")
    lang = await normalizer.detect_language("Hello world")
    assert lang == "en"


async def test_translate(normalizer, llm_client):
    llm_client.set_response('{"translated": "Hello world"}')
    translated = await normalizer.translate("Hola mundo", target="en")
    assert translated == "Hello world"


async def test_translate_fallback(normalizer, llm_client):
    llm_client.complete.side_effect = Exception("LLM failed")
    translated = await normalizer.translate("Hola mundo")
    assert translated == "Hola mundo"


async def test_language_distribution(normalizer, llm_client):
    session_id = uuid4()
    sources = [
        SourceRef(
            id=uuid4(),
            session_id=session_id,
            url=f"https://example{i}.com",
            provider="tavily",
            branch_type=BranchType.AVANCES,
            accessed_at=datetime.now(UTC),
            title="Hola" if i < 2 else "Hello" if i < 4 else "Bonjour",
        )
        for i in range(6)
    ]

    async def fake_detect(text: str) -> str:
        if text == "Hola":
            return "es"
        if text == "Hello":
            return "en"
        return "fr"

    normalizer.detect_language = fake_detect  # type: ignore[assignment]
    dist = await normalizer.language_distribution(sources)
    assert abs(dist.get("es", 0) - 2 / 6) < 0.01
    assert abs(dist.get("en", 0) - 2 / 6) < 0.01
    assert abs(dist.get("fr", 0) - 2 / 6) < 0.01
