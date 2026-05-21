# Implementation Plan: Multi-Agent System Enhancements v2

## Problem

The current multi-agent technology surveillance system collects information but cannot analyze it programmatically, lacks cross-session memory, has a passive execution planner, supports only single-use interactions, cannot convert documents or automate browser interactions, produces one-size-fits-all reports, makes no trend predictions, and treats all sources equally. These limitations prevent the system from functioning as a continuous intelligence platform.

## Approach

Implement nine interconnected components across the existing architecture: (A) analytical sandbox MCP for code execution and bibliometrics, (B) document conversion via Markitdown MCP, (C) browser automation via Playwright MCP, (D) reactive planner with signal-driven replanning, (E) cross-session memory using pgvector, (F) continuous conversation mode, (G) trend forecasting agent, (H) multi-stakeholder reporting, and (I) source trust scoring. Each component is a self-contained module with clear interfaces, registered through the existing MCP provider pattern.

---

## Technical Context

| Area | Decision |
|------|----------|
| Sandbox transport | Python STDIO MCP server with `execute_code` and `list_libraries` tools |
| Sandbox libraries | matplotlib, seaborn, numpy, pandas, metaknowledge, PySciSci, scienceplots |
| Document conversion | `markitdown-mcp` pip package, STDIO transport |
| Browser automation | `@playwright/mcp` npx package, STDIO transport |
| Reactive planner | Extend `BranchCoordinator` with `asyncio.wait(FIRST_COMPLETED)` + signal consumer loop |
| Cross-session storage | PostgreSQL + pgvector (existing), new `GlobalKnowledgeRepository` |
| Embeddings | Gemini (existing `GeminiEmbeddingGateway`) |
| Trend forecasting | scipy.optimize + numpy in sandbox |
| Reporting variants | Prompt-based synthesis from existing findings |
| Source scoring | Weighted scoring (confirmation ratio + recency + diversity), persisted in PostgreSQL |
| Config pattern | Pydantic Settings with `VT_` prefix (existing pattern) |
| MCP registration | `mcp-providers.json` + `provider_registry.py` + `mcp_cache.py` (existing pattern) |

## External Constraints

| Constraint | Impact |
|------------|--------|
| `VT_MINIMAX_API_KEY` no disponible | No se puede usar MiniMax para nuevas features; todo el pipeline de LLM sigue en modo fallback |
| `reasoning_split=True` ya hardcodeado | No cambiar config de MiniMax; el split de razonamiento ya existe |
| Sandbox no debe tener acceso a red | El sandbox MCP debe ejecutarse en subproceso aislado sin conexión |
| STDIO MCP es el estándar del proyecto | Los 3 nuevos MCPs (sandbox, markitdown, playwright) usan STDIO |
| Las librerías científicas requieren formatos específicos | metaknowledge requiere WoS/Scopus exports; PySciSci requiere DataFrames con citing/cited/year |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/infra/mcp/sandbox/__init__.py` | Sandbox MCP package init |
| `src/vigilancia_multiagente/infra/mcp/sandbox/server.py` | Sandbox MCP STDIO server with execute_code and list_libraries tools |
| `src/vigilancia_multiagente/infra/mcp/sandbox/analytics.py` | Bibliometric analysis functions (novelty, clusters, next_queries) |
| `src/vigilancia_multiagente/infra/mcp/markitdown_mcp.py` | Markitdown MCP provider wrapper |
| `src/vigilancia_multiagente/infra/mcp/playwright_mcp.py` | Playwright MCP provider wrapper |
| `src/vigilancia_multiagente/domain/global_knowledge.py` | Cross-session memory entity (GlobalKnowledgeSnapshot) |
| `src/vigilancia_multiagente/infra/persistence/global_knowledge_repository.py` | PostgreSQL repository for cross-session memory |
| `src/vigilancia_multiagente/application/memory/cross_session_service.py` | Service for cross-session retrieval and merging |
| `src/vigilancia_multiagente/domain/conversation_state.py` | Session continuation state entity |
| `src/vigilancia_multiagente/application/conversation/conversation_service.py` | Post-research Q&A service |
| `src/vigilancia_multiagente/domain/trend_projection.py` | Trend projection entity |
| `src/vigilancia_multiagente/application/forecasting/trend_forecaster.py` | Trend forecasting service (orchestrates sandbox analysis) |
| `src/vigilancia_multiagente/domain/report_variant.py` | Report variant entity |
| `src/vigilancia_multiagente/application/reporting/report_generator.py` | Multi-stakeholder report generation |
| `src/vigilancia_multiagente/domain/source_trust.py` | Source trust entity |
| `src/vigilancia_multiagente/infra/persistence/source_trust_repository.py` | PostgreSQL repository for source trust scores |
| `src/vigilancia_multiagente/application/routing/source_scorer.py` | Source scoring service |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/infra/mcp/mcp-providers.json` | Add sandbox, markitdown, playwright provider entries |
| `src/vigilancia_multiagente/infra/mcp/provider_registry.py` | Register 3 new providers in `ensure_standard_providers()` |
| `src/vigilancia_multiagente/infra/mcp/mcp_cache.py` | Add cache TTLs for sandbox, markitdown, playwright tools |
| `src/vigilancia_multiagente/application/execution/branch_coordinator.py` | Add reactive planner (signal consumer loop, mid-execution replanning) |
| `src/vigilancia_multiagente/application/orchestration/orchestrator_service.py` | Add cross-session preload, conversation mode, trend forecaster, multi-report hooks |
| `src/vigilancia_multiagente/config/settings.py` | Add env vars for new services |
| `.env.example` | Document new environment variables |
| `src/vigilancia_multiagente/api/dependencies.py` | Wire new services into DI graph |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Alignment**:
  - **Pensar Antes de Codificar**: All design decisions documented in Technical Context; assumptions explicitly listed
  - **Simplicidad Obligatoria**: Each component has single responsibility; no over-engineering; using existing patterns (MCP STDIO, provider registry, DI)
  - **Modularidad Primero**: 9 independent components, each in its own module; clear interfaces through MCP tools and repository patterns
  - **Cambios Quirurgicos y Trazables**: Every new file and modification mapped to a specific component; no lateral refactors
  - **Entrega Verificable**: Success criteria defined per component with measurable outcomes

---

## Phases

### Phase 0 — Research & Design

1. Design data models for cross-session memory (GlobalKnowledgeSnapshot)
2. Design data models for source trust scoring
3. Design conversation state machine
4. Design sandbox execution protocol
5. Review existing BranchCoordinator signal infrastructure

**Output**: research.md, data-model.md, contracts/

### Phase 1 — Infrastructure & MCP Services (Components A, B, C)

1. Create sandbox MCP server with execute_code tool
2. Add bibliometric analysis functions to sandbox
3. Register sandbox in mcp-providers.json and provider_registry
4. Create Markitdown MCP provider wrapper and register
5. Create Playwright MCP provider wrapper and register
6. Add cache TTLs for sandbox, markitdown, playwright tools
7. Add environment variables for new services

**Output**: Sandbox MCP running, Markitdown + Playwright registered

### Phase 2 — Reactive Planner (Component D)

1. Implement signal consumer loop in BranchCoordinator
2. Implement replanning logic (route new directives based on signals)
3. Add replanning iteration limiter
4. Log all replanning decisions

**Output**: BranchCoordinator with mid-execution replanning

### Phase 3 — Cross-Session Memory (Component E)

1. Implement GlobalKnowledgeSnapshot entity and repository
2. Implement cross-session retrieval service
3. Integrate cross-session preload into OrchestratorService
4. Implement session timeline view

**Output**: Sessions can access prior knowledge

### Phase 4 — Continuous Conversation (Component F)

1. Implement session continuation state
2. Implement conversation service (query from graph, supplementary search)
3. Wire conversation mode into OrchestratorService
4. Add idle timeout and session cleanup

**Output**: Users can continue exploring after research completes

### Phase 5 — Trend Forecasting (Component G)

1. Implement trend forecaster service (scans collected data, invokes sandbox)
2. Integrate as post-execution step in OrchestratorService
3. Return structured projections for report inclusion

**Output**: Post-research trend projections

### Phase 6 — Multi-Stakeholder Reporting (Component H)

1. Implement report variant entity
2. Implement report generator with 3 prompt templates
3. Integrate into OrchestratorService post-fuse step

**Output**: Multiple report variants from same findings

### Phase 7 — Source Trust Scoring (Component I)

1. Implement SourceTrustRecord entity and repository
2. Implement source scoring service
3. Integrate confirmation/contradiction detection into findings pipeline
4. Wire scoring into SmartToolRouter / source selection

**Output**: Source trust scores that evolve with use

---

## Rollout Strategy

All components can be developed and tested independently in parallel since they are modular and have clear interfaces:

- **Tier 1 (MVP)**: Sandbox + Markitdown + Playwright MCPs (Components A, B, C) — enables immediate analytical and data-access improvements
- **Tier 2**: Reactive Planner (Component D) — changes core execution model
- **Tier 3**: Cross-Session Memory + Conversation (Components E, F) — changes user interaction model
- **Tier 4**: Trend Forecaster + Reporting + Scoring (Components G, H, I) — value-add services on top

Each tier is independent and can be tested before the next begins.

---

## Success Criteria

- **SC-001**: All 3 new MCPs register and respond to tool calls within 5 seconds
- **SC-002**: BranchCoordinator processes mid-execution signals and replans within 10 seconds
- **SC-003**: A new session retrieves related prior findings from cross-session memory
- **SC-004**: User can ask 5+ follow-up questions after research without triggering new investigation
- **SC-005**: Trend forecaster produces projections for any time-series with ≥4 data points
- **SC-006**: Three distinct report variants generated from one session's findings
- **SC-007**: Source trust scores change after confirmation/contradiction events

## Constitution Check (Post-Design)

- **Status**: PASS
- **Justification**: The plan respects all constitutional principles. Each component has a single responsibility and clear interfaces (Modularidad Primero). No over-engineering — components use existing patterns (MCP STDIO, provider registry). Changes are surgical (every file maps to a specific component). Success criteria are verifiable (Entrega Verificable). Assumptions are explicitly documented (Pensar Antes de Codificar). Complexity is constrained to what was requested (Simplicidad Obligatoria).
