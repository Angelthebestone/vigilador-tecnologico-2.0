"""SkillLoader — orchestrates loading from curated/learned/k-dense/agency-agents.

Spec 021 D3 (FR-033): ``.claude/skills/`` is no longer a runtime source.
The 4 canonical sources are:
``[curated, learned, external:k-dense, external:agency-agents]``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.agency_agents_adapter import (
    AgencyAgentsAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.hash_tracker import HashTracker
from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import (
    KDenseAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    SkillCard,
    SkillSource,
    SkillState,
    SkillSummary,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import (
    SkillRegistry,
    ToolRegistryPort,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_schema_validator import (
    validate_frontmatter,
)

logger = logging.getLogger(__name__)


@dataclass
class LoadResult:
    """Result of loading all skill sources."""

    total_registered: int = 0
    total_unavailable: int = 0
    total_skipped: int = 0
    errors: list[str] = field(default_factory=list)


class SkillLoader:
    """Orchestrates skill loading from enabled sources (Spec 021 D3)."""

    def __init__(
        self,
        registry: SkillRegistry,
        tool_registry: ToolRegistryPort,
        sources_enabled: list[str],
        curated_path: Path,
        learned_path: Path,
        k_dense_vendor_path: Path,
        agency_agents_vendor_path: Path,
        hash_tracker: HashTracker | None = None,
    ) -> None:
        self._registry = registry
        self._tool_registry = tool_registry
        self._sources_enabled = sources_enabled
        self._curated_path = curated_path
        self._learned_path = learned_path
        self._k_dense_path = k_dense_vendor_path
        self._agency_agents_path = agency_agents_vendor_path
        self._hash_tracker = hash_tracker or HashTracker()

    async def load_all(self) -> LoadResult:
        """Load skills from all enabled sources (no-op for unknown sources)."""
        result = LoadResult()

        if "curated" in self._sources_enabled:
            await self._load_directory(self._curated_path, SkillSource.CURATED, result)

        if "learned" in self._sources_enabled:
            await self._load_directory(self._learned_path, SkillSource.LEARNED, result)

        if "external:k-dense" in self._sources_enabled:
            await self._load_marketplace(
                KDenseAdapter(self._k_dense_path),
                "external:k-dense",
                result,
            )

        if "external:agency-agents" in self._sources_enabled:
            await self._load_marketplace(
                AgencyAgentsAdapter(self._agency_agents_path),
                "external:agency-agents",
                result,
            )

        # Any explicitly-unknown source is a config bug — surface explicitly.
        known = {
            "curated", "learned",
            "external:k-dense", "external:agency-agents",
        }
        for source in self._sources_enabled:
            if source not in known:
                result.errors.append(
                    f"SkillLoader: unknown source '{source}' "
                    "(supported: curated, learned, external:k-dense, "
                    "external:agency-agents)"
                )

        return result

    async def _load_directory(
        self, path: Path, source: SkillSource, result: LoadResult
    ) -> None:
        """Load skills from a curated/learned directory."""
        if not path.is_dir():
            return
        import re

        import yaml

        frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

        for md_file in sorted(path.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            match = frontmatter_re.match(content)
            if not match:
                continue
            try:
                frontmatter = yaml.safe_load(match.group(1))
            except yaml.YAMLError as exc:
                result.errors.append(f"YAML error in {md_file}: {exc}")
                result.total_skipped += 1
                continue

            if not isinstance(frontmatter, dict):
                result.total_skipped += 1
                continue

            validation = validate_frontmatter(frontmatter, str(md_file))
            if not validation.valid:
                result.errors.extend(validation.errors)
                result.total_skipped += 1
                continue

            skill_id = str(frontmatter.get("id") or frontmatter.get("name", ""))
            card = SkillCard(
                id=skill_id,
                display_name=skill_id,
                description=str(frontmatter.get("description", "")),
                source=source,
                path=str(md_file),
            )
            summary = SkillSummary(
                required_capabilities=frontmatter.get("required_capabilities", [])
                if isinstance(frontmatter.get("required_capabilities"), list)
                else [],
            )

            available = await self._validate_capabilities(summary)
            if not available:
                card.state = SkillState.UNAVAILABLE
                result.total_unavailable += 1

            try:
                await self._registry.register(card, summary, str(md_file))
                result.total_registered += 1
            except ValueError as exc:
                result.errors.append(str(exc))
                result.total_skipped += 1

    async def _load_marketplace(
        self,
        adapter: object,  # KDenseAdapter | AgencyAgentsAdapter
        source_label: str,
        result: LoadResult,
    ) -> None:
        """Common loader path for the cloned in-tree marketplaces (FR-031/032)."""
        scanner = getattr(adapter, "scan", None)
        if scanner is None:
            result.errors.append(
                f"SkillLoader: adapter for '{source_label}' missing scan() method"
            )
            return

        for card, summary, _body in scanner():
            # Track content_hash so revalidation triggers on upstream bumps.
            if self._hash_tracker.has_changed(card.id, card.content_hash):
                card.state = SkillState.PENDING_REVALIDATION
            else:
                self._hash_tracker.update(card.id, card.content_hash)

            available = await self._validate_capabilities(summary)
            if not available and card.state == SkillState.AVAILABLE:
                card.state = SkillState.UNAVAILABLE
                result.total_unavailable += 1

            try:
                await self._registry.register(card, summary, card.path)
                result.total_registered += 1
            except ValueError as exc:
                result.errors.append(str(exc))
                result.total_skipped += 1

    async def _validate_capabilities(self, summary: SkillSummary) -> bool:
        """Check all required_capabilities are available. Empty list = always available."""
        if not summary.required_capabilities:
            return True
        for cap in summary.required_capabilities:
            if not await self._tool_registry.is_capability_available(cap):
                return False
        return True
