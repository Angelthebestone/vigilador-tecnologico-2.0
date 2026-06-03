# Specification Quality Checklist: Backend Optimization & Google Workspace MCP Revert

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-01
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

**Notes**:
- Reference a algunos paquetes Python (`tavily-python`, `pyalex`, etc.) en FRs es deliberado — el FR identifica QUÉ migrar, no CÓMO; estos son targets de migración concretos del scope, no detalles de implementación. La elección entre SDK y BaseHTTPProvider es estratégica (assumption A-01).
- Reference a `~/.vigilador/cache/` paths es operacional (config), no implementation.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (las 9 decisiones del usuario ya están cerradas en Assumptions)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (todos con métricas concretas: <5s, <200ms, ≥25 capabilities, etc.)
- [x] Success criteria are technology-agnostic (NO mencionan frameworks específicos en SCs)
- [x] All acceptance scenarios are defined (10 escenarios cubriendo perf, MCP revert, retry, concurrency, audit, dev-ergonomy)
- [x] Edge cases are identified (8 EC-XX casos específicos)
- [x] Scope is clearly bounded (In Scope vs Out of Scope con listas explícitas)
- [x] Dependencies and assumptions identified (14 assumptions A-01..A-14)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria (15 SCs cuantitativos)
- [x] No implementation details leak into specification

**Validación cruzada SC ↔ FR**:
- SC-001 (cold start <5s) ← FR-001 (embedding precompute) + FR-003 (skill embed cache) + FR-018 (lazy WS imports)
- SC-002 (discover p95 <200ms) ← FR-001 + FR-002 (batch SQL)
- SC-004 (≥25 capabilities Google Workspace) ← FR-009 (MCP declared) + FR-010 (WRAP-SDK removed) + FR-011 (catalog updated)
- SC-005 (Tavily 99% success vs 503) ← FR-012 (SDK migration) o FR-013 (BaseHTTPProvider retry policy)
- SC-006 (concurrent ingestion) ← FR-019 (TurboVec lock per-tenant)
- SC-007 (sync flush audit) ← FR-020 (sync flush AuditLog) + FR-021 (sync flush PIQuarantine)
- SC-008 (suite <30s) ← FR-024 (_roadmap exclusion)
- SC-009 (≤400 LOC) ← FR-016 (dependencies split)
- SC-010 (2.0 preserved) ← FR-027/028/029 (no diff baseline)
- SC-011 (-5% LOC) ← FR-022 (dead code) + FR-014 (BaseHTTPProvider consolidation) + FR-012 (SDK migration)
- SC-013 (provider contract) ← FR-013 + FR-014
- SC-014 (≥45 total capabilities) ← FR-009/010/011

## Spec-021 Alignment

- [x] D1 (TurboVec único) preservada (FR-019 añade lock, no cambia contract)
- [x] D2 (_vendor en src) preservada (`_cold/` es subpath, no relocates)
- [x] D3 (NO .claude/skills runtime) consolidada (FR-022 elimina claude_local_adapter)
- [x] D4 (NO user auth) preservada (Google Workspace MCP usa OAuth de servicio igual)
- [x] D5 (native-first) reafirmada con prioridad SDK > BaseHTTPProvider > MCP-EXTERNO
- [x] MVP scope C1 preservado (20 caps + expansión productivity vía MCP, sin alterar 4 dominios MVP)

## Constitución v1.2.0 Alignment

- [x] SRP en cada módulo nuevo o modificado
- [x] ≤400 LOC/file (FR-016 elimina 1 violación, FR-014 evita crear nuevas)
- [x] Explicit errors (FR-013 retry policy + EC-08 lock timeout)
- [x] CQS preservado
- [x] DIP preservado
- [x] KISS/YAGNI (A-01 SDK criteria + F-01..F-10 anti-patterns en sintesis)
- [x] #5 cambios quirúrgicos (O-01..O-05 operational constraints)

## Notes

- Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`
- Validación pasada en iteración 1 (no se requirieron iteraciones adicionales).
- Documento de síntesis técnica `docs/optimization/synthesis_plan_v1.md` ya existe como SSOT del análisis (520 LOC, generado por sub-agentes deep-dive).
- Pre-execution check: el `before_specify` git hook (`speckit.git.feature`) fue **skip-eado deliberadamente** porque crea branch + auto-commit, lo que violaría la directiva del usuario de NO commits/pushes en esta sesión. Este bypass se documenta aquí; cuando el spec llegue a `/speckit.plan` el usuario puede decidir si reactivar el hook.
