"""Claude local adapter — scans .claude/skills/*/SKILL.md and normalizes to SkillCard."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import yaml

from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    CommandSkill,
    SkillSource,
    SkillState,
    SkillSummary,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_schema_validator import (
    validate_frontmatter,
)

logger = logging.getLogger(__name__)

_SANDBOX_KEYWORDS: tuple[str, ...] = (
    "execute_command",
    "subprocess",
    "os.system",
    "os.popen",
    "Popen",
    "shell=True",
    "bash -c",
    "git push",
    "git reset",
    "git clean",
    "rm -rf",
    "shutil.rmtree",
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class ClaudeLocalAdapter:
    """Adapter that scans .claude/skills/*/SKILL.md and produces CommandSkill cards."""

    def __init__(self, skills_path: Path) -> None:
        self._skills_path = skills_path

    def scan(self) -> list[tuple[CommandSkill, SkillSummary, str]]:
        """Scan all subdirectories for SKILL.md. Returns (card, summary, body_content) tuples."""
        results: list[tuple[CommandSkill, SkillSummary, str]] = []
        if not self._skills_path.is_dir():
            logger.warning("Skills path does not exist: %s", self._skills_path)
            return results

        for subdir in sorted(self._skills_path.iterdir()):
            if not subdir.is_dir():
                continue
            skill_file = subdir / "SKILL.md"
            if not skill_file.is_file():
                logger.warning("No SKILL.md in directory: %s", subdir.name)
                continue
            result = self._parse_skill_file(skill_file)
            if result is not None:
                results.append(result)
        return results

    def _parse_skill_file(self, path: Path) -> tuple[CommandSkill, SkillSummary, str] | None:
        content = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(content)
        if not match:
            logger.error("Invalid or missing YAML frontmatter in: %s", path)
            return None

        raw_yaml_str = match.group(1)
        try:
            frontmatter = yaml.safe_load(raw_yaml_str)
        except yaml.YAMLError as exc:
            logger.error("YAML parse error in %s: %s", path, exc)
            return None

        if not isinstance(frontmatter, dict):
            logger.error("Frontmatter is not a mapping in: %s", path)
            return None

        normalized = self._normalize_openclaw(frontmatter)
        validation = validate_frontmatter(normalized, str(path))
        if not validation.valid:
            for err in validation.errors:
                logger.error(err)
            return None

        skill_id = str(normalized.get("id", ""))
        body = content[match.end():]
        content_hash = self.compute_hash(content)
        requires_sandbox = self.detect_sandbox_required(content)

        card = CommandSkill(
            id=skill_id,
            display_name=str(normalized.get("id", "")),
            description=str(normalized.get("description", "")),
            tags=normalized.get("tags", []) if isinstance(normalized.get("tags"), list) else [],
            source=SkillSource.EXTERNAL_CLAUDE_LOCAL,
            mode_compatible=normalized.get("mode_compatible", []) if isinstance(normalized.get("mode_compatible"), list) else [],
            state=SkillState.AVAILABLE,
            content_hash=content_hash,
            requires_sandbox=requires_sandbox,
            path=str(path),
            argument_hint=str(normalized.get("argument-hint", "")),
            user_invocable=bool(normalized.get("user-invocable", True)),
        )

        required_caps = normalized.get("required_capabilities", [])
        summary = SkillSummary(
            required_capabilities=required_caps if isinstance(required_caps, list) else [],
        )

        return card, summary, body

    def _normalize_openclaw(self, frontmatter: dict[str, object]) -> dict[str, object]:
        """Normalize OpenClaw format: name->id, allowed-tools->required_capabilities."""
        result = dict(frontmatter)
        if "name" in result and "id" not in result:
            result["id"] = result["name"]
        if "allowed-tools" in result and "required_capabilities" not in result:
            tools = result.pop("allowed-tools")
            result["required_capabilities"] = tools if isinstance(tools, list) else []
        # Ensure source
        if "source" not in result:
            result["source"] = SkillSource.EXTERNAL_CLAUDE_LOCAL
        return result

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def detect_sandbox_required(body: str) -> bool:
        """Detect if skill requires sandbox based on command/code keywords."""
        return any(kw in body for kw in _SANDBOX_KEYWORDS)
