"""T087 — Pruebas de PydanticExtractionSchemaRegistry.

SC-B03: respuesta MCP malformada -> ValidationError.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from vigilancia_multiagente.application.evaluation.ws_b.pydantic_schema_registry import (
    PydanticExtractionSchemaRegistry,
)
from vigilancia_multiagente.domain.evaluation_entities import ExtractionSchema, SourceType


@pytest.fixture
def registry() -> PydanticExtractionSchemaRegistry:
    reg = PydanticExtractionSchemaRegistry()

    class NewsSchema(BaseModel):
        title: str
        url: str
        content: str | None = None

    reg.register("news", "general", NewsSchema)
    return reg


def test_validate_valid_response(registry):
    schema = ExtractionSchema(
        source_type=SourceType.NEWS,
        domain="general",
        json_schema={"title": "NewsSchema", "type": "object"},
        version=1,
    )
    result = registry.validate({"title": "Test", "url": "https://example.com", "content": "Hello"}, schema)
    assert result["title"] == "Test"
    assert result["url"] == "https://example.com"


def test_validate_malformed_response_raises(registry):
    schema = ExtractionSchema(
        source_type=SourceType.NEWS,
        domain="general",
        json_schema={"title": "NewsSchema", "type": "object"},
        version=1,
    )
    with pytest.raises(ValidationError):
        registry.validate({"invalid": "data"}, schema)


def test_get_schema_unknown_key_raises(registry):
    with pytest.raises(KeyError):
        registry.get_schema("unknown", "domain")


def test_validate_empty_dict(registry):
    schema = ExtractionSchema(
        source_type=SourceType.NEWS,
        domain="general",
        json_schema={"title": "NewsSchema", "type": "object"},
        version=1,
    )
    with pytest.raises(ValidationError):
        registry.validate({}, schema)
