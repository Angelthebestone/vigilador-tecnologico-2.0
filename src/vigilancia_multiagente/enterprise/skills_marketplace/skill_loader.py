"""SkillLoader — orchestrates loading from curated/learned/k-dense/agency-agents.

Spec 021 D2/D3 (FR-031..FR-033 + organization layer): the 4 canonical
sources are ``[curated, learned, external:k-dense, external:agency-agents]``.

When a :class:`SkillCatalogPort` is supplied, the loader:

* skips registration of skill ids the catalog declares ``inactive``
  (alias or disabled);
* prepends the canonical taxonomy category as the FIRST tag on every
  ``SkillCard`` (e.g. ``"research"``, ``"engineering"``);
* if a ``sub_category`` is declared, adds it as a ``"sub:<id>"`` tag.

When ``catalog`` is ``None`` (legacy / tests), behavior matches the
previous loader: no taxonomy injection, no alias filtering.
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
from vigilancia_multiagente.enterprise.skills_marketplace.skill_catalog import (
    SkillCatalogPort,
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
from vigilancia_multiagente.infra.embeddings.embedding_cache import EmbeddingCache
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
    total_skipped_by_catalog: int = 0
    errors: list[str] = field(default_factory=list)


class SkillLoader:
    """Orchestrates skill loading from enabled sources (Spec 021 D3).

    ``catalog``: optional :class:`SkillCatalogPort`. When provided, every
    skill is filtered + tagged according to the central taxonomy SSOT.
    """

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
        catalog: SkillCatalogPort | None = None,
        embedding_cache: EmbeddingCache | None = None,
        cold_skills_enabled: bool = False,
    ) -> None:
        self._registry = registry
        self._tool_registry = tool_registry
        self._sources_enabled = sources_enabled
        self._curated_path = curated_path
        self._learned_path = learned_path
        self._k_dense_path = k_dense_vendor_path
        self._agency_agents_path = agency_agents_vendor_path
        self._hash_tracker = hash_tracker or HashTracker()
        self._catalog = catalog
        self._embedding_cache = embedding_cache
        self._cold_skills_enabled = cold_skills_enabled

    async def load_all(self) -> LoadResult:
        """Load skills from all enabled sources (no-op for unknown sources)."""
        result = LoadResult()

        # FR-003: Load embedding cache from disk at the start of boot
        if self._embedding_cache:
            self._embedding_cache.load_from_disk()

        if "curated" in self._sources_enabled:
            await self._load_directory(self._curated_path, SkillSource.CURATED, result)

        if "learned" in self._sources_enabled:
            await self._load_directory(self._learned_path, SkillSource.LEARNED, result)

        if "external:k-dense" in self._sources_enabled:
            await self._load_marketplace(
                KDenseAdapter(self._k_dense_path, cold_skills_enabled=self._cold_skills_enabled),
                "external:k-dense",
                result,
            )

        if "external:agency-agents" in self._sources_enabled:
            await self._load_marketplace(
                AgencyAgentsAdapter(self._agency_agents_path, cold_skills_enabled=self._cold_skills_enabled),
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

        # FR-003: Batch save hashes and flush cache at the end of registry build
        self._hash_tracker.save_all()
        await self._registry.flush_cache()

        return result

    # ------------------------------------------------------------------
    # Source loaders
    # ------------------------------------------------------------------

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
            if not self._catalog_admits(skill_id, result):
                continue

            description = str(frontmatter.get("description", ""))
            tags = self._build_tags(skill_id, source.value, [])
            card = SkillCard(
                id=skill_id,
                display_name=skill_id,
                description=description,
                tags=tags,
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
            if not self._catalog_admits(card.id, result):
                continue
            # Augment tags with canonical category & sub-category from the catalog.
            hint = _hint_from_id(card.id)
            card.tags = self._build_tags(card.id, hint, list(card.tags))

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

    # ------------------------------------------------------------------
    # Catalog integration helpers
    # ------------------------------------------------------------------

    def _catalog_admits(self, skill_id: str, result: LoadResult) -> bool:
        if self._catalog is None:
            return True
        if not self._catalog.is_active(skill_id):
            result.total_skipped_by_catalog += 1
            logger.debug(
                "SkillLoader: skill '%s' filtered by catalog (alias/disabled)",
                skill_id,
            )
            return False
        return True

    def _build_tags(
        self, skill_id: str, hint: str, existing: list[str]
    ) -> list[str]:
        """Return tags with canonical category prepended.

        Order: ``[<category>, "sub:<sub>"?, ...existing]``. Idempotent —
        if the canonical category is already in ``existing``, it is moved
        to position 0 instead of duplicated.
        """
        if self._catalog is None:
            return list(existing)
        category = self._catalog.category_for(skill_id, hint)
        sub = self._catalog.sub_category_for(skill_id)
        # Drop any existing entry that matches the canonical category (idempotent).
        cleaned = [t for t in existing if t != category]
        out: list[str] = [category]
        if sub:
            out.append(f"sub:{sub}")
        out.extend(cleaned)
        return out

    async def _validate_capabilities(self, summary: SkillSummary) -> bool:
        """Check all required_capabilities are available. Empty list = always available."""
        if not summary.required_capabilities:
            return True
        for cap in summary.required_capabilities:
            if not await self._tool_registry.is_capability_available(cap):
                return False
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hint_from_id(skill_id: str) -> str:
    """Recover the upstream ``category_hint`` from a canonical skill id.

    Layout:
        * ``agency_agents.<division>.<slug>`` → hint = ``<division>``
        * ``k_dense.<slug>``                   → hint = ``"k_dense"``
        * anything else (curated/learned)      → hint = ``""`` (catalog
          falls back to its ``default_category``).
    """
    if skill_id.startswith("agency_agents."):
        parts = skill_id.split(".")
        if len(parts) >= 3:
            return parts[1]
    if skill_id.startswith("k_dense."):
        return "k_dense"
    return ""
