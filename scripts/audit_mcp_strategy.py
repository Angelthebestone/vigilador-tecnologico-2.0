"""Audit MCP strategy per provider (FR-055, spec 021 D5 native-first).

For each provider in `config/tools/catalog.yaml`, detect:
- main language (python | typescript | go | rust)
- presence of stable Python SDK or REST API
- LOC of the upstream repo (rule <5000 LOC from spec 018)

Emit a JSON report with the proposed `strategy` (WRAP-SDK / CLONE-UPSTREAM /
MCP-EXTERNO) and `runtime` (`python_internal` / `process_stdio` / `process_http`)
per provider, and update `loc_validated: true` in the catalog when measured.

Usage:
    python scripts/audit_mcp_strategy.py [--report]

Outputs:
    docs/audit-mcp-strategy.json
    config/tools/catalog.yaml (in-place, only loc_validated flips)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "config" / "tools" / "catalog.yaml"
REPORT_PATH = REPO_ROOT / "docs" / "audit-mcp-strategy.json"
MCP_SERVERS_DIR = REPO_ROOT / ".mcp-servers"
DOCUMENTATION_DIR = REPO_ROOT / "documentation"

LOC_THRESHOLD = 5000

# Known SDK availability (manual mapping based on public package directories).
# The audit honors this list so a provider with a stable Python SDK becomes
# WRAP-SDK by default, even if no upstream repo is present in this checkout.
KNOWN_PYTHON_SDKS: dict[str, str] = {
    "tavily": "tavily-python",
    "exa": "exa-py",
    "firecrawl": "firecrawl-py",
    "openalex": "pyalex",
    "playwright": "playwright",
    "markitdown": "markitdown",
    "minimax_image": "minimax-mcp-py-or-rest",
    "google_workspace": "google-api-python-client",
    "fetch": "httpx",
    # REST-only providers (no Python SDK but trivial to wrap)
    "brave": "rest",
    "serper": "rest",
    "serper_patents": "rest",
    "jina": "rest",
    "sandbox": "e2b",  # candidate; audit confirms or downgrades
}


@dataclass
class ProviderAudit:
    id: str
    domain: str
    upstream_path: str | None
    language: str
    loc_count: int
    loc_validated: bool
    has_python_sdk: bool
    sdk_hint: str | None
    proposed_strategy: str
    proposed_runtime: str
    notes: str


def _is_python_repo(path: Path) -> bool:
    return (path / "pyproject.toml").exists() or (path / "setup.py").exists() or any(
        path.rglob("*.py")
    )


def _is_node_repo(path: Path) -> bool:
    return (path / "package.json").exists()


def _detect_language(path: Path) -> str:
    if not path.exists():
        return "unknown"
    if (path / "package.json").exists():
        # Node project: distinguish TS vs JS by tsconfig presence
        if (path / "tsconfig.json").exists() or any(path.rglob("*.ts")):
            return "typescript"
        return "javascript"
    if _is_python_repo(path):
        return "python"
    if (path / "go.mod").exists():
        return "go"
    if (path / "Cargo.toml").exists():
        return "rust"
    return "unknown"


def _count_python_loc(path: Path) -> int:
    """Count .py LOC excluding tests, docs, and conftest."""
    if not path.exists():
        return 0
    excluded = ("test", "docs", "documentation")
    total = 0
    for py_file in path.rglob("*.py"):
        # Skip if any path part matches excluded substrings (case-insensitive)
        lower_parts = [p.lower() for p in py_file.parts]
        if any(any(ex in part for ex in excluded) for part in lower_parts):
            continue
        if py_file.name in ("conftest.py",) or py_file.name.endswith("_test.py"):
            continue
        # Read with errors="ignore" so the audit is best-effort across messy
        # third-party trees. A genuine OSError (file vanished, permission
        # denied) is surfaced as a warning per constitucion #4 — never
        # silently swallowed.
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            print(
                f"[audit][warn] cannot read {py_file}: {exc}", file=sys.stderr
            )
            continue
        total += sum(1 for _ in content.splitlines())
    return total


def _find_upstream(provider_id: str) -> Path | None:
    """Locate cloned upstream for a provider, if any.

    Checks `.mcp-servers/<id>/*` and `.mcp-servers/<id-with-hyphens>/*`,
    plus fuzzy match in `documentation/`.
    """
    candidates: list[Path] = []
    # Try both underscore and hyphen variants under .mcp-servers/
    variants = {provider_id, provider_id.replace("_", "-"), provider_id.replace("-", "_")}
    for variant in variants:
        mcp_dir = MCP_SERVERS_DIR / variant
        if mcp_dir.exists():
            nested = [p for p in mcp_dir.iterdir() if p.is_dir()]
            candidates.extend(nested or [mcp_dir])
            break
    # documentation/ has folder names like 'arxip mcp', 'brave mcp', etc.
    if not candidates and DOCUMENTATION_DIR.exists():
        for child in DOCUMENTATION_DIR.iterdir():
            if not child.is_dir():
                continue
            normalized = child.name.lower().replace(" ", "_").replace("-", "_")
            if provider_id in normalized or normalized.startswith(provider_id):
                candidates.append(child)
                break
    return candidates[0] if candidates else None


def _classify(provider_id: str, upstream: Path | None) -> tuple[str, str, str, str, int, bool]:
    """Return (language, strategy, runtime, sdk_hint, loc_count, loc_validated)."""
    sdk_hint = KNOWN_PYTHON_SDKS.get(provider_id)
    has_sdk = bool(sdk_hint)
    language = _detect_language(upstream) if upstream else "unknown"
    loc_count = _count_python_loc(upstream) if upstream and language == "python" else 0
    loc_validated = upstream is not None and language != "unknown"

    # Decision tree (native-first, D5):
    #   1) Has stable Python SDK or REST → WRAP-SDK (in-process)
    #   2) Upstream is Python and LOC < threshold → CLONE-UPSTREAM (in-process)
    #   3) Otherwise → MCP-EXTERNO fallback
    if has_sdk:
        return language, "WRAP-SDK", "python_internal", sdk_hint, loc_count, loc_validated
    if language == "python" and 0 < loc_count < LOC_THRESHOLD:
        return language, "CLONE-UPSTREAM", "python_internal", None, loc_count, loc_validated
    if language in ("typescript", "javascript", "go", "rust"):
        return language, "MCP-EXTERNO", "process_stdio", None, loc_count, loc_validated
    # Unknown upstream + no SDK → conservative fallback
    return language, "MCP-EXTERNO", "process_stdio", None, loc_count, loc_validated


def _load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        raise SystemExit(f"Catalog not found: {CATALOG_PATH}")
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


def _save_catalog(catalog: dict) -> None:
    CATALOG_PATH.write_text(
        yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def audit_all() -> list[ProviderAudit]:
    catalog = _load_catalog()
    entries: Iterable[dict] = catalog.get("tools", []) or []
    audits: list[ProviderAudit] = []
    for entry in entries:
        provider_id = entry.get("id", "")
        existing_strategy = entry.get("strategy", "")
        # Only audit entries currently flagged as MCP-EXTERNO. Native entries
        # (COPY-HERMES, NUEVO, WRAP-SDK already-set) keep their classification.
        if existing_strategy != "MCP-EXTERNO":
            continue
        upstream = _find_upstream(provider_id)
        language, strategy, runtime, sdk_hint, loc, validated = _classify(
            provider_id, upstream
        )
        notes_parts: list[str] = []
        if upstream:
            notes_parts.append(f"upstream={upstream.relative_to(REPO_ROOT)}")
        if sdk_hint:
            notes_parts.append(f"sdk={sdk_hint}")
        if not validated:
            notes_parts.append("upstream not cloned; sdk hint applied")

        # Persist loc_validated when measured
        if validated and language == "python":
            entry["loc_count"] = loc
            entry["loc_validated"] = True

        audits.append(
            ProviderAudit(
                id=provider_id,
                domain=entry.get("domain", ""),
                upstream_path=str(upstream.relative_to(REPO_ROOT)) if upstream else None,
                language=language,
                loc_count=loc,
                loc_validated=validated,
                has_python_sdk=bool(sdk_hint),
                sdk_hint=sdk_hint,
                proposed_strategy=strategy,
                proposed_runtime=runtime,
                notes="; ".join(notes_parts),
            )
        )
    _save_catalog(catalog)
    return audits


def write_report(audits: list[ProviderAudit]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    by_strategy: dict[str, list[str]] = {}
    for a in audits:
        by_strategy.setdefault(a.proposed_strategy, []).append(a.id)
    payload = {
        "summary": {strategy: sorted(ids) for strategy, ids in by_strategy.items()},
        "providers": [asdict(a) for a in audits],
    }
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="store_true",
        help="(Reserved) the audit always prints a summary to stdout.",
    )
    parser.parse_args()

    audits = audit_all()
    write_report(audits)

    # Always print to stdout — the --report flag stays for backwards-compat
    # but the summary is cheap and useful in CI logs.
    print(f"Audited {len(audits)} providers; report at {REPORT_PATH.relative_to(REPO_ROOT)}")
    by_strategy: dict[str, list[str]] = {}
    for a in audits:
        by_strategy.setdefault(a.proposed_strategy, []).append(a.id)
    for strategy in ("WRAP-SDK", "CLONE-UPSTREAM", "MCP-EXTERNO"):
        ids = by_strategy.get(strategy, [])
        print(f"  {strategy:<16} ({len(ids):>2}): {', '.join(sorted(ids)) or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
