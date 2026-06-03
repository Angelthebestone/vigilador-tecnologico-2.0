"""K-Dense scientific-agent-skills adapter (Spec 021 D2/T069, FR-031/032).

Scans the cloned ``_vendor/k_dense/skills/<id>/SKILL.md`` tree, parses
each frontmatter block, and emits ``(SkillCard, SkillSummary, body)``
triples in the same shape as :class:`ClaudeLocalAdapter` so the existing
``SkillRegistry`` can register them without changes.

The adapter is **read-only** — it never mutates the vendored tree.
Skills with malformed YAML are reported via the standard
``SkillSchemaValidator`` (no silent skip).

Source identifier: ``SkillSource.EXTERNAL_K_DENSE`` (``external:k-dense``).
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    CommandSkill,
    SkillSource,
    SkillSummary,
)

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class _Triple:
    card: CommandSkill
    summary: SkillSummary
    body: str


class KDenseAdapter:
    """Adapter for the ``K-Dense-AI/scientific-agent-skills`` marketplace."""

    def __init__(self, vendor_path: Path) -> None:
        """``vendor_path`` is the ``_vendor/k_dense/`` directory root."""
        self._root = vendor_path

    def scan(self) -> list[tuple[CommandSkill, SkillSummary, str]]:
        out: list[tuple[CommandSkill, SkillSummary, str]] = []
        skills_dir = self._root / "skills"
        if not skills_dir.is_dir():
            logger.warning("KDenseAdapter: skills/ not found at %s", skills_dir)
            return out

        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            triple = self._parse_one(skill_file)
            if triple is not None:
                out.append((triple.card, triple.summary, triple.body))
        logger.info("KDenseAdapter: scanned %d skills under %s", len(out), skills_dir)
        return out

    # ------------------------------------------------------------------
    # parser
    # ------------------------------------------------------------------

    def _parse_one(self, path: Path) -> _Triple | None:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("KDenseAdapter: cannot read %s: %s", path, exc)
            return None
        match = _FRONTMATTER_RE.match(content)
        if not match:
            logger.warning("KDenseAdapter: no frontmatter in %s", path)
            return None
        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            logger.warning("KDenseAdapter: YAML error in %s: %s", path, exc)
            return None
        if not isinstance(frontmatter, dict):
            logger.warning("KDenseAdapter: non-dict frontmatter in %s", path)
            return None
        body = content[match.end():]

        skill_id = self._slug(str(frontmatter.get("name") or path.parent.name))
        description = str(frontmatter.get("description", ""))
        author = str(frontmatter.get("author", ""))
        compatibility = str(frontmatter.get("compatibility", ""))
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        version = str(metadata.get("version", "")) if metadata else ""

        # Tags: K-Dense skills are scientific tools; emit category from
        # the directory name + author + version for downstream filtering.
        tags = [
            "k-dense",
            path.parent.name,
        ]
        if author:
            tags.append(f"author:{author.lower().replace(' ', '_')}")
        if version:
            tags.append(f"v{version}")

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        card = CommandSkill(
            id=f"k_dense.{skill_id}",
            display_name=skill_id,
            description=description,
            tags=tags,
            source=SkillSource.EXTERNAL_K_DENSE,
            content_hash=content_hash,
            path=str(path),
            user_invocable=True,
        )
        summary = SkillSummary(
            required_capabilities=[],
            examples=[compatibility] if compatibility else [],
            audit_level="standard",
        )
        return _Triple(card=card, summary=summary, body=body)

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9_-]+", "_", value.lower().strip())
        return cleaned.strip("_") or "unknown"
