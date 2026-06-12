"""CatalogLoader — carga y valida el catálogo SSOT de tools (FR-001, FR-002).

Responsabilidades:
- Parsear config/tools/catalog.yaml.
- Validar campos obligatorios y valores permitidos.
- Retornar lista tipada de CatalogEntry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

VALID_STRATEGIES = frozenset({"COPY-HERMES", "WRAP-SDK", "MCP-EXTERNO", "TRANSLATE-THIN", "NUEVO"})
VALID_RUNTIMES = frozenset({"python_internal", "process_stdio", "process_http"})
VALID_LANGUAGES = frozenset({"python", "typescript", "go", "rust", "yaml"})

REQUIRED_FIELDS = (
    "id",
    "domain",
    "source",
    "strategy",
    "runtime",
    "status",
    "owner",
    "license",
    "capabilities",
    "requires_key",
    "env_var",
    "healthcheck",
    "update_policy",
    "loc_count",
    "loc_validated",
    "language",
    "mvp",
)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """Entrada del catálogo SSOT — una capacidad del sistema."""

    id: str
    domain: str
    source: str
    strategy: str
    runtime: str
    status: str
    owner: str
    license: str
    capabilities: list[str]
    requires_key: bool
    env_var: str
    healthcheck: str
    update_policy: str
    loc_count: int
    loc_validated: bool
    language: str
    mvp: bool
    # Opcionales
    notes: str = ""
    dedup_group: str = ""
    source_repo: str = ""
    pinned_version: str = ""
    last_audit_date: str = ""


class CatalogValidationError(Exception):
    """Error de validación del catálogo con contexto explícito."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(
            f"Catalog validation failed with {len(errors)} error(s): {'; '.join(errors)}"
        )


class CatalogLoader:
    """Carga y valida el catálogo SSOT desde YAML."""

    def load(self, path: Path) -> list[CatalogEntry]:
        """Carga catalog.yaml, valida y retorna entradas tipadas."""
        if not path.exists():
            raise CatalogValidationError([f"Catalog file not found: {path}"])

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "tools" not in raw:
            raise CatalogValidationError(["Catalog YAML must have a top-level 'tools' key"])

        entries: list[CatalogEntry] = []
        errors: list[str] = []

        for idx, item in enumerate(raw["tools"]):
            entry_errors = self._validate_entry(item, idx)
            if entry_errors:
                errors.extend(entry_errors)
                continue
            entry = self._parse_entry(item)
            if not entry.loc_validated:
                logger.warning("Entry '%s' has loc_validated=false; LOC not verified", entry.id)
            entries.append(entry)

        if errors:
            raise CatalogValidationError(errors)

        return entries

    def load_mvp_only(self, path: Path) -> list[CatalogEntry]:
        """Carga solo entradas con mvp=true."""
        return [e for e in self.load(path) if e.mvp]

    def _validate_entry(self, item: dict[str, Any], idx: int) -> list[str]:
        errors: list[str] = []
        entry_id = item.get("id", f"<index {idx}>")

        for field_name in REQUIRED_FIELDS:
            if field_name not in item:
                errors.append(f"Entry '{entry_id}': missing required field '{field_name}'")

        if not errors:
            if item["strategy"] not in VALID_STRATEGIES:
                errors.append(
                    f"Entry '{entry_id}': invalid strategy '{item['strategy']}'; "
                    f"must be one of {sorted(VALID_STRATEGIES)}"
                )
            if item["runtime"] not in VALID_RUNTIMES:
                errors.append(
                    f"Entry '{entry_id}': invalid runtime '{item['runtime']}'; "
                    f"must be one of {sorted(VALID_RUNTIMES)}"
                )
            if item["language"] not in VALID_LANGUAGES:
                errors.append(
                    f"Entry '{entry_id}': invalid language '{item['language']}'; "
                    f"must be one of {sorted(VALID_LANGUAGES)}"
                )
            # Coherencia LOC vs strategy (FR-005, FR-006)
            if (
                item["language"] == "python"
                and item["loc_count"] < 5000
                and item["runtime"] != "python_internal"
            ):
                errors.append(
                    f"Entry '{entry_id}': python + loc<5000 must have runtime=python_internal"
                )
            # Exception: strategy NUEVO with python is allowed regardless of LOC rule
            if (
                (item["language"] != "python" or item["loc_count"] >= 5000)
                and item["runtime"] == "python_internal"
                and item["source"] != "nuevo"
                and item["strategy"] != "NUEVO"
            ):
                errors.append(
                    f"Entry '{entry_id}': non-python or loc>=5000 must not have "
                    f"runtime=python_internal"
                )

        return errors

    def _parse_entry(self, item: dict[str, Any]) -> CatalogEntry:
        return CatalogEntry(
            id=item["id"],
            domain=item["domain"],
            source=item["source"],
            strategy=item["strategy"],
            runtime=item["runtime"],
            status=item["status"],
            owner=item["owner"],
            license=item["license"],
            capabilities=list(item["capabilities"]),
            requires_key=bool(item["requires_key"]),
            env_var=str(item.get("env_var", "")),
            healthcheck=item["healthcheck"],
            update_policy=item["update_policy"],
            loc_count=int(item["loc_count"]),
            loc_validated=bool(item["loc_validated"]),
            language=item["language"],
            mvp=bool(item["mvp"]),
            notes=str(item.get("notes", "")),
            dedup_group=str(item.get("dedup_group", "")),
            source_repo=str(item.get("source_repo", "")),
            pinned_version=str(item.get("pinned_version", "")),
            last_audit_date=str(item.get("last_audit_date", "")),
        )
