# F1 — Deferred Implementation (Native-first runtime, partial)

**Spec**: 021-mvp-integration-extraction
**Tasks**: T007–T034 (F1.A native-first runtime + tools)
**Created**: 2026-05-30 (during the F1.A-F partial implementation pass)

## Summary

Phase F1.A-F (T007–T034) is **partially complete**. The infrastructure pieces and 3 reference WRAP-SDK tools are in place; the remaining work — most importantly the **MCP client port** and **11 additional WRAP-SDK tools** — needs dedicated sessions because each has its own non-trivial scope (the MCP client alone is 3711 LOC upstream).

This document is the contract for the next sessions.

## Status of F1.A-F

### Done in this pass

| Task | Deliverable | LOC |
|---|---|---|
| **T010 / T011** | `enterprise/mcp/process_supervisor.py` — `MCPProcessSupervisor` with backoff + healthcheck | 313 |
| **T012 / T013** | `enterprise/tooling/mcp_tool_wrapper.py` — `McpToolWrapper` bridge | 101 |
| **T014** | `config/mcp/external.yaml` — empty manifest (audit reports 0 MCP-EXTERNO) | 34 |
| **T015 / T016** | `enterprise/tooling/builtin/research/tavily.py` — WRAP-SDK reference | 111 |
| **T018** | `enterprise/tooling/builtin/research/brave.py` — WRAP-SDK reference | 123 |
| **T023** | `enterprise/tooling/builtin/web/fetch.py` — WRAP-SDK reference | 136 |
| **T034** | `api/enterprise_composition.py::_build_tool_registry` registers the 3 native tools | (modified) |
| **(tests)** | `tests/enterprise/tooling/test_f1_native_first_runtime.py` (16 tests, all green) | 258 |

### Deferred to dedicated sessions

| Task | Why deferred | Estimated effort |
|---|---|---|
| **T007 / T008** — port Hermes `tools/mcp_tool.py` → `enterprise/tooling/mcp_client/` | Upstream is **3711 LOC**; needs real modularization into stdio / http / sse / sampling submodules each ≤400 LOC. Audit shows **0 MCP-EXTERNO providers** today, so the runtime never hits this code path; the port is infrastructure for any future fallback. | 1–1.5 days |
| **T017 / T019 / T020 / T021 / T022 / T024 / T025 / T026 / T027 / T028** — 10 remaining WRAP-SDK tools | Each tool needs: read SDK/REST surface, write wrapper, write 3 unit tests, validate optional dependency installs. **~30–60 min each**, but the pattern is locked down by the 3 reference tools (tavily/brave/fetch). | 6–10 hours |
| **T029 / T030 / T031** — 2 CLONE-UPSTREAM Python MCPs (arxiv, google_scholar) | Already cloned under `.mcp-servers/`. Refactor into `enterprise/tooling/builtin/research/` per ≤400 LOC, with attribution to upstream repos. Includes their own non-Hermes deps (`arxiv` PyPI, `scholarly`). | 3–4 hours |
| **T032** — sandbox tool | Audit conditional: WRAP-SDK over `e2b` if installable, else MCP-EXTERNO fallback (the only candidate to need fallback). | 1–2 hours |
| **T033** — universal-registration test | `test_universal_tool_registration.py` asserting `ToolRegistry` ends with the full 16-provider set after composition. Pending tasks T017–T032 above. | 30 min |

## Modularization plan — Hermes `tools/mcp_tool.py` (T008)

**Total**: 3711 LOC → 4–6 submodules at ≤400 LOC each.

```
documentation/hermes agent/hermes-agent/tools/mcp_tool.py   (3711 LOC)
```

Vigilador destination tree:
```
enterprise/tooling/mcp_client/
├── __init__.py            # public API: connect(), call_tool(), list_tools()
├── transports/
│   ├── stdio.py           # stdio_client + subprocess pipes (~350 LOC)
│   ├── http.py            # httpx-based StreamableHTTP transport (~300 LOC)
│   └── sse.py             # Server-Sent Events transport (~250 LOC)
├── jsonrpc.py             # request/response framing, id management (~250 LOC)
├── sampling.py            # MCP sampling protocol (LLM-as-tool) (~300 LOC)
└── env_filter.py          # subprocess env var allowlist (~150 LOC)
```

### Acceptance criteria

1. Each submodule ≤400 LOC.
2. Header `# Adapted from Hermes Agent — Original file: tools/mcp_tool.py — License: MIT` on each submodule.
3. Each submodule has its own dedicated test file (≥3 tests).
4. Hermes-internal deps adapted: `hermes_constants` → `~/.vigilador`, any `hermes_cli` → settings or dropped.
5. `McpToolWrapper.execute()` (currently raising `NotImplementedError`) replaced by a real implementation that calls `mcp_client.call_tool(name, args)` over the configured transport.
6. Constitución #4 — no defensive `try/except: pass`; protocol errors propagate with context.

## Pattern reference for the 11 remaining WRAP-SDK tools

The 3 reference tools (tavily, brave, fetch) lock down the pattern. Every remaining tool follows the same shape:

```python
from dataclasses import dataclass

import httpx  # or the provider's SDK

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


@dataclass(frozen=True)
class <Provider>Tool:
    name: str = "<id>"            # matches catalog
    domain: str = "<domain>"      # matches catalog
    is_external_mcp: bool = False
    requires_auth: bool = <bool>

    def _api_key(self) -> str | None:
        return os.getenv("VT_<PROVIDER>_API_KEY") or None

    async def healthcheck(self) -> HealthcheckResult:
        # Either: (a) check VT_X_API_KEY presence (no quota burn), OR
        # (b) cheap GET on a public endpoint.
        ...

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        # Dispatch by tool_name → one helper per capability declared in the catalog.
        ...
```

| Provider | Capabilities (from catalog) | SDK / REST | New env var |
|---|---|---|---|
| `exa` | semantic_search, find_similar | exa-py or REST | `VT_EXA_API_KEY` (exists) |
| `serper` | google_search, scholar_search, patent_search, news_search | REST | `VT_SERPER_API_KEY` (exists) |
| `serper_patents` | patent_search, patent_details | REST (alias of serper) | `VT_SERPER_API_KEY` |
| `jina` | reader, extract_content | REST `r.jina.ai` | `VT_JINA_API_KEY` (exists) |
| `firecrawl` | crawl_url, scrape_page, map_site | firecrawl-py | `VT_FIRECRAWL_API_KEY` (exists) |
| `playwright` | navigate, screenshot, click, fill | playwright (Python) | (none — local browser) |
| `openalex` | search_works, get_authors, get_institutions | pyalex / REST | `VT_OPENALEX_API_KEY` (exists) |
| `markitdown` | convert_to_markdown, extract_text | markitdown PyPI | (none) |
| `minimax_image` | generate_image, edit_image | REST | `VT_MINIMAX_IMAGE_API_KEY` (exists) |
| `google_workspace` | read_docs, write_docs, read_sheets, send_email | google-api-python-client + OAuth | `VT_GOOGLE_CLIENT_ID/SECRET` (added Phase 0) |
| `sandbox` | run_code, execute_command | e2b (if available) or MCP fallback | `VT_E2B_API_KEY` (new) |

### Acceptance criteria per tool

1. ≤200 LOC per file (each capability is a thin REST/SDK call).
2. `ToolWrapper` Protocol satisfied — frozen dataclass with the 4 attributes + 2 async methods.
3. Healthcheck returns `UNCONFIGURED` when the env var is missing; `UP` when present.
4. `execute()` raises `ValueError` on unknown `tool_name` with the supported list.
5. Args validation per capability (required fields, type checks).
6. ≥3 unit tests per tool: healthcheck-unconfigured, execute-unknown-capability, args-validation.
7. Wired into `_build_tool_registry` in `api/enterprise_composition.py`.

## CLONE-UPSTREAM plan — `arxiv` and `google_scholar` (T029–T031)

Both already exist under `.mcp-servers/`:

```
.mcp-servers/arxiv/arxiv-mcp-server-0.5.0/
.mcp-servers/google-scholar/Google-Scholar-MCP-Server-main/
```

### Steps per repo

1. Read every `.py` to understand the public surface and dependencies.
2. Modularize into `enterprise/tooling/builtin/research/<id>.py` (+ helpers if needed) ≤400 LOC each.
3. Header `# Adapted from <upstream-repo-url> — License: <upstream license>`.
4. Implement `ToolWrapper` (capabilities from catalog: `search_papers`, `get_paper`, `list_categories` for arxiv; `search_papers`, `get_citations` for google_scholar).
5. Add the upstream's runtime deps to `pyproject.toml` (e.g. `arxiv`, `scholarly`).
6. ≥3 tests per tool with a mocked outbound call.
7. Wire into `_build_tool_registry`.

## Out of scope here

* Any change to the `ToolWrapper` Protocol (spec 009 contract — read-only consumer).
* Any change to `ToolRegistry` (already wired with discovery + gating + 3-level detail).
* The 5 deferred F1.G files (`approval`, `lazy_deps`, etc.) — see `docs/f1g-deferred-modularization.md`.

## Acceptance gate before considering F1.A-F "complete"

* [x] `MCPProcessSupervisor` + `McpToolWrapper` + manifest landed (this session).
* [x] 3 reference WRAP-SDK tools landed + tested (this session).
* [x] Universal registration wired in `enterprise_composition.py` (this session).
* [ ] `mcp_client` modular port landed; `McpToolWrapper.execute()` no longer raises `NotImplementedError`.
* [ ] 10 remaining WRAP-SDK tools landed (exa, serper, serper_patents, jina, firecrawl, playwright, openalex, markitdown, minimax_image, google_workspace).
* [ ] 2 CLONE-UPSTREAM tools landed (arxiv, google_scholar).
* [ ] sandbox tool decision (WRAP-SDK or MCP-EXTERNO) implemented.
* [ ] Universal registration test asserting 16-provider total.
* [ ] Suite 2.0 still 100% green; ruff/basedpyright/layer-imports clean.

**Estimated remaining effort**: ~3 working days (mcp_client port 1.5d + tools 1.5d). Each session can deliver a coherent batch (e.g. all 4 search providers, then all 4 web/research, then productivity+sandbox).
