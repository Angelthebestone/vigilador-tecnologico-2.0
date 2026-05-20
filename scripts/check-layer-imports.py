#!/usr/bin/env python3
"""Validate layered imports: infra must not import api/application."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "vigilancia_multiagente"

LAYER_PREFIXES = {
    "domain": "vigilancia_multiagente.domain",
    "application": "vigilancia_multiagente.application",
    "infra": "vigilancia_multiagente.infra",
    "api": "vigilancia_multiagente.api",
    "shared": "vigilancia_multiagente.shared",
    "config": "vigilancia_multiagente.config",
}

FORBIDDEN: list[tuple[str, str, str]] = [
    ("infra", "api", "infra must not import api"),
    ("infra", "application", "infra must not import application"),
    ("application", "api", "application must not import api"),
    ("application", "infra", "application must not import infra (DIP)"),
]


def layer_for_path(path: Path) -> str | None:
    rel = path.relative_to(SRC_ROOT)
    parts = rel.parts
    if not parts:
        return None
    return parts[0]


def imported_layers(node: ast.AST) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                mod = alias.name
                for layer, prefix in LAYER_PREFIXES.items():
                    if mod == prefix or mod.startswith(prefix + "."):
                        found.append((layer, child.lineno))
        elif isinstance(child, ast.ImportFrom) and child.module:
            mod = child.module
            for layer, prefix in LAYER_PREFIXES.items():
                if mod == prefix or mod.startswith(prefix + "."):
                    found.append((layer, child.lineno))
    return found


def check_file(path: Path) -> list[str]:
    source_layer = layer_for_path(path)
    if source_layer is None:
        return []
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported = imported_layers(tree)
    for src_layer, tgt_layer, message in FORBIDDEN:
        if source_layer != src_layer:
            continue
        for imp_layer, lineno in imported:
            if imp_layer == tgt_layer:
                rel = path.relative_to(REPO_ROOT)
                detail = message
                if tgt_layer == "api" and "api.dependencies" in source:
                    detail = f"{message} (api.dependencies)"
                errors.append(f"{rel}:{lineno}: {detail}")
    return errors


def main() -> int:
    all_errors: list[str] = []
    for py_file in sorted(SRC_ROOT.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        all_errors.extend(check_file(py_file))
    if all_errors:
        print("Layer import violations found:", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    print("OK: no layer import violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
