"""Tests for mode_schema.py: parse_mode_yaml validation (spec 011 Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.modes.mode_schema import ModeSchemaError, parse_mode_yaml


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test_mode.yaml"
    p.write_text(content, encoding="utf-8")
    return p


class TestParseModeYaml:
    def test_valid_full_mode_parses(self, tmp_path: Path) -> None:
        yaml_content = """\
id: test-mode
display_name: "Test Mode"
description: "A test mode"
version: "1.0.0"
status: active
tools:
  domains: [search, web]
  excluded: [bad_tool]
playbooks:
  default: general
  allowed: [general]
company_geo:
  country: Colombia
  department: Santander
  municipality: Barrancabermeja
  timezone: America/Bogota
"""
        path = _write_yaml(tmp_path, yaml_content)
        mode = parse_mode_yaml(path)
        assert mode.id == "test-mode"
        assert mode.display_name == "Test Mode"
        assert mode.tools is not None
        assert mode.tools.domains == ["search", "web"]
        assert mode.company_geo is not None
        assert mode.company_geo.country == "Colombia"
        assert mode.company_geo.municipality == "Barrancabermeja"

    def test_missing_id_fails(self, tmp_path: Path) -> None:
        yaml_content = """\
display_name: "No ID"
version: "1.0.0"
description: "missing id"
"""
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(ModeSchemaError, match="missing required field 'id'"):
            parse_mode_yaml(path)

    def test_company_geo_without_country_fails(self, tmp_path: Path) -> None:
        yaml_content = """\
id: bad-geo
display_name: "Bad Geo"
description: "geo without country"
version: "1.0.0"
company_geo:
  department: Santander
"""
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(ModeSchemaError, match="company_geo requires 'country'"):
            parse_mode_yaml(path)

    def test_status_roadmap_parses(self, tmp_path: Path) -> None:
        yaml_content = """\
id: future-mode
display_name: "Future"
description: "roadmap mode"
version: "1.0.0"
status: roadmap
"""
        path = _write_yaml(tmp_path, yaml_content)
        mode = parse_mode_yaml(path)
        assert mode.status == "roadmap"

    def test_optional_fields_absent_no_error(self, tmp_path: Path) -> None:
        yaml_content = """\
id: minimal
display_name: "Minimal"
description: "minimal mode"
version: "1.0.0"
"""
        path = _write_yaml(tmp_path, yaml_content)
        mode = parse_mode_yaml(path)
        assert mode.tools is None
        assert mode.soul_overlay is None
        assert mode.company_geo is None

    def test_tools_domains_as_list_validates(self, tmp_path: Path) -> None:
        yaml_content = """\
id: domains-test
display_name: "Domains"
description: "test domains"
version: "1.0.0"
tools:
  domains:
    - search
    - web
    - analytics
"""
        path = _write_yaml(tmp_path, yaml_content)
        mode = parse_mode_yaml(path)
        assert mode.tools is not None
        assert mode.tools.domains == ["search", "web", "analytics"]
