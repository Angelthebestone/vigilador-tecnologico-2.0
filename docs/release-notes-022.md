# Release Notes — Spec 022: Backend Optimization

**Date**: 2026-06-02
**Version**: 0.1.0

## Overview

Spec 022 implements comprehensive backend optimizations across 6 phases (145 tasks), improving performance, reducing LOC, and modernizing the provider layer.

## Key Changes

### Phase 1: Base Infrastructure (T006-T020)
- Created `BaseHTTPProvider` with retry policy for HTTP-based tools
- Created `EmbeddingCache` (two-tier L1/L2) for tool and skill embeddings
- Added `get_statuses_batch()` to `ToolHealthRepository`

### Phase 2: Tool Registry Optimization (T021-T030)
- Pre-computed embeddings during tool registration
- Batch status fetching in `discover()`
- Injected `EmbeddingCache` into `ToolRegistry` and `enterprise_composition.py`

### Phase 3: Skills Boot Optimization (T031-T060)
- Frontmatter-only reads in K-Dense and Agency-Agents adapters
- Cold skills archiving (131 directories moved to `_cold/`)
- `HashTracker.save_all()` batch write
- `@lru_cache` on Gemini `embed()`, batch size 100 in `embed_documents()`
- `VT_COLD_SKILLS_ENABLED` setting for optional cold skill activation

### Phase 4: Provider Migration (T061-T100)
- **SDK Migrations** (5 providers):
  - Tavily: `tavily-python` SDK
  - OpenAlex: `pyalex` SDK
  - Arxiv: `arxiv` SDK
  - Exa: `exa-py` SDK
  - Firecrawl: `firecrawl-py` SDK
- **BaseHTTPProvider Migrations** (1 provider):
  - Brave: subclass with `X-Subscription-Token` auth

### Phase 5: Composition Root Split (T101-T115)
- Split `dependencies.py` (646 LOC) into 12 submodules
- Created `_singletons.py` with `@lru_cache` factories
- Lazy imports for WS-A/B/C/D/E modules

### Phase 6: Correctness + Cleanup (T116-T145)
- Per-tenant locks in `TurboVecIndex` for concurrent write safety
- `os.fsync()` in `AuditLog` and `PIQuarantineJSONLWriter`
- Configurable DB pool size (`VT_DB_POOL_SIZE`, `VT_DB_POOL_OVERFLOW`)
- LRU eviction in `MCPSmartCache` (`VT_MCP_CACHE_MAX_ENTRIES`)
- Dead code removal (playwright_mcp, minimax_image_mcp, claude_local_adapter)
- Prompts wiring: `get_docs()` loads from `prompts/tools/{name}.txt`

## Files Created

- `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/` — BaseHTTPProvider + RetryPolicy
- `src/vigilancia_multiagente/infra/embeddings/embedding_cache.py` — Two-tier cache
- `src/vigilancia_multiagente/api/dependencies/` — Split composition root (12 files)
- `tests/enterprise/tooling/test_tavily_sdk.py` — Tavily SDK tests
- `tests/enterprise/tooling/test_pyalex_migration.py` — OpenAlex SDK tests
- `tests/enterprise/tooling/test_arxiv_sdk.py` — Arxiv SDK tests
- `tests/enterprise/tooling/test_exa_sdk.py` — Exa SDK tests
- `tests/enterprise/tooling/test_firecrawl_sdk.py` — Firecrawl SDK tests
- `tests/enterprise/tooling/test_brave_sdk.py` — Brave BaseHTTPProvider tests
- `tests/enterprise/skills_marketplace/test_cold_skills_excluded.py` — Cold skills tests
- `tests/enterprise/skills_marketplace/test_cold_skills_included.py` — Cold skills tests
- `tests/enterprise/skills_marketplace/test_frontmatter_only_read.py` — Frontmatter tests
- `tests/enterprise/skills_marketplace/test_hash_tracker_save_all.py` — Hash tracker tests
- `tests/enterprise/skills_marketplace/test_skill_registry_cache.py` — Registry cache tests

## Files Modified

- `pyproject.toml` — Added SDK dependencies
- `src/vigilancia_multiagente/config/settings.py` — `cold_skills_enabled` setting
- `src/vigilancia_multiagente/enterprise/tooling/builtin/research/tavily.py` — SDK migration
- `src/vigilancia_multiagente/enterprise/tooling/builtin/research/openalex.py` — SDK migration
- `src/vigilancia_multiagente/enterprise/tooling/builtin/research/arxiv.py` — SDK migration
- `src/vigilancia_multiagente/enterprise/tooling/builtin/research/exa.py` — SDK migration
- `src/vigilancia_multiagente/enterprise/tooling/builtin/research/firecrawl.py` — SDK migration
- `src/vigilancia_multiagente/enterprise/tooling/builtin/research/brave.py` — BaseHTTPProvider
- `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_registry.py` — EmbeddingCache
- `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py` — Cold skills
- `src/vigilancia_multiagente/enterprise/skills_marketplace/k_dense_adapter.py` — Frontmatter
- `src/vigilancia_multiagente/enterprise/skills_marketplace/agency_agents_adapter.py` — Frontmatter
- `src/vigilancia_multiagente/enterprise/skills_marketplace/hash_tracker.py` — Batch save
- `src/vigilancia_multiagente/infra/embeddings/gemini_gateway.py` — LRU cache + batch
- `src/vigilancia_multiagente/infra/persistence/turbovec_index.py` — Tenant locks
- `src/vigilancia_multiagente/infra/db/connection.py` — Pool config
- `src/vigilancia_multiagente/infra/mcp/mcp_cache.py` — LRU eviction
- `src/vigilancia_multiagente/enterprise/governance/audit_log.py` — fsync
- `src/vigilancia_multiagente/enterprise/governance/pi_quarantine_writer.py` — fsync
- `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` — Prompts wiring

## Files Removed

- `src/vigilancia_multiagente/infra/mcp/playwright_mcp.py`
- `src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py`
- `src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py`
- `src/vigilancia_multiagente/api/dependencies.py` (replaced by package)

## Verification

- All SDK migration tests pass (32/32)
- All skills marketplace tests pass
- All tooling tests pass
- All infra tests pass
