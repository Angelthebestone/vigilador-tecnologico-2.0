"""Skill inventory generator (read-only).

Walks the 4 skill sources and extracts a normalized record per skill.
Output: ``docs/skills-inventory.json`` — a single JSON array consumed
by ``analyze_skill_similarity.py`` and the human review workflow.

Sources and layouts:

* ``config/skills/curated/**/*.md`` (Vigilador-curated)
* ``config/skills/learned/**/*.md`` (auto-learned at runtime)
* ``src/.../skills_marketplace/_vendor/k_dense/skills/<id>/SKILL.md``
* ``src/.../skills_marketplace/_vendor/agency_agents/<division>/<agent>.md``

Each record:

```jsonc
{
  "id":          "k_dense.adaptyv",          // canonical id (matches adapter)
  "source":      "k-dense" | "agency-agents" | "curated" | "learned",
  "raw_name":    "adaptyv",                  // value of `name:` in frontmatter
  "slug":        "adaptyv",                  // normalized, [a-z0-9-]+
  "description": "How to use ...",
  "raw_path":    "src/.../adaptyv/SKILL.md",
  "category_hint": "k_dense" | "<division>", // pre-taxonomy bucket
  "tags": ["..."]                            // raw tags from frontmatter if any
}
```
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CURATED_DIR = REPO_ROOT / "config" / "skills" / "curated"
LEARNED_DIR = REPO_ROOT / "config" / "skills" / "learned"
KDENSE_DIR = (
    REPO_ROOT / "src" / "vigilancia_multiagente" / "enterprise"
    / "skills_marketplace" / "_vendor" / "k_dense" / "skills"
)
AGENCY_DIR = (
    REPO_ROOT / "src" / "vigilancia_multiagente" / "enterprise"
    / "skills_marketplace" / "_vendor" / "agency_agents"
)
SKIP_AGENCY_DIVS = {".github", "examples", "scripts", "integrations"}

OUT_PATH = REPO_ROOT / "docs" / "skills-inventory.json"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", value.lower().strip())
    return cleaned.strip("-") or "unknown"


def _parse_frontmatter(path: Path) -> dict[str, Any] | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _scan_kdense() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not KDENSE_DIR.is_dir():
        return out
    for skill_dir in sorted(KDENSE_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        fm = _parse_frontmatter(skill_file)
        if fm is None:
            continue
        raw_name = str(fm.get("name") or skill_dir.name)
        slug = _slug(raw_name)
        tags = fm.get("tags") if isinstance(fm.get("tags"), list) else []
        out.append({
            "id": f"k_dense.{slug}",
            "source": "k-dense",
            "raw_name": raw_name,
            "slug": slug,
            "description": str(fm.get("description", "")).strip(),
            "raw_path": str(skill_file.relative_to(REPO_ROOT)).replace("\\", "/"),
            "category_hint": "k_dense",
            "tags": [str(t) for t in tags],
            "license": str(fm.get("license", "")),
            "author": str(fm.get("author", "")),
        })
    return out


def _scan_agency() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not AGENCY_DIR.is_dir():
        return out
    for division_dir in sorted(AGENCY_DIR.iterdir()):
        if not division_dir.is_dir():
            continue
        if division_dir.name.startswith(".") or division_dir.name in SKIP_AGENCY_DIVS:
            continue
        for agent_file in sorted(division_dir.glob("*.md")):
            fm = _parse_frontmatter(agent_file)
            if fm is None:
                continue
            stem = agent_file.stem
            slug = _slug(stem)
            raw_name = str(fm.get("name") or stem)
            tags = fm.get("tags") if isinstance(fm.get("tags"), list) else []
            out.append({
                "id": f"agency_agents.{division_dir.name}.{slug}",
                "source": "agency-agents",
                "raw_name": raw_name,
                "slug": slug,
                "description": str(fm.get("description", "")).strip(),
                "raw_path": str(
                    agent_file.relative_to(REPO_ROOT)
                ).replace("\\", "/"),
                "category_hint": division_dir.name,
                "tags": [str(t) for t in tags],
                "color": str(fm.get("color", "")),
                "emoji": str(fm.get("emoji", "")),
            })
    return out


def _scan_managed_dir(path: Path, source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.is_dir():
        return out
    for md_file in sorted(path.rglob("*.md")):
        fm = _parse_frontmatter(md_file)
        if fm is None:
            continue
        raw_id = str(fm.get("id") or fm.get("name", md_file.stem))
        slug = _slug(raw_id)
        out.append({
            "id": slug,
            "source": source,
            "raw_name": raw_id,
            "slug": slug,
            "description": str(fm.get("description", "")).strip(),
            "raw_path": str(md_file.relative_to(REPO_ROOT)).replace("\\", "/"),
            "category_hint": source,
            "tags": (
                [str(t) for t in fm.get("tags", [])]
                if isinstance(fm.get("tags"), list)
                else []
            ),
        })
    return out


def main() -> int:
    inventory: list[dict[str, Any]] = []
    inventory.extend(_scan_managed_dir(CURATED_DIR, "curated"))
    inventory.extend(_scan_managed_dir(LEARNED_DIR, "learned"))
    inventory.extend(_scan_kdense())
    inventory.extend(_scan_agency())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    by_source: dict[str, int] = {}
    for s in inventory:
        by_source[s["source"]] = by_source.get(s["source"], 0) + 1
    print(f"Wrote {len(inventory)} skills to {OUT_PATH.relative_to(REPO_ROOT)}")
    for src, count in sorted(by_source.items()):
        print(f"  {src:<14} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
