"""Tests for SystemBaseLoader."""

from pathlib import Path

import pytest

from vigilancia_multiagente.application.governance.system_base_loader import (
    SystemBaseLoadError,
    SystemBaseLoader,
)


def _minimal_system_base_md(version: str = "1.0.0") -> str:
    return f"""---
version: {version}
---

# System Base

## Global Rules (Tool Usage)

1. Each agent executes tools in order defined by agent-governance.md.
2. Tool fallback to next tool on failure.

- **tool_order**: sequential

## Safety Limits

- **max_depth**: 5

## Error Handling

1. Retry on failure.
2. Fail explicitly.

## Output Style

1. JSON format.

## Model Behavior

- **temperature**: 0.3

## Embedding Configuration (Activo)

- **dimensions**: 768"""


@pytest.fixture
def contracts_root(tmp_path: Path) -> Path:
    root = tmp_path / "contracts"
    root.mkdir()
    return root


def test_load_empty_file_raises_error(contracts_root: Path) -> None:
    """An empty system base file should raise an error."""
    path = contracts_root / "system-base.md"
    path.write_text("", encoding="utf-8")

    loader = SystemBaseLoader(contracts_root)
    with pytest.raises(SystemBaseLoadError, match="missing required section"):
        loader.load()


def test_load_minimal_valid_file(contracts_root: Path) -> None:
    """A valid minimal system base should load successfully."""
    path = contracts_root / "system-base.md"
    path.write_text(_minimal_system_base_md(), encoding="utf-8")

    loader = SystemBaseLoader(contracts_root)
    system_base = loader.load()

    assert system_base.version == "1.0.0"
    assert len(system_base.global_rules) == 3  # 2 numbered rules + 1 key-value line
    assert len(system_base.safety_limits) >= 1
    assert "max_depth" in system_base.safety_limits


def test_load_missing_file_raises_error(contracts_root: Path) -> None:
    """Missing system base file should raise an error."""
    loader = SystemBaseLoader(contracts_root)
    with pytest.raises(SystemBaseLoadError, match="not found"):
        loader.load()


def test_resolve_path(contracts_root: Path) -> None:
    """resolve_path returns the correct absolute path."""
    loader = SystemBaseLoader(contracts_root)
    expected = contracts_root / "system-base.md"
    assert loader.resolve_path() == expected


def test_version_parsing(contracts_root: Path) -> None:
    """The version from YAML frontmatter is correctly parsed."""
    path = contracts_root / "system-base.md"
    path.write_text(_minimal_system_base_md(version="2.1.0"), encoding="utf-8")

    loader = SystemBaseLoader(contracts_root)
    system_base = loader.load()
    assert system_base.version == "2.1.0"


def test_missing_frontmatter_defaults_to_0_0_0(contracts_root: Path) -> None:
    """A file without YAML frontmatter should default to 0.0.0."""
    path = contracts_root / "system-base.md"
    content = _minimal_system_base_md()
    # Remove frontmatter
    lines = content.splitlines()
    if lines and lines[0] == "---":
        end = next((i for i, l in enumerate(lines[1:], 1) if l == "---"), None)
        if end is not None:
            lines = lines[end + 1 :]
    path.write_text("\n".join(lines), encoding="utf-8")

    loader = SystemBaseLoader(contracts_root)
    system_base = loader.load()
    assert system_base.version == "0.0.0"


def test_embedding_config_parsing(contracts_root: Path) -> None:
    """Embedding configuration values are correctly typed."""
    path = contracts_root / "system-base.md"
    path.write_text(_minimal_system_base_md(), encoding="utf-8")

    loader = SystemBaseLoader(contracts_root)
    system_base = loader.load()
    assert system_base.embedding_config.get("dimensions") == 768
