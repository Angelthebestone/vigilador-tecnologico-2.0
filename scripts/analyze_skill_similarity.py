"""Skill similarity analyzer (read-only).

Reads ``docs/skills-inventory.json`` produced by ``inventory_skills.py``
and emits two artifacts:

* ``docs/skills-similarity-pairs.json`` — every candidate duplicate pair
  with normalized scores (slug Levenshtein + description Jaccard +
  combined score).
* ``docs/skills-similarity-analysis.md`` — human-readable report grouping
  pairs above the review threshold by source and category, with
  recommended canonical pick.

Heuristics:

1. **Slug similarity** — character-bigram Jaccard on the normalized slug.
   Catches reformulations like ``backend-architect`` vs
   ``backend-engineer``. Threshold: ``>= 0.55``.
2. **Description similarity** — word-shingle (size 3) Jaccard on the
   first 600 chars of ``description``. Catches paraphrases.
   Threshold: ``>= 0.30``.
3. **Combined** — ``0.4 * slug + 0.6 * description``. Pairs with combined
   ``>= 0.45`` go into the report; pairs with ``>= 0.65`` are suggested
   as **strong duplicates** (prime candidates for ``alias_of`` in the
   catalog override).

We only compare:

* skills inside the SAME source (most likely duplicate population),
* skills inside the SAME ``category_hint`` (intra-division),
* and full cross-source pairs only when slug similarity is very high
  (> 0.75) — cross-source dupes are rare but worth flagging.

Constitución: read-only, deterministic output (sorted), explicit error
on missing inventory file.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "docs" / "skills-inventory.json"
PAIRS_OUT = REPO_ROOT / "docs" / "skills-similarity-pairs.json"
REPORT_OUT = REPO_ROOT / "docs" / "skills-similarity-analysis.md"

_SLUG_THRESHOLD = 0.55
_DESC_THRESHOLD = 0.30
_REVIEW_THRESHOLD = 0.35
_STRONG_THRESHOLD = 0.55
_CROSS_SOURCE_SLUG_FLOOR = 0.65
_DESC_MAX_CHARS = 600
_SHINGLE_K = 3


# ---------------------------------------------------------------------------
# Slug normalization — strip division prefix so "engineering-ai-engineer"
# and "engineering-data-engineer" don't share an inflated bigram overlap
# from the common "engineering-" prefix that doesn't actually carry
# semantic content.
# ---------------------------------------------------------------------------


def _core_slug(skill: dict) -> str:
    slug = skill["slug"]
    # agency_agents files start with "<division>-..."; remove that prefix.
    cat = skill.get("category_hint", "")
    if cat and slug.startswith(cat + "-"):
        return slug[len(cat) + 1:]
    return slug


# ---------------------------------------------------------------------------
# Similarity primitives
# ---------------------------------------------------------------------------


def _bigrams(text: str) -> set[str]:
    text = text.lower()
    if len(text) < 2:
        return {text}
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _normalize_desc(desc: str) -> str:
    text = (desc or "")[:_DESC_MAX_CHARS].lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _shingles(desc: str, k: int = _SHINGLE_K) -> set[str]:
    words = _normalize_desc(desc).split()
    if len(words) < k:
        return set(words)
    return {
        " ".join(words[i : i + k])
        for i in range(len(words) - k + 1)
    }


# ---------------------------------------------------------------------------
# Pair detection
# ---------------------------------------------------------------------------


def _score_pair(a: dict, b: dict) -> tuple[float, float, float]:
    slug_sim = _jaccard(_bigrams(_core_slug(a)), _bigrams(_core_slug(b)))
    desc_sim = _jaccard(_shingles(a["description"]), _shingles(b["description"]))
    combined = 0.4 * slug_sim + 0.6 * desc_sim
    return slug_sim, desc_sim, combined


def _pick_canonical(a: dict, b: dict) -> tuple[dict, dict]:
    """Pick canonical (winner) and alias (loser) for a duplicate pair.

    Heuristic: prefer the entry with the longer description (more meat),
    breaking ties by source priority (curated > learned > k-dense >
    agency-agents) then by alphabetical id for determinism.
    """
    source_priority = {
        "curated": 0, "learned": 1, "k-dense": 2, "agency-agents": 3,
    }

    def score(s: dict) -> tuple[int, int, str]:
        return (
            -len(s["description"] or ""),  # longer first
            source_priority.get(s["source"], 9),
            s["id"],
        )

    if score(a) <= score(b):
        return a, b
    return b, a


def main() -> int:
    if not INVENTORY.exists():
        print(
            f"ERROR: {INVENTORY.relative_to(REPO_ROOT)} not found. "
            "Run scripts/inventory_skills.py first.",
            file=sys.stderr,
        )
        return 1
    skills = json.loads(INVENTORY.read_text(encoding="utf-8"))

    # Bucket by (source, category_hint) for intra-bucket pair generation.
    buckets: dict[tuple[str, str], list[dict]] = {}
    for s in skills:
        key = (s["source"], s["category_hint"])
        buckets.setdefault(key, []).append(s)

    pairs: list[dict] = []

    # Intra-bucket pairs.
    for skills_in_bucket in buckets.values():
        for a, b in itertools.combinations(skills_in_bucket, 2):
            slug_sim, desc_sim, combined = _score_pair(a, b)
            if combined < _REVIEW_THRESHOLD:
                continue
            if slug_sim < _SLUG_THRESHOLD and desc_sim < _DESC_THRESHOLD:
                continue
            canonical, alias = _pick_canonical(a, b)
            pairs.append({
                "canonical_id": canonical["id"],
                "alias_id": alias["id"],
                "scope": "intra-bucket",
                "source": a["source"],
                "category_hint": a["category_hint"],
                "slug_similarity": round(slug_sim, 3),
                "description_similarity": round(desc_sim, 3),
                "combined_score": round(combined, 3),
                "strong_duplicate": combined >= _STRONG_THRESHOLD,
                "canonical_name": canonical["raw_name"],
                "alias_name": alias["raw_name"],
                "canonical_description": canonical["description"][:200],
                "alias_description": alias["description"][:200],
            })

    # Cross-source pairs (only when slug similarity is very high).
    for a, b in itertools.combinations(skills, 2):
        if a["source"] == b["source"]:
            continue
        slug_sim = _jaccard(_bigrams(_core_slug(a)), _bigrams(_core_slug(b)))
        if slug_sim < _CROSS_SOURCE_SLUG_FLOOR:
            continue
        desc_sim = _jaccard(_shingles(a["description"]), _shingles(b["description"]))
        combined = 0.4 * slug_sim + 0.6 * desc_sim
        if combined < _REVIEW_THRESHOLD:
            continue
        canonical, alias = _pick_canonical(a, b)
        pairs.append({
            "canonical_id": canonical["id"],
            "alias_id": alias["id"],
            "scope": "cross-source",
            "source": f"{a['source']}+{b['source']}",
            "category_hint": "",
            "slug_similarity": round(slug_sim, 3),
            "description_similarity": round(desc_sim, 3),
            "combined_score": round(combined, 3),
            "strong_duplicate": combined >= _STRONG_THRESHOLD,
            "canonical_name": canonical["raw_name"],
            "alias_name": alias["raw_name"],
            "canonical_description": canonical["description"][:200],
            "alias_description": alias["description"][:200],
        })

    pairs.sort(key=lambda p: (-p["combined_score"], p["canonical_id"]))

    PAIRS_OUT.write_text(
        json.dumps(pairs, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown report.
    strong = [p for p in pairs if p["strong_duplicate"]]
    review = [p for p in pairs if not p["strong_duplicate"]]
    lines: list[str] = [
        "# Skills similarity analysis",
        "",
        f"Auto-generated by `scripts/analyze_skill_similarity.py`. "
        f"Inventory: `{INVENTORY.relative_to(REPO_ROOT)}` "
        f"({len(skills)} skills).",
        "",
        f"- Pairs above review threshold ({_REVIEW_THRESHOLD}): **{len(pairs)}**",
        f"  - Strong duplicates (>= {_STRONG_THRESHOLD}): **{len(strong)}** — "
        "candidates for `alias_of` in `config/skills/catalog.yaml`",
        f"  - Borderline ({_REVIEW_THRESHOLD}-{_STRONG_THRESHOLD}): "
        f"**{len(review)}** — manual review",
        "",
        "## Strong duplicates",
        "",
    ]
    for p in strong:
        lines.append(f"### `{p['canonical_id']}` ⇐ `{p['alias_id']}`")
        lines.append(
            f"  Combined: **{p['combined_score']}** "
            f"(slug={p['slug_similarity']}, desc={p['description_similarity']}) "
            f"— scope `{p['scope']}`"
        )
        lines.append(f"  - canonical: {p['canonical_name']} — {p['canonical_description']}")
        lines.append(f"  - alias    : {p['alias_name']} — {p['alias_description']}")
        lines.append("")
    if not strong:
        lines.append("_(none — no strong duplicates detected)_")
        lines.append("")
    lines.extend(["## Borderline (manual review)", ""])
    for p in review:
        lines.append(
            f"- `{p['canonical_id']}` vs `{p['alias_id']}` "
            f"({p['combined_score']:.2f}) — {p['scope']}"
        )
    if not review:
        lines.append("_(none)_")
        lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Pairs JSON: {PAIRS_OUT.relative_to(REPO_ROOT)} ({len(pairs)} pairs)")
    print(f"  strong duplicates: {len(strong)}")
    print(f"  borderline:        {len(review)}")
    print(f"Report:    {REPORT_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
