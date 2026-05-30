# F1.G — Deferred Modularization (Hermes Heavy Files)

**Spec**: 021-mvp-integration-extraction
**Tasks**: T035–T043 (governance + tooling base from Hermes)
**Created**: 2026-05-30 (during the Phase 0 + F1.I + F1.G partial implementation)

## Summary

Of the **11 Hermes governance + tooling base files** that spec 021 task T036–T043 require porting, **9 are done** in this implementation pass and **2 remain deferred** because they exceed the ≤400 LOC `preferencia` (doc 06 §1.1) by enough margin that *real* modularization — not a verbatim port with cohesion justification — is required to honor constitución v1.2.0 #2 (Simplicidad) and #3 (Modularidad).

This document is the contract for the next session that implements them.

## Status of F1.G

| Hermes file | LOC | Status | Destination |
|---|---|---|---|
| `tools/path_security.py` | 43 | ✅ ported | `enterprise/governance/path_security.py` |
| `tools/tool_output_limits.py` | 92 | ✅ ported | `enterprise/tooling/output_limits.py` |
| `tools/interrupt.py` | 98 | ✅ ported | `enterprise/governance/approvals/interrupt.py` |
| `tools/slash_confirm.py` | 167 | ✅ ported | `enterprise/governance/approvals/slash_confirm.py` |
| `tools/website_policy.py` | 282 | ✅ ported | `enterprise/governance/website_policy.py` |
| `tools/url_safety.py` | 351 | ✅ ported | `enterprise/governance/url_safety.py` |
| `agent/file_safety.py` | 453 | ✅ ported (subset, **249 LOC**) | `enterprise/governance/file_safety.py` |
| `tools/schema_sanitizer.py` | 445 | ✅ ported (whole, 439 LOC, cohesion note) | `enterprise/tooling/schema_sanitizer.py` |
| `agent/redact.py` | 504 | ✅ ported (whole, 461 LOC, cohesion note) | `enterprise/governance/redact.py` |
| `tools/lazy_deps.py` | 616 | ⏸ **deferred** | `enterprise/tooling/lazy_deps/` (split) |
| `tools/approval.py` | 1441 | ⏸ **deferred** | `enterprise/governance/approvals/approval/` (split into 3–4 modules) |

## Why these two are deferred (not just ported whole)

Both `approval.py` (1441 LOC) and `lazy_deps.py` (616 LOC) are large enough that the cohesion-justification escape valve used for `schema_sanitizer.py` and `redact.py` does **not** apply:

* **`schema_sanitizer.py`** (445 LOC, 11% over) — every function consults the same `_sanitize_node` tree-walk; splitting forces redundant `import *` and breaks the deep co-evolution. *Single concern.*
* **`redact.py`** (461 LOC, 15% over after porting) — patterns + redactor + gating substrings are tightly co-evolved. *Single concern.*
* **`approval.py`** (1441 LOC, 260% over) — multiple distinct concerns (state machine, persistence, callbacks, transport-specific UI, rule matching). *Real modularization required.*
* **`lazy_deps.py`** (616 LOC, 54% over) — multiple concerns (lazy loader, fallback resolution, dependency graph). *Real modularization required.*

A verbatim port of these two would either:
1. Violate constitución #3 (one module, multiple responsibilities), or
2. Invite the next reader to assume artificial splits are acceptable, eroding the standard.

## Modularization plan — `approval.py`

**Total**: ~1441 LOC → 3–4 modules at ~300–400 LOC each.

Hermes upstream:
```
documentation/hermes agent/hermes-agent/tools/approval.py   (1441 LOC)
```

Vigilador destination tree:
```
enterprise/governance/approvals/approval/
├── __init__.py            # public API re-exports
├── state.py               # PendingApproval dataclass + lifecycle states (~250 LOC)
├── store.py               # in-memory + persisted store (lock, TTL, dedup) (~300 LOC)
├── matchers.py            # rule matching (file paths, command shapes, allowlists) (~350 LOC)
└── runner.py              # request→prompt→resolve flow + adapter callbacks (~400 LOC)
```

### Acceptance criteria for `approval/` split

1. Each submodule ≤ 400 LOC (constitución #2 KISS, doc 06 §1.1).
2. `__init__.py` re-exports the same public names that callers import from upstream `approval`.
3. Each submodule has its own dedicated test file (3 tests minimum: input válido / inválido / edge case).
4. Header `# Adapted from Hermes Agent — Original file: tools/approval.py — License: MIT` on each submodule.
5. Hermes-internal deps adapted: `hermes_constants.get_hermes_home()` → `Path("~/.vigilador").expanduser()`; any `hermes_cli.config` reference → settings or dropped.
6. No defensive `try/except: pass` — every error propagates with context per constitución #4.

### Suggested split rationale

* **`state.py`**: pure data — `PendingApproval` dataclass, status enum, TTL helpers. No I/O.
* **`store.py`**: thread-safe pending-approval registry. Persistence to JSONL audit. Dedup. Time-out clean-up.
* **`matchers.py`**: rule resolution — given a tool call, decide whether it requires approval (path-based, command-based, allowlist).
* **`runner.py`**: orchestration — `request()` creates state, surfaces prompt via adapter, awaits resolution, re-runs the gated tool. The platform adapter callback layer.

The split mirrors the natural responsibilities upstream Hermes has buried in one file.

## Modularization plan — `lazy_deps.py`

**Total**: ~616 LOC → 2 modules at ~300 LOC each.

Hermes upstream:
```
documentation/hermes agent/hermes-agent/tools/lazy_deps.py   (616 LOC)
```

Vigilador destination tree:
```
enterprise/tooling/lazy_deps/
├── __init__.py        # public API re-exports
├── loader.py          # lazy import + ImportError → installation hint (~300 LOC)
└── registry.py        # known-package registry (name → pip spec, optional features) (~300 LOC)
```

### Acceptance criteria for `lazy_deps/` split

Same as `approval/` (≤400 LOC per submodule, attribution, tests, no defensive try/except). The split between `loader` (the runtime lazy-import machinery) and `registry` (the static catalogue of known packages) is natural and already implicit in upstream.

## Tests required

After modularization:

* `tests/enterprise/governance/approvals/test_approval_{state,store,matchers,runner}.py` — one file per submodule, ≥3 tests each.
* `tests/enterprise/tooling/lazy_deps/test_{loader,registry}.py` — one file per submodule, ≥3 tests each.

The smoke tests in `tests/enterprise/governance/test_hermes_governance_ports.py` and `tests/enterprise/governance/test_hermes_borderline_ports.py` cover the 9 already-ported files; the new tests are additive.

## Out of scope here

* Wiring `approval.py` into the runtime (PlaybookRunner gates) — that lands in F4a.
* Wiring `lazy_deps.py` into the tool-loading path — that lands in F1.C native tools (T015–T032), where each WRAP-SDK tool registers its lazy dep.

## Estimated effort

* `approval.py` modularization + tests: ~6–8 hours (4 submodules, ~12 tests, careful state-machine reading).
* `lazy_deps.py` modularization + tests: ~3–4 hours (2 submodules, ~6 tests).
* **Total**: ~10–12 hours (1.5 working days for one engineer).

## Acceptance gate before considering F1.G "complete"

* [x] 9 of 11 files ported with attribution + tests (this session).
* [ ] `approval/` submodule split landed + tests green.
* [ ] `lazy_deps/` submodule split landed + tests green.
* [ ] Final F1.G verification: `pytest tests/enterprise/governance/ tests/enterprise/tooling/` all green; `ruff check` clean; `check-layer-imports.py` OK; suite 2.0 unaffected (cero regresiones).
