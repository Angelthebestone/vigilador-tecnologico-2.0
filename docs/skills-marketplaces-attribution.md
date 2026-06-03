# Skills Marketplaces — Attribution

The Vigilador Tecnológico bundles two third-party skill catalogs verbatim
under `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/`
per spec 021 decision **D2** (clone in-tree instead of consuming as a
runtime download).

Each adapter normalizes the upstream skill format into Vigilador's
`SkillCard` / `SkillSummary` / `SkillBody` shape (see
`enterprise/skills_marketplace/skill_models.py`).

## K-Dense — Scientific Agent Skills

| Field | Value |
| --- | --- |
| Repository | https://github.com/K-Dense-AI/scientific-agent-skills |
| Vendor path | `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/k_dense/` |
| Commit pinned | `effb57c5699c1d400ef461a7aa80fc6693939805` |
| License | MIT (see vendored `LICENSE`) |
| Adapter | `enterprise/skills_marketplace/k_dense_adapter.py` |
| Source identifier | `external:k-dense` |
| Skill format | `<vendor>/skills/<id>/SKILL.md` with YAML frontmatter |
| Frontmatter fields used | `name`, `author`, `description`, `license`, `compatibility`, `metadata.version`, `metadata.skill-author` |

## Agency Agents

| Field | Value |
| --- | --- |
| Repository | https://github.com/msitarzewski/agency-agents |
| Vendor path | `src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor/agency_agents/` |
| Commit pinned | `783f6a72bfd7f3135700ac273c619d92821b419a` |
| License | MIT (see vendored `LICENSE`) |
| Adapter | `enterprise/skills_marketplace/agency_agents_adapter.py` |
| Source identifier | `external:agency-agents` |
| Skill format | `<vendor>/<division>/<agent>.md` (single Markdown file per agent) with YAML frontmatter |
| Frontmatter fields used | `name`, `description`, `color`, `emoji`, `vibe` |
| Division → Vigilador taxonomy | division name becomes a tag; first tag is the division id |

## Refresh policy

To upgrade either catalog, run from the repo root:

```powershell
cd src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor
git -C k_dense pull --rebase --autostash
git -C agency_agents pull --rebase --autostash
```

Then update the **Commit pinned** column above with the new hashes and
record the bump in the changelog. Adapters are insulated from upstream
churn by their YAML-frontmatter parser; only field renames break them.

## Out of scope

* The third historical source `external:claude-local` is **dropped from
  runtime** per spec 021 decision **D3**. The adapter file
  `claude_local_adapter.py` remains in the tree as a reference for any
  consumer that wants to opt in manually, but `SkillLoader` no longer
  loads it (FR-033). See `tests/enterprise/skills_marketplace/test_no_claude_local.py`.

* Neither marketplace is hot-reloaded at runtime; the snapshot is taken
  at the commit hash above. A YAML schema mismatch from a future
  upstream change surfaces as `SkillLoader.errors[]` rather than a
  silent skip — the loader is explicit.
