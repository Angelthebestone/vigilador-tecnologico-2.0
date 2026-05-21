"""PydanticExtractionSchemaRegistry — spec 007 T072.

Implementa ExtractionSchemaRegistry con schemas Pydantic por (source_type, domain).
"""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import BaseModel, ValidationError, create_model

from vigilancia_multiagente.domain.evaluation_entities import ExtractionSchema, SourceType
from vigilancia_multiagente.domain.ports.extraction_schema import ExtractionSchemaRegistry


class PydanticExtractionSchemaRegistry:
    def __init__(self) -> None:
        self._models: dict[tuple[str, str], type[BaseModel]] = {}

    def register(
        self, source_type: str, domain: str, schema: type[BaseModel]
    ) -> None:
        self._models[(source_type, domain)] = schema

    def register_from_extraction_schema(
        self, extraction_schema: ExtractionSchema
    ) -> None:
        key = (extraction_schema.source_type.value, extraction_schema.domain)
        json_schema = extraction_schema.json_schema
        model = _build_model_from_json_schema(json_schema)
        self._models[key] = model

    def get_schema(self, source_type: str, domain: str) -> ExtractionSchema:
        key = (source_type, domain)
        if key not in self._models:
            raise KeyError(f"No schema registered for source_type={source_type!r} domain={domain!r}")
        model = self._models[key]
        schema_dict = model.model_json_schema()
        return ExtractionSchema(
            source_type=SourceType(source_type),
            domain=domain,
            json_schema=cast(dict[str, object], schema_dict),
            version=1,
        )

    def validate(
        self, raw: dict[str, object], schema: ExtractionSchema
    ) -> dict[str, object]:
        key = (schema.source_type.value, schema.domain)
        model = self._models.get(key)
        if model is None:
            model = _build_model_from_json_schema(schema.json_schema)
            self._models[key] = model

        try:
            instance = model.model_validate(raw)
            result: dict[str, object] = instance.model_dump()
            return result
        except ValidationError:
            raise


def _build_model_from_json_schema(
    schema_dict: dict[str, object]
) -> type[BaseModel]:
    if "title" in schema_dict and "type" in schema_dict:
        return _json_schema_to_pydantic(schema_dict)
    return _dynamic_model_from_dict(schema_dict)


def _json_schema_to_pydantic(schema: dict[str, object]) -> type[BaseModel]:
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        fields: dict[str, tuple[type, Any]] = {}
        for field_name, prop in properties.items():
            if isinstance(prop, dict):
                field_type = _json_type_to_python(prop.get("type", "string"))
                fields[field_name] = (field_type, ...)
        model_name = str(schema.get("title", "DynamicModel"))
        return create_model(model_name, **fields)  # type: ignore[call-overload]
    return BaseModel


def _dynamic_model_from_dict(
    schema: dict[str, object]
) -> type[BaseModel]:
    fields: dict[str, tuple[type, Any]] = {}
    for field_name, prop in schema.items():
        if isinstance(prop, dict):
            ft = _json_type_to_python(prop.get("type", "string"))
            fields[field_name] = (ft, ...)
        else:
            fields[field_name] = (type(prop), prop)
    return create_model("DynamicModel", **fields)  # type: ignore[call-overload]


def _json_type_to_python(json_type: object) -> type:
    mapping: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    return mapping.get(str(json_type), str)
