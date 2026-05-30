#!/usr/bin/env python3
"""Valida config/tools/catalog.yaml contra reglas del spec 018.

Verifica:
- Campos obligatorios presentes en cada entrada.
- Valores permitidos de strategy, runtime, language.
- Coherencia LOC vs strategy (FR-005, FR-006).
- Conteo total de entradas y MVP.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Añadir src al path para importar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vigilancia_multiagente.enterprise.tooling.catalog_loader import (
    CatalogLoader,
    CatalogValidationError,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "tools" / "catalog.yaml"


def main() -> int:
    loader = CatalogLoader()
    try:
        entries = loader.load(CATALOG_PATH)
    except CatalogValidationError as exc:
        print(f"VALIDATION FAILED ({len(exc.errors)} errors):", file=sys.stderr)
        for err in exc.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    total = len(entries)
    mvp_count = sum(1 for e in entries if e.mvp)

    print(f"Total entries: {total}")
    print(f"MVP entries: {mvp_count}")

    errors: list[str] = []
    if mvp_count != 20:
        errors.append(f"Expected 20 MVP entries, got {mvp_count}")

    # Verificar coherencia adicional
    for entry in entries:
        if entry.language == "python" and entry.loc_count < 5000:
            if entry.runtime != "python_internal":
                errors.append(
                    f"Entry '{entry.id}': python + loc<5000 should be python_internal, "
                    f"got {entry.runtime}"
                )

    if errors:
        print(f"\nCOHERENCE ERRORS ({len(errors)}):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("OK: catalog validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
