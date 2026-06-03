"""Agency-Agents adapter (Spec 021 D2/T071, FR-031/032).

Scans the cloned ``_vendor/agency_agents/<division>/<agent>.md`` tree,
parses the YAML frontmatter, and emits ``(CommandSkill, SkillSummary,
body)`` triples for ``SkillRegistry``.

Differences vs K-Dense:

* One file per agent (no per-agent directory).
* Frontmatter has ``name``, ``description``, ``color``, ``emoji``,
  ``vibe``. We carry ``color`` and ``emoji`` into the card's tag list
  for UI rendering; ``vibe`` becomes an example (level-2 detail).
* The division (top-level directory) is captured both as a tag and as
  a prefix on the skill id so collisions across divisions cannot occur.
* All agency-agents skills carry ``audit_level="alto"`` because they
  describe roles that may take consequential actions (e.g. financial
  analysis, infrastructure changes).

Source identifier: ``SkillSource.EXTERNAL_AGENCY_AGENTS``.
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
_SKIP_DIRS = {".github", "examples", "scripts", "integrations"}


@dataclass(frozen=True)
class _Triple:
    card: CommandSkill
    summary: SkillSummary
    body: str


class AgencyAgentsAdapter:
    """Adapter for the ``msitarzewski/agency-agents`` marketplace."""

    def __init__(self, vendor_path: Path) -> None:
        """``vendor_path`` is the ``_vendor/agency_agents/`` root."""
        self._root = vendor_path

    def scan(self) -> list[tuple[CommandSkill, SkillSummary, str]]:
        out: list[tuple[CommandSkill, SkillSummary, str]] = []
        if not self._root.is_dir():
            logger.warning("AgencyAgentsAdapter: vendor path missing: %s", self._root)
            return out

        for division_dir in sorted(self._root.iterdir()):
            if not division_dir.is_dir():
                continue
            if division_dir.name.startswith(".") or division_dir.name in _SKIP_DIRS:
                continue
            for md_file in sorted(division_dir.glob("*.md")):
                triple = self._parse_one(md_file, division_dir.name)
                if triple is not None:
                    out.append((triple.card, triple.summary, triple.body))
        logger.info(
            "AgencyAgentsAdapter: scanned %d agents under %s", len(out), self._root
        )
        return out

    # ------------------------------------------------------------------
    # parser
    # ------------------------------------------------------------------

    def _parse_one(self, path: Path, division: str) -> _Triple | None:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("AgencyAgentsAdapter: cannot read %s: %s", path, exc)
            return None
        match = _FRONTMATTER_RE.match(content)
        if not match:
            logger.warning("AgencyAgentsAdapter: no frontmatter in %s", path)
            return None
        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            logger.warning("AgencyAgentsAdapter: YAML error in %s: %s", path, exc)
            return None
        if not isinstance(frontmatter, dict):
            logger.warning("AgencyAgentsAdapter: non-dict frontmatter in %s", path)
            return None
        body = content[match.end():]

        agent_name = str(frontmatter.get("name") or path.stem)
        slug = self._slug(path.stem)
        description = str(frontmatter.get("description", ""))
        color = str(frontmatter.get("color", ""))
        emoji = str(frontmatter.get("emoji", ""))
        vibe = str(frontmatter.get("vibe", ""))

        tags = ["agency-agents", division]
        if color:
            tags.append(f"color:{color}")
        if emoji:
            tags.append(f"emoji:{emoji}")

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        card = CommandSkill(
            id=f"agency_agents.{division}.{slug}",
            display_name=agent_name,
            description=description,
            tags=tags,
            source=SkillSource.EXTERNAL_AGENCY_AGENTS,
            content_hash=content_hash,
            path=str(path),
            user_invocable=True,
        )
        summary = SkillSummary(
            required_capabilities=[],
            examples=[vibe] if vibe else [],
            audit_level="alto",
        )
        return _Triple(card=card, summary=summary, body=body)

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9_-]+", "_", value.lower().strip())
        return cleaned.strip("_") or "unknown"
