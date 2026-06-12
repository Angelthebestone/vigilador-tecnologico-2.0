"""SkillCatalog — central organizer for the unified skill marketplace.

Spec 021 D2/D3 — single source of truth that decides, given a skill id
and its source-side ``category_hint``, the canonical taxonomy slot, any
override (recategorize / disable / alias), and the optional sub-category
tag. Consumed by :class:`SkillLoader` so every adapter feeds the same
organizing logic without duplicating taxonomy code.

Behavior:

* ``category_for(skill_id, hint)`` — resolves to the canonical top-level
  category id (e.g. ``"research"``, ``"engineering"``). Order of resolution:

  1. ``catalog.recategorize[skill_id]`` if present.
  2. ``taxonomy.mapping[hint]`` if present.
  3. ``taxonomy.default_category`` as fallback.

* ``sub_category_for(skill_id)`` — optional finer placement
  (``catalog.sub_category[skill_id]``); returns ``None`` if unset.

* ``is_active(skill_id)`` — False iff the id is in ``catalog.disabled``
  or ``catalog.aliases`` (an alias should never be loaded as a skill in
  its own right).

* ``canonical_for(skill_id)`` — when ``skill_id`` is an alias, returns
  the canonical id; else returns ``skill_id`` unchanged.

* ``categories()`` — read-only list of top-level
  :class:`CategoryDefinition` (for UI / reporting).

Constitución:
* SRP: read-only catalog logic; no I/O beyond the two YAML files at init.
* DIP: ``SkillLoader`` depends on this class via the ``SkillCatalogPort``
  Protocol declared at the bottom.
* #4 explicit: malformed YAML or missing required keys raise on construct.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubCategoryDefinition:
    id: str
    label: str


@dataclass(frozen=True)
class CategoryDefinition:
    id: str
    label: str
    description: str = ""
    sub_categories: tuple[SubCategoryDefinition, ...] = field(default_factory=tuple)


class SkillCatalogError(RuntimeError):
    """Raised when taxonomy/catalog YAML is malformed or inconsistent."""


class SkillCatalog:
    """Loads ``taxonomy.yaml`` + ``catalog.yaml`` once and answers queries."""

    def __init__(
        self,
        taxonomy_path: Path,
        catalog_path: Path | None = None,
    ) -> None:
        self._taxonomy_path = taxonomy_path
        self._catalog_path = catalog_path
        self._categories: dict[str, CategoryDefinition] = {}
        self._mapping: dict[str, str] = {}
        self._default_category: str = "specialized"
        self._aliases: dict[str, str] = {}
        self._disabled: set[str] = set()
        self._recategorize: dict[str, str] = {}
        self._sub_category: dict[str, str] = {}
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._load_taxonomy()
        if self._catalog_path is not None and self._catalog_path.exists():
            self._load_catalog_overrides()
        self._validate()

    def _load_taxonomy(self) -> None:
        if not self._taxonomy_path.is_file():
            raise SkillCatalogError(f"taxonomy file not found: {self._taxonomy_path}")
        try:
            data = yaml.safe_load(self._taxonomy_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise SkillCatalogError(
                f"taxonomy YAML invalid ({self._taxonomy_path}): {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise SkillCatalogError(
                f"taxonomy must be a mapping at top level ({self._taxonomy_path})"
            )

        cats_raw = data.get("categories")
        if not isinstance(cats_raw, list) or not cats_raw:
            raise SkillCatalogError(
                f"taxonomy.categories must be a non-empty list ({self._taxonomy_path})"
            )
        for cat in cats_raw:
            if not isinstance(cat, dict) or "id" not in cat:
                raise SkillCatalogError(f"taxonomy category entry missing 'id': {cat!r}")
            sub_defs: list[SubCategoryDefinition] = []
            for sub in cat.get("sub_categories", []) or []:
                if not isinstance(sub, dict) or "id" not in sub:
                    raise SkillCatalogError(f"taxonomy sub_category entry missing 'id': {sub!r}")
                sub_defs.append(
                    SubCategoryDefinition(
                        id=str(sub["id"]),
                        label=str(sub.get("label", sub["id"])),
                    )
                )
            cat_def = CategoryDefinition(
                id=str(cat["id"]),
                label=str(cat.get("label", cat["id"])),
                description=str(cat.get("description", "")),
                sub_categories=tuple(sub_defs),
            )
            self._categories[cat_def.id] = cat_def

        mapping_raw = data.get("mapping") or {}
        if not isinstance(mapping_raw, dict):
            raise SkillCatalogError("taxonomy.mapping must be a mapping")
        self._mapping = {str(k): str(v) for k, v in mapping_raw.items()}

        default_cat = data.get("default_category")
        if isinstance(default_cat, str) and default_cat:
            self._default_category = default_cat

    def _load_catalog_overrides(self) -> None:
        try:
            data = yaml.safe_load(
                self._catalog_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
            )
        except yaml.YAMLError as exc:
            raise SkillCatalogError(f"catalog YAML invalid ({self._catalog_path}): {exc}") from exc
        if data is None:
            return  # empty file is fine — no overrides
        if not isinstance(data, dict):
            raise SkillCatalogError(
                f"catalog must be a mapping at top level ({self._catalog_path})"
            )

        self._aliases = {str(k): str(v) for k, v in (data.get("aliases") or {}).items()}
        disabled_raw = data.get("disabled") or []
        if not isinstance(disabled_raw, list):
            raise SkillCatalogError("catalog.disabled must be a list")
        self._disabled = {str(x) for x in disabled_raw}
        self._recategorize = {str(k): str(v) for k, v in (data.get("recategorize") or {}).items()}
        self._sub_category = {str(k): str(v) for k, v in (data.get("sub_category") or {}).items()}

    def _validate(self) -> None:
        # Every mapping target must reference an existing category.
        for hint, cat_id in self._mapping.items():
            if cat_id not in self._categories:
                raise SkillCatalogError(
                    f"taxonomy.mapping[{hint!r}] -> {cat_id!r} is not a declared category"
                )
        # Every recategorize target must reference an existing category.
        for sid, cat_id in self._recategorize.items():
            if cat_id not in self._categories:
                raise SkillCatalogError(
                    f"catalog.recategorize[{sid!r}] -> {cat_id!r} is not a declared category"
                )
        # Every alias's target must NOT itself be aliased (one-hop only).
        for alias, target in self._aliases.items():
            if target in self._aliases:
                raise SkillCatalogError(
                    f"alias chain not allowed: {alias!r} -> {target!r} (target is itself an alias)"
                )

    # ------------------------------------------------------------------
    # Public queries
    # ------------------------------------------------------------------

    def category_for(self, skill_id: str, category_hint: str) -> str:
        """Resolve the canonical top-level category for ``skill_id``."""
        if skill_id in self._recategorize:
            return self._recategorize[skill_id]
        if category_hint in self._mapping:
            return self._mapping[category_hint]
        return self._default_category

    def sub_category_for(self, skill_id: str) -> str | None:
        return self._sub_category.get(skill_id)

    def is_active(self, skill_id: str) -> bool:
        return skill_id not in self._disabled and skill_id not in self._aliases

    def canonical_for(self, skill_id: str) -> str:
        return self._aliases.get(skill_id, skill_id)

    def categories(self) -> list[CategoryDefinition]:
        return list(self._categories.values())

    def category_ids(self) -> list[str]:
        return list(self._categories.keys())

    def aliases(self) -> dict[str, str]:
        """Read-only view of declared aliases."""
        return dict(self._aliases)

    def disabled(self) -> set[str]:
        return set(self._disabled)


# ---------------------------------------------------------------------------
# Port for SkillLoader to consume (DIP)
# ---------------------------------------------------------------------------


@runtime_checkable
class SkillCatalogPort(Protocol):
    """Subset SkillLoader depends on."""

    def category_for(self, skill_id: str, category_hint: str) -> str: ...

    def sub_category_for(self, skill_id: str) -> str | None: ...

    def is_active(self, skill_id: str) -> bool: ...
