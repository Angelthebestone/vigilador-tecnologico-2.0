"""Tests for claude_local_adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.claude_local_adapter import (
    ClaudeLocalAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import SkillSource


def _make_skill_dir(base: Path, name: str, content: str) -> None:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")


_VALID_SKILL = """\
---
name: "test-skill"
description: "A test skill"
---

## Procedure

Do something.
"""

_SANDBOX_SKILL = """\
---
name: "sandbox-skill"
description: "Runs commands"
---

## Steps

Use `execute_command` to run subprocess calls.
"""

_INVALID_YAML_SKILL = """\
---
name: [invalid yaml
description: "broken"
---

Body.
"""


def test_scan_returns_skills():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _make_skill_dir(base, "skill-a", _VALID_SKILL)
        _make_skill_dir(base, "skill-b", _VALID_SKILL.replace("test-skill", "skill-b"))
        adapter = ClaudeLocalAdapter(base)
        results = adapter.scan()
        assert len(results) == 2


def test_normalize_name_to_id():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _make_skill_dir(base, "my-skill", _VALID_SKILL)
        adapter = ClaudeLocalAdapter(base)
        results = adapter.scan()
        card = results[0][0]
        assert card.id == "test-skill"
        assert card.source == SkillSource.EXTERNAL_CLAUDE_LOCAL


def test_hash_deterministic():
    adapter = ClaudeLocalAdapter(Path("."))
    h1 = adapter.compute_hash("hello world")
    h2 = adapter.compute_hash("hello world")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_sandbox_detection_positive():
    assert ClaudeLocalAdapter.detect_sandbox_required("use execute_command here") is True
    assert ClaudeLocalAdapter.detect_sandbox_required("import subprocess") is True
    assert ClaudeLocalAdapter.detect_sandbox_required("git push --force") is True


def test_sandbox_detection_no_false_positives():
    assert ClaudeLocalAdapter.detect_sandbox_required("write a file") is False
    assert ClaudeLocalAdapter.detect_sandbox_required("create a document") is False
    assert ClaudeLocalAdapter.detect_sandbox_required("delete the entry") is False


def test_directory_without_skill_md_ignored(caplog):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "empty-dir").mkdir()
        adapter = ClaudeLocalAdapter(base)
        results = adapter.scan()
        assert results == []
        assert "No SKILL.md" in caplog.text


def test_invalid_yaml_excluded(caplog):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _make_skill_dir(base, "bad", _INVALID_YAML_SKILL)
        adapter = ClaudeLocalAdapter(base)
        results = adapter.scan()
        assert results == []
        assert "YAML parse error" in caplog.text


def test_sandbox_skill_marked():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _make_skill_dir(base, "cmd", _SANDBOX_SKILL)
        adapter = ClaudeLocalAdapter(base)
        results = adapter.scan()
        card = results[0][0]
        assert card.requires_sandbox is True


def test_scan_real_claude_skills():
    """Scan real .claude/skills/ directory — expects >= 14 skills."""
    repo_root = Path(__file__).resolve().parents[3]
    skills_path = repo_root / ".claude" / "skills"
    if not skills_path.is_dir():
        return  # Skip if not in repo context
    adapter = ClaudeLocalAdapter(skills_path)
    results = adapter.scan()
    assert len(results) >= 14
