"""Generic YAML config loader with Pydantic validation and explicit errors."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ConfigLoadError(Exception):
    """Raised when YAML loading or schema validation fails."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"Config error in '{path}': {detail}")


def load_yaml_config(path: Path, schema: type[T]) -> T:
    """Load a YAML file and validate against a Pydantic model.

    Raises ConfigLoadError with path and field context on failure.
    """
    if not path.exists():
        raise ConfigLoadError(path, "file not found")

    raw_text = path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigLoadError(path, f"malformed YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigLoadError(path, "expected a YAML mapping at top level")

    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        fields = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigLoadError(path, f"schema validation failed — {fields}") from exc
