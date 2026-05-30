"""Tests for enterprise config_loader: valid YAML, malformed, schema mismatch."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from vigilancia_multiagente.enterprise.config_loader import ConfigLoadError, load_yaml_config


class _SampleSchema(BaseModel):
    id: str
    name: str
    count: int


class TestLoadYamlConfig:
    def test_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "valid.yaml"
        f.write_text("id: x\nname: hello\ncount: 5\n", encoding="utf-8")
        result = load_yaml_config(f, _SampleSchema)
        assert result.id == "x"
        assert result.name == "hello"
        assert result.count == 5

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigLoadError, match="file not found"):
            load_yaml_config(tmp_path / "nope.yaml", _SampleSchema)

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  - [invalid\n", encoding="utf-8")
        with pytest.raises(ConfigLoadError, match="malformed YAML"):
            load_yaml_config(f, _SampleSchema)

    def test_schema_mismatch_missing_field(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.yaml"
        f.write_text("id: x\nname: hello\n", encoding="utf-8")
        with pytest.raises(ConfigLoadError, match="count"):
            load_yaml_config(f, _SampleSchema)

    def test_schema_mismatch_wrong_type(self, tmp_path: Path) -> None:
        f = tmp_path / "wrong.yaml"
        f.write_text("id: x\nname: hello\ncount: not_a_number\n", encoding="utf-8")
        with pytest.raises(ConfigLoadError, match="schema validation failed"):
            load_yaml_config(f, _SampleSchema)

    def test_non_mapping_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ConfigLoadError, match="expected a YAML mapping"):
            load_yaml_config(f, _SampleSchema)
