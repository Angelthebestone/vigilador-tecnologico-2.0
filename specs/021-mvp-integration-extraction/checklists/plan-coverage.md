# Plan v3.0 Coverage Checklist: 021 Integracion Runtime MVP

**Purpose**: Verificar, documento por documento del set `plan vigilador 3.0/`, que los requisitos del **MVP (F0-F5a)** quedan cubiertos por spec/plan 021, y marcar explicitamente lo que NO esta cubierto (gaps reales) vs lo diferido a roadmap por decision del propio plan (00b).
**Created**: 2026-05-29
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Leyenda**: `[x]` cubierto por 021 (con traza) · `[~]` cubierto parcialmente / depende de otra spec · `[ ]` **GAP real** (MVP no cubierto en 021) · `(roadmap)` diferido legitimamente por 00b (no es gap).

**Documentos leidos** (set activo, 14): README, 00-canon, 00b-mvp-scope, 01-vision, 02-modos, 03-playbooks, 04-skills, 05-autoaprendizaje, 06-catalogo-tools, 07-migracion, 08-gobernanza, ANEXO-A, ANEXO-B, GLOSARIO. `_archive/` (historico) y `v3-enterprise-toolkit-extraction.md` (deprecado) excluidos.

---

## 00 — Canon operativo (C0 #1-#16)

- [x] CHK001 #1 Frontend como consola principal → 021 FR-046/050 (4 superficies MVP, sin login per D4; superficies post-MVP artefactos/optimizacion/admin = roadmap F5c).
- [x] CHK002 #2 Embeddings/reranker API seleccionables → 021 FR-014 (reuso `GeminiEmbeddingGateway`/`SemanticReranker`) + FR-049 (seleccion `embedding_provider`/`reranker_provider`).
- [x] CHK003 #3 Preservar workstreams/modulos/ports/infra del 2.0 → 021 FR-023 + Delivery Constraints (#5).
- [x] CHK004 #4 TurboVec indice vectorial unico (sin pgvector) → 021 FR-009/010/011 (**nativo in-process** via paquete PyPI `turbovec`, D1 revisada).
- [x] CHK005 #5 Modos sensibles a pais/departamento/municipio → 021 FR-021 (`company_geo`).
- [x] CHK006 #6 Adapter por modelo/proveedor → spec 009 (LLM Xiaomimimo); 021 A-07 lo reusa.
- [x] CHK007 #7 Importar skills/comandos → **corregido D3**: se DROPEA `.claude` local; se usan marketplaces (FR-031/032).
- [x] CHK008 #8 Decisiones obsoletas marcadas → plan §Deprecated D.
- [x] CHK009 #9 Discovery semantico + carga progresiva (tools/skills) → tools=spec 018; skills=021 FR-034.
- [x] CHK010 #10 Hermes/OpenClaw modularizado antes del core → 021 FR-025/026/027.
- [x] CHK011 #11 Sin quotas por usuario → 021 FR-038.
- [ ] CHK012 #12 Automantenimiento admin de repos clonados → **(roadmap F5b)**; no MVP.
- [x] CHK013 #13 Catalogo SSOT con origen/estado/estrategia/ownership → spec 018; 021 lo reusa (FR-002).
- [x] CHK014 #14 Indexacion empresarial cloud+local por connectors/MCPs → 021 FR-012/013 (Drive primero; OneDrive/local_fs/Outlook/Gmail declarados).
- [ ] CHK015 #15 Modulo optimizacion (ISO/NTC) → **(roadmap F4b, company-optimization)**; no MVP.
- [ ] CHK016 #16 Modulo artefactos (dashboards/pipelines) → **(roadmap F4b, artifact-development)**; no MVP.

## 00b — Alcance MVP (C1)

- [x] CHK017 C1.1 LLM default Xiaomimimo `mimo-v2-flash` → spec 009; 021 A-07.
- [x] CHK018 C1.2 Tiers 1 y 2 conservados → 021 Tabla 1 (16 MCP) + Tabla 2/3 (Tier 1).
- [x] CHK019 C1.3 4 dominios MVP (search/web/research/documents) → 021 inventario + catalogo.
- [x] CHK020 C1.4 Google Workspace MCP como unica adicion Tier 2 → 021 FR-007 (`google_workspace`).
- [x] CHK021 C1.5 Dominios nuevos documentados, no implementados → **(roadmap)**; 021 no los implementa.
- [x] CHK022 C1.6 Frontend MVP (4 superficies, sin login per D4) → 021 FR-046/050 (GAP-1 incorporado).
- [x] CHK023 MVP exit #3 indexar 100 docs via Drive → 021 SC-004.
- [x] CHK024 MVP exit #4 Vigilancia Tech corre 6 ramas 2.0 → 021 SC-005.
- [x] CHK025 MVP exit #5 default→general con 20 tools → 021 SC-006/SC-002.
- [x] CHK026 MVP exit #6 CEO→deep-research structured+free-form → 021 SC-006.
- [x] CHK027 MVP exit #7 supervisor levanta MCPs → **reinterpretado bajo D5 (native-first)**: la mayoria de proveedores son tools nativas; el supervisor levanta solo los que queden como MCP fallback (0..N). 021 SC-001/FR-053.
- [x] CHK028 MVP exit #8 tool-gating sin API key → 021 SC-012/FR-042.
- [x] CHK029 MVP exit #9 audit trail JSONL → 021 FR-045.
- [x] CHK030 MVP exit #10 tests E2E 20 tools → 021 SC-002.
- [x] CHK031 MVP exit #1/#2 frontend + onboarding <15min → 021 FR-046/047 + SC-013 (GAP-1/GAP-2 incorporados).

## 01 — Vision y arquitectura

- [x] CHK032 Jerarquia Channel→Mode→Playbook→Agent→Skill→Capability→Tool → 021 FR-017..024 + Key Entities.
- [x] CHK033 Estructura `enterprise/` (mcp, ingestion, memory, modes, orchestration, tooling, governance, dreaming, skills_marketplace) → 021 Files to Create.
- [x] CHK034 Ports nuevos: `vector_index` (TurboVecIndex nativo), `ingestion_connector`, `mode_resolution_strategy`, `channel_adapter` → 021 FR-010/013/019 (channel_adapter = web/SSE existente).
- [x] CHK035 Stack: Xiaomimimo + Gemini + Cohere + TurboVec + PostgreSQL + JSONL/YAML → 021 Technical Context + Variables.
- [ ] CHK036 `enterprise/optimization/` + `enterprise/artifacts/` subcarpetas → **(roadmap F4b)**.

## 02 — Modos y personalidades

- [x] CHK037 Entidad Mode (soul_overlay, company_subset, company_geo, skills, playbooks, tools, mode_settings) → 021 FR-021.
- [x] CHK038 ModeResolver 5 pasos (explicit→canal→heuristica→LLM→default) → 021 FR-019.
- [x] CHK039 ModeContext frozen snapshot + rebuild en `/mode` → 021 FR-019 (`enterprise/modes/mode_context.py`).
- [x] CHK040 ModeLoader validacion en boot → 021 FR-020.
- [x] CHK041 3 modos MVP (`default`, `vigilancia-tech`, `CEO`) → 021 FR-021; modos roadmap deprecados (§Deprecated C).
- [x] CHK042 6 reglas de composicion Mode↔Playbook↔Skill → 021 FR-018/019 (PlaybookRunner valida `mode_compatible`).

## 03 — Playbooks y orquestacion

- [x] CHK043 PlaybookRunner (carga YAML, valida modo, instancia agents, flow) → 021 FR-018.
- [x] CHK044 ComplexityClassifier (SIMPLE/MODERADA/COMPLEJA) → 021 FR-017.
- [x] CHK045 3 playbooks MVP: `technology-watch` (envuelve BranchCoordinator 2.0), `deep-research`, `general` → 021 FR-022/023/024.
- [x] CHK046 Flow types `sequential`/`rounds` MVP; `dag`/`hierarchical` → **(roadmap)** 021 FR-018.
- [x] CHK047 SubagentRegistry (spawn/track basico) → 021 FR-051 (GAP-4 incorporado; pause/resume/approval = roadmap).
- [x] CHK048 Playbooks avanzados (decision-debate, market-research, goal-pursuit, etc.) → **(roadmap F4b)**; deprecados §C.

## 04 — Skills y capacidades

- [x] CHK049 Marketplaces externos K-Dense + agency-agents clonados en `src/` → 021 FR-031 (D2, `_vendor/`).
- [x] CHK050 Adapters `k_dense_adapter` + `agency_agents_adapter` → 021 FR-032.
- [x] CHK051 SkillLoader (prioridad curated>learned>external; sin `external:claude-local`) → 021 FR-033 (D3).
- [x] CHK052 SkillRegistry + discovery 3 niveles (SkillCard/Summary/Body) → 021 FR-034.
- [x] CHK053 Skill `unavailable` si faltan `required_capabilities` → 021 FR-035.
- [x] CHK054 Schema unificado SKILL.md + license/origin/hash → 021 FR-031/032 (registra repo/licencia/hash).
- [x] CHK055 CommandSkill model (comando parametrizable) → 021 FR-052 (GAP-5 incorporado; soporte en `SkillLoader` para comandos de marketplace con sandbox/aprobacion).
- [x] CHK056 Skill curator lifecycle (pull/quarantine/revalidate) → **(roadmap)**.

## 05 — Autoaprendizaje y autonomia

- [x] CHK057 Dreaming scheduler (APScheduler cron 3AM + idle 10min) → 021 FR-039.
- [x] CHK058 Dreaming MVP = SOLO `memory_consolidation` + `ingestion_sync` → 021 FR-040.
- [x] CHK059 Resto de fases (2-4,6-10) + 5-7 loops + agent_modifier + tabla `agent_modifications` + anomaly_detector → **(roadmap F5b)**; deprecados §C/FR-041.
- [x] CHK060 Busqueda normativa localizada en Dreaming → **(roadmap, loop regulatory_watcher)**.

## 06 — Catalogo tools y extraccion

- [x] CHK061 Conversion de TODOS los proveedores a tools — native-first (WRAP-SDK/CLONE-UPSTREAM, MCP-EXTERNO solo fallback) + abstraccion universal `ToolWrapper` (todo proveedor = Tool, soporta proveedores sin MCP) + audit de estrategia → 021 FR-053/054/055 + §Inventario Tabla 1; F1 pasos 1-5. (decision 021-D5)
- [x] CHK062 MCPProcessSupervisor (~150 LOC, backoff, healthcheck; **0..N procesos fallback** bajo native-first) → 021 FR-004/005/006/007.
- [x] CHK063 Cliente MCP (STDIO/HTTP/SSE) de Hermes `mcp_tool.py` → 021 FR-003.
- [x] CHK064 Extraccion Hermes governance (file_safety/redact/path_security/url_safety/website_policy) → 021 FR-025.
- [x] CHK065 Tooling base (lazy_deps/schema_sanitizer/output_limits) + approvals → 021 FR-025.
- [x] CHK066 4 tools Tier 1 documents (file_system + template_render/docx/pdf) → 021 §Inventario Tabla 2/3 + FR-028.
- [x] CHK067 Computer use Windows 11 (pyautogui/pygetwindow/mss) + gate aprobacion → 021 FR-029/030 (Tabla 3).
- [x] CHK068 OpenClaw solo referencia (no copia codigo) → 021 FR-027.
- [x] CHK069 Regla import <5000 LOC + destinos `src/` + atribucion ≤400 LOC → spec 018 + 021 FR-026.
- [x] CHK070 Nombramiento de todas las tools (crean/clonan/refactorizan) → 021 §Inventario (Tabla 1/2/3 + Resumen 21 tools).
- [ ] CHK071 Tier 3 traducidos + sub-tools `*_local.py` + dominios design/eng/media/analytics → **(roadmap F3b)**.

## 07 — Migracion 2.0→3.0

- [~] CHK072 F0 (auditoria licencias + supuestos A1-A14 + estructura) → **spec 019 + docs/f0-*** (no 021).
- [x] CHK073 F1 Foundation (supervisor, governance, tooling base, remover auth) → 021 Phase F1.
- [x] CHK074 F2 TurboVec + ingestion + memoria → 021 Phase F2.
- [x] CHK075 F3a tools nuevas + computer use → 021 Phase F3a.
- [x] CHK076 F4a orquestacion + 3 modos + 3 playbooks → 021 Phase F4a.
- [x] CHK077 F5a Dreaming basico + PI defense + audit → 021 Phase F5a.
- [x] CHK078 Cero breaking changes al 2.0 (API `/api/v2/research/*` intacta) → 021 Delivery Constraints (#5) + SC-005.
- [x] CHK079 Onboarding wizard (COMPANY/*.md, OAuth, primera ingestion, geo) → 021 FR-047/048 + SC-013 (GAP-2 incorporado).
- [x] CHK080 Plan de rollback por fase → 021 §Rollout Strategy.

## 08 — Gobernanza, seguridad y operaciones

- [x] CHK081 Tool-gating (sin key/CB down → no listada), CQS READ-ONLY → 021 FR-042.
- [x] CHK082 Politica no-delete (excluir `delete_*`, whitelist `forget_user`) → 021 FR-043.
- [x] CHK083 PI defense regex + Lakera; cuarentena pre-LLM → 021 FR-044 (embedding layer = roadmap).
- [x] CHK084 Audit trail JSONL (`~/.vigilador/audit/`) → 021 FR-045.
- [x] CHK085 **Eliminar auth de usuario** (SSO/login/token/device) → 021 FR-036 (D4) + §Deprecated A.
- [x] CHK086 Conservar OAuth de servicio (`oauth_manager`, scopes sin delete) → 021 FR-037/016.
- [x] CHK087 Capability tokens + anomaly detector → **(roadmap F5b)**.

## ANEXO-A / ANEXO-B / GLOSARIO

- [x] CHK088 Orden de dependencias F0→F5a → 021 Phases (orden correcto).
- [x] CHK089 Flujo runtime Channel→ModeResolver→Complexity→PlaybookRunner→BranchCoordinator/ToolRegistry → 021 FR-017..024 + Key Entities.
- [x] CHK090 Decisiones ANEXO-B relevantes (#11 extraccion, #64 supervisor, #30 auth, #41 embeddings, #29 quotas, #12 computer use) → 021 §Deprecated D + traza FR.
- [x] CHK091 Terminologia GLOSARIO (Mode/Playbook/Skill/Capability/Tool/ToolWrapper/Channel/Dreaming/TurboVecIndex) → 021 usa los terminos consistentemente.

---

## Gaps detectados — INCORPORADOS a 021 (peticion del usuario: "anade el gap al 021")

| ID | Gap | Origen plan | Estado | FR/SC en 021 |
|---|---|---|---|---|
| **GAP-1** | **Frontend MVP** (4 superficies, sin login per D4: onboarding, chat+modo+workstreams, tools/MCPs status, datos) | 00 #1, 00b C1.6, 07 F4a | ✅ Incorporado (Phase F4a paso 8) | FR-046, FR-050, SC-013/014 |
| **GAP-2** | **Onboarding wizard** + endpoints `api/v2/enterprise/onboarding/*` sin auth | 07 §Onboarding, 00b exit #2 | ✅ Incorporado (Phase F4a paso 9) | FR-047, FR-048, SC-013 |
| **GAP-3** | **Seleccion de provider embeddings/reranker** | 00 #2, 02, 07 F2 | ✅ Incorporado (settings `embedding_provider`/`reranker_provider`) | FR-049 |
| **GAP-4** | **SubagentRegistry** (spawn/track basico) | 03 §SubagentRegistry, ANEXO-A | ✅ Incorporado (Phase F4a paso 7) | FR-051, SC-015 |
| **GAP-5** | **CommandSkill model** (comando parametrizable) | 04 §CommandSkill | ✅ Incorporado (Phase F2 paso 6) | FR-052, SC-015 |

> Las superficies de frontend **post-MVP** (artefactos, optimizacion, admin/Dreaming viewer, audit/rollback UI) siguen siendo roadmap F5c — NO son parte del MVP ni de 021.

### Diferidos legitimamente a roadmap (NO son gaps — 00b lo decide)

Automantenimiento admin (#12), optimizacion ISO/NTC (#15), artefactos (#16), dominios design/eng/media/analytics (C1.5), playbooks avanzados (decision-debate/market-research/goal-pursuit/app-development/artifact-development/company-optimization), modos CFO/Legal/Marketing/B2B/Ops, 5-7 loops de autoaprendizaje + `agent_modifications` SQL + anomaly detector, capability tokens, PI defense por embeddings, Tier 3 + sub-tools `*_local.py`, SSO/DR. Todos documentados y deprecados en el plan 021 (§Deprecated C/D).

---

## Notes

- **Cobertura MVP completa**: tras incorporar los 5 gaps (peticion del usuario), 021 cubre el MVP F1-F5a **end-to-end** — backbone backend + frontend MVP (4 superficies) + onboarding + seleccion de providers + SubagentRegistry + CommandSkill.
- **Sin login**: el frontend MVP no tiene pantalla de auth (auth de usuario eliminada por D4); 4 superficies = onboarding, chat+modo+workstreams, estado tools/MCPs, datos empresariales.
- **F0** (auditoria/licencias) pertenece a spec 019 + `docs/f0-*`, no a 021.
- **Roadmap (no son gaps)**: optimizacion/artefactos/automantenimiento, dominios design/eng/media/analytics, playbooks/modos avanzados, loops de autoaprendizaje, capability tokens, PI por embeddings, Tier3/`*_local.py`, SSO/DR y frontend post-MVP (F5c).

## Validation summary

- Documentos del set verificados: 14/14 activos (excluidos `_archive/` y `v3-enterprise-toolkit-extraction.md` deprecado).
- Items de cobertura: 91 (CHK001-CHK091).
- Marcas tras incorporar los gaps: `[x]` cubierto = **85** · `[~]` otra-spec = **1** (CHK072 F0 = spec 019) · `[ ]` no-en-021 = **5** (CHK012, CHK015, CHK016, CHK036, CHK071 — **TODOS roadmap legitimo** diferido por 00b).
- **Gaps MVP reales restantes: 0** — GAP-1..5 incorporados a 021 (FR-046..052, SC-013..015).
- **Veredicto**: 021 cubre el **MVP end-to-end (F1-F5a) completo**. Lo unico `[ ]` es roadmap diferido por 00b; F0 corresponde a spec 019. Listo para `/speckit.tasks`.
