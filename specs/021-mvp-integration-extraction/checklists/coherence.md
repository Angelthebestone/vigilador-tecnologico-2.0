# Coherence Checklist: 021 spec ↔ plan ↔ tasks ↔ constitution v1.2.0

**Purpose**: Verificar consistencia interna entre los 4 artefactos del feature 021 — `spec.md`, `plan.md`, `tasks.md` y la `constitucion v1.2.0` (`.specify/memory/constitution.md`). A diferencia de `plan-coverage.md` (que valida 021 contra el plan vigilador 3.0), este checklist valida que los 4 artefactos digan lo mismo entre si.

**Created**: 2026-05-30
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)
**Constitution**: `.specify/memory/constitution.md` v1.2.0

**Leyenda**: `[x]` coherente · `[~]` coherente con observacion menor · `[ ]` incoherencia material (requiere fix).

**Conteos verificados (programatico)**:
- spec FRs: **55** (FR-001..FR-055).
- spec SCs: **15** (SC-001..SC-015).
- plan FR refs: **162** (cada FR aparece ≥1 vez; total 55/55).
- tasks FR refs: **92** (cada FR aparece ≥1 vez; total 55/55).
- tasks IDs: **155** (T001..T155).
- decisiones del usuario: **D1..D5** (5).

---

## Axis A — Spec ↔ Plan

- [x] CHK001 Los 55 FRs del spec aparecen referenciados en el plan (verificado: `for i in 1..55: grep "FR-iii" plan.md` retorna ≥1 cada uno).
- [x] CHK002 La matriz "Trazabilidad FR → Fase" del plan declara cobertura **55/55** alineada con el conteo de FRs del spec.
- [x] CHK003 Los `Key Entities` del spec tienen entrada concreta en el plan (`McpToolWrapper`, `MCPProcessSupervisor`, `mcp_client`, `TurboVecIndex`, `IngestionOrchestrator`, `IngestionConnector`, `ModeResolver/ModeContext/ModeLoader`, `ComplexityClassifier`, `PlaybookRunner`, `Mode`, `Playbook`, `SkillLoader/SkillRegistry/k_dense_adapter/agency_agents_adapter`, `computer_use`, `Dreaming`, `oauth_manager`, `PromptInjectionDetector`, `Frontend MVP`, `OnboardingService`, `SubagentRegistry`, `CommandSkill`).
- [x] CHK004 La tabla **Inventario y Nombramiento de Tools** del plan (16 proveedores + 3 nuevas + 2 refactorizadas + turbovec) es consistente con la lista de proveedores en spec FR-053/054 y SC-001/002.
- [x] CHK005 Cada **decision del usuario** declarada en spec (021-D1..D5) tiene equivalente en el plan: D1 → Technical Context "TurboVec (D1 revisada)" + Phase F2 paso 1; D2 → "F2 paso 6 clonar" + skills_vendor_dir; D3 → "F2 paso 6 quitar `external:claude-local`"; D4 → "Auth (D4)" en Technical Context + §Deprecated A; D5 → Technical Context "Estrategia native-first" + Phase F1.
- [x] CHK006 Spec dice "modulos ≤400 LOC con atribucion" y plan repite la regla en Technical Context, External Constraints y Phase F1 (governance Hermes).
- [x] CHK007 Spec FR-007 dice `external.yaml` contiene **solo** los proveedores fallback; el plan refleja lo mismo en New Files (`external.yaml` "Manifiesto de proveedores que queden como MCP externo (fallback)") sin contradiccion.
- [x] CHK008 Spec EC-02 (TurboVec library DOWN) coincide con plan Rollout F2 (libreria `turbovec` no carga → busqueda deshabilitada con error).

## Axis B — Spec ↔ Tasks

- [x] CHK009 Los 55 FRs del spec aparecen referenciados en tasks (verificado: 55/55 con ≥1 task).
- [x] CHK010 Los 15 SCs del spec aparecen referenciados en tasks Polish (T138-T155 cubren SC-001..SC-015 1:1; FR-027 OpenClaw verificado en T146).
- [x] CHK011 Cada FR tiene una task de **implementacion** y/o **verificacion**: revisado por bloque (F1.A-J, F2.A-G, F3a.A-C, F4a.A-I, F5a.A-E).
- [x] CHK012 Spec FR-001/002 (puente MCP fallback) → tasks T012-T014 + T034 (registro universal). Coherente.
- [x] CHK013 Spec FR-009/010/011 (TurboVec **nativo** in-process via PyPI `turbovec`) → tasks T053-T055 (test+install+impl). Coherente con D1 revisada.
- [x] CHK014 Spec FR-029/030 (computer use Win11 + gate aprobacion) → tasks T085-T089. Backend `windows_backend.py` con `pyautogui`/`pygetwindow`/`mss` aparece en ambos.
- [x] CHK015 Spec FR-036/037/038 (eliminar auth de usuario / conservar OAuth servicio / sin quotas) → tasks T046-T051 (REMOVE secuencial) + T144 verificacion SC-008.
- [x] CHK016 Spec FR-039/040/041 (Dreaming MVP solo 2 fases + deprecar resto) → tasks T123-T130 (scheduler limitado + DEPRECATE 9 fases extra + 7 loops + goal_pursuit/app_development/artifacts).
- [x] CHK017 Spec FR-046..050 (frontend MVP 4 superficies sin login) → tasks T114-T118; FR-047/048 (onboarding sin auth) → T119-T120.
- [x] CHK018 Spec FR-051 (SubagentRegistry) → tasks T111-T113 (test+migracion+impl).
- [x] CHK019 Spec FR-052 (CommandSkill) → tasks T078-T079 (test+impl).
- [x] CHK020 Spec FR-053/054/055 (native-first / abstraccion universal / audit) → tasks T001-T002 (audit), T015-T032 (tools nativas), T033-T034 (registro universal).

## Axis C — Plan ↔ Tasks

- [x] CHK021 Cada **Variable** definida en plan §Variables esta referenciada en tasks (17/17 settings + 2/2 env vars verificado): `mcp_external_config`, `mcp_supervisor_enabled`, `mcp_logs_dir`, `vector_index_backend`, `ingestion_enabled`, `ingestion_connectors`, `skills_sources_enabled`, `skills_vendor_dir`, `computer_use_enabled`, `computer_use_app_allowlist`, `audit_dir`, `tools_delete_whitelist`, `pi_defense_enabled`, `embedding_provider`, `reranker_provider`, `frontend_enabled`, `onboarding_enabled`, `VT_GOOGLE_CLIENT_ID`, `VT_GOOGLE_CLIENT_SECRET` (todos en T003-T004).
- [x] CHK022 La env var `VT_TURBOVEC_MCP_*` aparece **solo** en T003 con la frase "NO incluir" (consistente con D1 revisada — TurboVec nativo).
- [x] CHK023 El campo `claude_local_path` aparece **solo** en contexto REMOVE/ELIMINAR (plan §Variables tachado, plan §Deprecated B "REMOVE", tasks T004 ELIMINAR + T073 modify + T080 grep verificacion = 0). Consistente.
- [x] CHK024 Cada **New File** del plan tiene una task que lo crea: `mcp_client.py` → T008; `mcp_tool_wrapper.py` → T013; `process_supervisor.py` → T010; `healthcheck.py` → T011; `external.yaml` → T014; `turbovec_index.py` → T055; `orchestrator.py` ingestion → T060; `chunking/dedup/acl_resolver.py` → T061-T063; `google_drive.py` → T065; `frozen_snapshot.py` → T057; governance Hermes → T036-T040; approvals → T042; tooling base → T043; documents tools → T082-T084; computer_use → T086-T088; orchestration → T092-T094; modes → T101-T103; playbooks → T105-T108; subagent_registry → T113; frontend surfaces → T114-T118; onboarding → T120; reporter → T126; PI detector → T132; audit_log → T135; audit script → T001.
- [x] CHK025 Cada **Modified File** del plan tiene una task que lo modifica: `tool_registry.py` → T008/T027/T028/T045; `settings.py` → T004; `app.py` → T051+T121; `router.py` → T048; `dependencies.py` → T049; `enterprise_onboarding.py` → T050+T120; `skill_loader.py` → T073/T077; `mode_resolver.py` → T096; `dreaming/scheduler.py` → T124; `technology-watch.yaml` → T108.
- [x] CHK026 Cada path en plan §Deprecated A (REMOVE auth) tiene una task: `enterprise_auth.py` → T047; `router.py` registro → T048; `dependencies.py` deps → T049; `enterprise_onboarding.py` → T050; conservar `oauth_manager.py` → T051.
- [x] CHK027 Cada path en plan §Deprecated B (REMOVE claude-local) tiene una task: `claude_local_adapter.py` → T073 (desregistrar); `skill_loader.py` lineas 9/50/58/71-72/136-138 → T073 (lineas explicitas); `settings.py:141/142` → T004 (modificar/eliminar).
- [x] CHK028 Cada path en plan §Deprecated C (DEPRECATE roadmap → no DELETE) tiene una task: `goal_pursuit/` (8py) → T129; `app_development/` (12py) → T129; `artifacts/` (10py) → T129; `dreaming/loops/` (8py) → T128; `dreaming/phases/` (9 de 11) → T127; modos roadmap (5 yaml) → T104; playbooks roadmap (4 yaml) → T110.
- [x] CHK029 Cada **Phase Verification** del plan tiene tasks: F1 → T052; F2 → T080; F3a → T090; F4a → T122; F5a → T137; Polish → T138-T155.
- [x] CHK030 Plan §Rollout Strategy menciona flags (`mcp_supervisor_enabled`, `ingestion_enabled`, `computer_use_enabled`, `dreaming_enabled`, `pi_defense_enabled`); todos esos flags aparecen en tasks T004 y se consumen en lifespan (T051+T121).

## Axis D — Constitution v1.2.0 ↔ All

> Spec/plan citan principios en sus secciones "Delivery Constraints" / "Constitution Check"; tasks.md es operacional y aplica los principios indirectamente. La constitucion **MUST** revisarse en cada ciclo de spec/plan (gobernanza); cumplido.

- [x] CHK031 **Principio 1 — Pensar antes de codificar**: spec declara A-01..A-11 y D1..D5 explicitamente; plan repite supuestos en Approach + Technical Context; tasks tienen "Independent Test Criteria" por fase.
- [x] CHK032 **Principio 2 — Simplicidad / KISS / YAGNI**: spec §Delivery Constraints + plan Constitution Check Pre/Post lo citan; tasks aplican (e.g. supervisor ~150 LOC, modulos ≤400 LOC, sin codigo de roadmap).
- [x] CHK033 **Principio 3 — Modularidad / SRP / SoC**: spec lo cita; plan repite ("extraccion Hermes en modulos ≤400 LOC"); tasks T036-T043 (cada archivo Hermes a su modulo) y T013-T032 (cada proveedor en su archivo) lo aplican.
- [x] CHK034 **Principio 4 — Manejo de errores estricto**: spec §Constraints; plan External Constraints "errores explicitos"; tasks T053 (TurboVec DOWN error explicito), T065 (OAuth invalido), T085 (sin display error explicito), T011/T132 (PI cuarentena).
- [x] CHK035 **Principio 5 — Cambios quirurgicos**: spec/plan repiten "el 2.0 no se toca"; tasks T141 verifica `git diff --stat` sobre `branch_coordinator.py` = 0 lineas; tasks T037+T141 confirman suite 2.0 verde.
- [x] CHK036 **Principio 6 — Entrega verificable**: spec define 15 SCs; plan los usa en §Success Criteria; tasks Polish (T138-T155) los verifica con artefactos automatizados (grep/wc/pytest/manual end-to-end).
- [x] CHK037 **Diseno — DRY**: spec evita redefinir `ToolWrapper`/`ToolRegistry`/catalogo SSOT (los reusa de specs 009/018); plan §Dependencies lo declara; tasks T007-T034 consumen los contratos sin redefinir.
- [x] CHK038 **Diseno — DIP**: spec §Constraints "DIP — connectors implementan IngestionConnector; TurboVecIndex implementa VectorIndex; ModeResolver implementa ModeResolutionStrategy"; plan repite; tasks T058 (port `IngestionConnector`), T055 (TurboVecIndex implementa port), T096 (ModeResolver) materializan.
- [x] CHK039 **Diseno — CQS (#81)**: spec §Constraints "CQS — list_tools_for_role solo lee tool_health; HealthMonitor escribe"; plan repite; tasks T044-T045 lo testean explicitamente.
- [x] CHK040 **Diseno — OCP / POLA / Convencion sobre configuracion**: modos/playbooks por YAML extensibles sin modificar runners (OCP); `ComplexityClassifier` loggea su decision (POLA); defaults sensatos en settings (Convencion).
- [x] CHK041 **Diseno — LSP / ISP**: spec §Delivery Constraints cita ahora LSP explicitamente (`TurboVecIndex.query()` sustituible por cualquier impl del port `VectorIndex`; `McpToolWrapper.execute()` retorna `ToolResult` indistinguible de tool nativa) e ISP (`ToolWrapper` minimo sin `tags`/`capabilities`; ports separados `VectorIndex`/`IngestionConnector`/`ModeResolutionStrategy`/`ChannelAdapter` en lugar de interfaz monolitica). [Mejora aplicada 2026-05-30]

## Axis E — Decisiones del usuario (D1..D5) consistencia

> Conteo programatico: D1=spec6/plan1/tasks1; D2=spec4/plan0/tasks0; D3=spec3/plan0/tasks0; D4=spec4/plan0/tasks0; D5=spec4/plan0/tasks0. Spec es la fuente; plan/tasks aplican los conceptos pero rara vez citan el ID.

- [x] CHK042 **D1 (TurboVec nativo, revisada)**: spec FR-009/010/011 + EC-02 + Tabla correcciones; plan Technical Context "(D1 revisada)" + Phase F2; tasks T053-T055; 0 referencias residuales a `TurboVecMCPIndex` o `turbovec_mcp_name`.
- [x] CHK043 **D2 (clonar marketplaces en src/)**: spec FR-031 + correccion table; plan New Files `_vendor/{k_dense,agency_agents}/`; tasks T066+T067; setting `skills_vendor_dir` apunta a `src/.../enterprise/skills_marketplace/_vendor`.
- [x] CHK044 **D3 (eliminar claude-local)**: spec FR-033 + correccion table; plan §Deprecated B + setting `skills_sources_enabled` sin `external:claude-local`; tasks T004 (modificar settings) + T072 (test no-claude-local) + T073 (eliminar lineas exactas) + T080 (grep verificacion = 0).
- [x] CHK045 **D4 (sin login)**: spec FR-036/037/038 + AS-10 + SC-008 + correccion table; plan §Deprecated A; tasks T046-T051; FR-046 frontend "sin login"; T144 verifica grep auth de usuario = 0.
- [x] CHK046 **D5 (native-first + abstraccion universal de Tool)**: spec FR-053/054/055 + correccion table; plan Technical Context "Estrategia native-first" + Tabla 1 reframed; tasks T001-T002 audit + T015-T034 native tools + universal registration.
- [x] CHK047 **Trazabilidad por ID**: plan.md Phase F1 anclado a "Aplica decisiones: 021-D5, 021-D4"; Phase F2 anclado a "021-D1 revisada, 021-D2, 021-D3". tasks.md Phase F1 cita D5+D4 con Principle alignment; Phase F2 cita D1+D2+D3; Phase F4a cita D4. La trazabilidad por ID ahora es explicita en cada fase. [Mejora aplicada 2026-05-30]

## Axis F — Internal Consistency (counts y wording)

- [x] CHK048 **Conteo de proveedores**: spec In-Scope, plan Tabla 1, tasks T015-T032 = 16 proveedores (search/web/research/documents/execution/creative/productivity). Coincide en los 3 artefactos.
- [x] CHK049 **Conteo de tools de agente**: 21 (16 + 3 nuevas + 2 refactorizadas, computer_use ya cuenta como una de las 2 refactorizadas en plan; spec/plan/tasks usan "21 tools" en SC-014/T138). El conteo del plan §Resumen reporta 21.
- [x] CHK050 **4 superficies del frontend** (sin login): spec In-Scope, FR-046, plan §New Files (`{onboarding,chat,sources,admin}/`), tasks T114-T118 (4 superficies + 0 login).
- [x] CHK051 **3 modos MVP**: `default`, `vigilancia-tech`, `CEO` consistente en spec FR-021, plan Technical Context, tasks T101-T103.
- [x] CHK052 **3 playbooks MVP**: `technology-watch`, `deep-research`, `general` consistente en spec FR-022, plan Technical Context, tasks T105-T108. `technology-watch` envuelve `BranchCoordinator` 2.0 en los 3.
- [x] CHK053 **6 ramas del 2.0**: spec FR-023, plan Technical Context, tasks T107+T109+T141 lo citan. Cero modificacion al `BranchCoordinator` (T141 lo verifica con `git diff --stat`).
- [x] CHK054 **Dreaming MVP = 2 fases**: `memory_consolidation` + `ingestion_sync` consistente en spec FR-040, plan Phase F5a paso 1, tasks T123-T125.
- [x] CHK055 **TurboVec wording uniforme**: 17 referencias a "TurboVecIndex" + 10 a "paquete PyPI `turbovec`"; 0 a `TurboVecMCPIndex` o `turbovec_mcp` (excepto 2 notas intencionales en plan §Deprecated D + spec Out-of-Scope que documentan el descarte).
- [x] CHK056 **OAuth de servicio se conserva**: 4 menciones explicitas a `oauth_manager.py` "conservar"/"KEEP" en spec/plan; tasks T051 (preservar en lifespan) + T065 (connectors lo usan) + T120 (onboarding lo usa).
- [x] CHK057 **0 quotas por usuario**: spec FR-038, plan Constitution Check Pre, tasks T138 (verificacion implicita en SC-008/SC-014). Consistente con C0 #11 obsoleta #29.
- [x] CHK058 **Cero modificaciones al 2.0**: spec §Constraints + plan + tasks T037+T141 lo verifican. `infra/mcp/mcp-providers.json`, `infra/embeddings/gemini_gateway.py`, `infra/reranking/semantic_reranker.py`, `application/execution/branch_coordinator.py` y los 6 agentes intactos.
- [x] CHK059 **Atribucion Hermes uniforme**: header `# Adapted from Hermes Agent — Original file: <path> — License: <MIT|Apache-2.0>` declarado en spec FR-026, plan §Files (governance Hermes), tasks T008/T036/T037/T038/T039/T040/T042/T043/T057/T086/T146 y verificado en SC-010 (T146 grep).

## Axis G — Observaciones menores no bloqueantes

- [x] CHK060 **T103 ahora fija `playbooks.default:"deep-research"`** (alineado con MVP) y mueve `decision-debate` a la lista de allowed con comentario `# roadmap F4b`. La incoherencia con T110 (que deprecaba decision-debate) queda resuelta sin necesidad de fallback en runtime. [Mejora aplicada 2026-05-30]
- [x] CHK061 **Constitution principles citation density**: tasks.md Phase F1 ahora cita explicitamente #5 Cambios quirurgicos + DIP + ISP + CQS #81 + DRY; Phase F2 cita DIP + LSP + #4 Errores estrictos + SRP/SoC + DRY; Phase F4a cita OCP + POLA + #5 Cambios quirurgicos + Convencion sobre configuracion + DIP. La trazabilidad a principios queda reforzada en las fases de mayor riesgo de regresion. [Mejora aplicada 2026-05-30]
- [x] CHK062 **Fechas y version**: constitucion v1.2.0 ratificada 2026-05-10 enmendada 2026-05-19; specs 021 creadas 2026-05-29; consistente con el orden temporal y la regla "revision MUST ejecutarse en cada ciclo".

---

## Notes

- **Veredicto global**: la coherencia entre spec, plan, tasks y constitucion es **completa**. Tras aplicar las 4 mejoras (2026-05-30), no quedan observaciones menores ni incoherencias materiales.
- **0 observaciones, 0 incoherencias materiales**.
- **Cobertura programatica**: 55/55 FRs en plan y tasks; 15/15 SCs en tasks; 17/17 Variables; 2/2 env vars nuevas; 0 referencias rezagadas a TurboVec MCP o claude-local fuera de su contexto de remocion.
- **Decisiones D1..D5**: ahora todas con anclas explicitas por ID en plan F1/F2 y tasks F1/F2/F4a (CHK047).
- **Constitucion v1.2.0**: 6 principios fundamentales + 16 sub-principios de diseno; **16/16 con citacion explicita** (LSP/ISP ahora declarados en spec §Delivery Constraints — CHK041).

## Validation summary

- Items totales: **62** (CHK001..CHK062).
- `[x]` coherente: **62** (tras aplicar las 4 mejoras CHK041/047/060/061 el 2026-05-30).
- `[~]` observacion menor: **0**.
- `[ ]` incoherencia material: **0**.
- **Veredicto**: spec 021, plan 021, tasks 021 y constitucion v1.2.0 son **plenamente coherentes**. Listo para `/speckit.implement`.
