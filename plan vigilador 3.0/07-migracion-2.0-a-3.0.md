# 07 — Migración Vigilador 2.0 → 3.0

> Documento que cierra la **brecha 1** del set: inventario consolidado de qué se preserva, qué se extiende y qué es nuevo. Antes esta información estaba dispersa entre las decisiones #3, #5, #11, #46, #52, #91-95, etc.

> **Corrección vigente**: el 3.0 no puede perder workstreams, modulos de `application/`, `domain/ports` ni `infra` del 2.0. Tambien se corrige vectorizacion a TurboVecIndex unico, providers seleccionables de embedding/reranker y frontend como consola completa. Ver [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md).

---

## Principio rector

**Cero breaking changes al 2.0**. Todo lo nuevo del 3.0 vive en un subpaquete paralelo `src/vigilancia_multiagente/enterprise/`. La API pública del 2.0 (`/api/v2/research/*`) sigue funcionando idéntica. Los 6 agentes de rama (AVANCES, COMERCIAL, RIESGO, PI_NORMATIVA, COMPETITIVO, OPORTUNIDADES) operan sin tocarse — el playbook `technology-watch` del 3.0 simplemente los invoca vía `BranchCoordinator`.

Razón: el 2.0 está en producción con tests pasando (specs 002-008). La constitución (#5 Cambios quirúrgicos) exige preservar lo verificado. La evolución a 3.0 se construye al lado, no encima.

---

## Matriz archivo-a-archivo

### A. Preservar intacto

Estos componentes NO se tocan. El 3.0 los reutiliza vía sus interfaces actuales (DIP). Cero refactor lateral.

| Componente | Ubicación | Razón |
|---|---|---|
| `OrchestratorService` | `application/orchestration/orchestrator_service.py` | Lifecycle de sesiones del 2.0. El 3.0 lo invoca para playbook `technology-watch`. |
| `BranchCoordinator` | `application/execution/branch_coordinator.py` | Ejecución paralela de 6 ramas. Núcleo del 2.0. |
| `BaseBranchAgent` | `application/agents/base.py` | Clase base de los 6 agentes. Cualquier extensión hereda sin tocar el base. |
| 6 agentes de rama | `application/agents/{avances,comercial,riesgo,pi_normativa,competitivo,oportunidades}_agent.py` | Lógica de dominio del 2.0. Skills y prompts del 3.0 no los redefinen. |
| `PromptComposer` | `application/governance/prompt_composer.py` | SystemBase + BranchOverlay composition. El 3.0 añade `DomainProfile` sin modificar este. |
| `ContractLoader` (`AgentSkillPolicy`) | `application/governance/contract_loader.py` | Per-branch tool order/timeouts/retry. El 3.0 añade nuevas policies en `enterprise/`. |
| `MCPExecutionClient` + cache | `infra/mcp/execution_client.py`, `infra/mcp/mcp_cache.py` | Ejecución de los 15 MCPs actuales. El 3.0 usa un cliente independiente `enterprise/tooling/mcp_client.py` (COPY-HERMES) — coexisten (decisión #52). |
| 15 MCP providers actuales | `infra/mcp/mcp-providers.json` + carpetas | tavily, exa, jina, brave, firecrawl, serper, google_scholar, arxiv, fetch, sandbox, markitdown, minimax-image, openalex, playwright (+1 más). Siguen registrados sin cambios. |
| Sistema de governance overlays | `application/governance/contract_loader.py:_BRANCH_OVERLAYS` | Hardcoded dict del 2.0. El 3.0 carga overlays adicionales desde `config/modes/` sin tocar este. |
| `application/memory/cross_session_service.py` | preload + merge de sesiones | El 3.0 extiende su persistencia (port `GlobalKnowledgeStore` lo implementa en `enterprise/`). |
| `application/evaluation/*` | analytics, audit, authenticity, calibration, 9 sub-módulos | Framework de eval del 2.0 sigue intacto. El 3.0 lo consume como input para Loop 3 (Prompt self-improvement, ver `05-autoaprendizaje-y-autonomia.md`). |
| Workstreams inteligentes WS-A..WS-E | `application/evaluation/ws_a/` a `application/evaluation/ws_e/` | No se reemplazan por nuevos playbooks. El frontend 3.0 los debe mostrar/activar como capacidades existentes. |
| Pipeline de agentes | `application/agents/pipeline/` | Pasos de WSA-WS-E, deep analysis, data intelligence y output assurance se preservan y se invocan desde playbooks. |
| `application/artifacts/*` | manifest y registro de artefactos del 2.0 | Base para `enterprise/artifacts/`; no se borra ni duplica sin adapter. |
| `application/observability/*` | metrics service | Base para dashboard/admin 3.0. |
| `application/forecasting/trend_forecaster.py` | proyección de tendencias | Sigue. |
| `application/graph/knowledge_graph_service.py` | NetworkX analytics | Sigue. El 3.0 añade `enterprise/graph/` como dual (investigación + empresarial, decisión #46) sin tocar este. |
| `application/routing/source_scorer.py` | source trust scoring | Sigue. |
| API routes existentes | `api/routes/*.py` | `/api/v2/research/*` sin cambios. Nuevos endpoints van a `api/v2/enterprise/*` o `api/channels/*`. |
| Frontend React actual | `frontend/src/` | Cero cambios mandatorios. El 3.0 añade vistas nuevas en `frontend/src/enterprise/`. |
| Frontend modules existentes | `frontend/src/chat`, `analysis`, `agents`, `graph`, `history`, `state`, `api` | Se preservan y se integran en la consola 3.0. No se reescribe la UI desde cero. |
| Ports de dominio | `domain/ports/*` | Contratos base para adapters 3.0: embedding, reranker, vector index, tool executor, MCP/provider registry, etc. |
| Infra existente | `infra/mcp`, `infra/embeddings`, `infra/reranking`, `infra/persistence`, `infra/llm` | Se envuelve/extiende. No se reemplaza por componentes paralelos incompatibles. |
| Tests existentes | `tests/test_orchestrator.py` y demás | Deben seguir pasando al 100% en cada fase F0-F5 (criterio verificable). |

**Verificación obligatoria F0**: ejecutar `pytest` sobre el set actual del 2.0; cada modificación posterior debe re-correr la batería completa antes de merge.

### B. Extender (OCP — sin tocar lo existente)

Estos componentes se amplían siguiendo Open/Closed: nueva subclase o nuevo parámetro opcional con default seguro.

| Componente | Tipo de extensión | Detalle |
|---|---|---|
| `BranchOverlay` (`domain/system_base.py`) | Subclase nueva `DomainProfile` | `DomainProfile(BranchOverlay)` añade `connectors_required`, `acl_default_scopes`, `playbook_id`. Cero cambios a `BranchOverlay`. (Decisión #46) |
| Port `VectorIndex` | Nuevo adapter `TurboVecIndex` | Implementa el port existente como indice vectorial unico del 3.0. Sin doble write ni pgvector backup obligatorio. |
| `MiniMaxClient` (`infra/llm/minimax_client.py`) | Adapter por modelo/proveedor | Si no se pasa modelo → default actual. Otros modelos se agregan por adapter, no por condicionales dispersos. |
| Port `EmbeddingGateway` (Gemini en el 2.0) | Adapters seleccionables | `GeminiEmbeddingGateway` API existente se preserva; `LocalEmbeddingsAdapter` es opcional si el usuario lo elige. |
| Port `Reranker` | Adapters seleccionables | `SemanticReranker` API existente (Cohere + fallback embeddings) se preserva; reranker local es opcional. |
| `AgentSkillPolicy` (`contract_loader.py`) | Carga adicional desde `config/modes/<id>.yaml` | El loader actual sigue leyendo `skill_matrix_default.yaml`; el 3.0 añade un segundo loader sin tocar el primero. |
| `MCPProviderRegistry` | Carga adicional desde `config/mcp/external.yaml` | Para los 15 MCPs externos Tier 2 del 3.0. Coexisten con los 15 del 2.0 sin conflicto (namespaces distintos: `mcp_2.<provider>` vs `mcp_ext.<provider>`). |
| `prompt_composer.PromptComposer` | Añade soporte para SOUL + COMPANY frozen snapshot | Solo si la sesión tiene un Mode activo (3.0); si no → comportamiento 2.0 sin cambios. |
| `LanguageRouter` (nuevo, conceptualmente extensión de `PromptComposer`) | Detecta locale por turno (#40) | Interno inglés / externo español por default. Si `language` no se pasa → inglés (comportamiento 2.0). |

### C. Crear nuevo en `enterprise/`

Todo bajo el subpaquete `src/vigilancia_multiagente/enterprise/`. Cero acoplamiento mandatorio con `application/` (solo lectura vía ports).

Estructura completa (heredada del plan maestro §2.1, refinada con decisiones de esta sesión):

```
src/vigilancia_multiagente/enterprise/
├── orchestration/
│   ├── complexity_classifier.py
│   ├── playbook_runner.py
│   ├── crewai_bridge.py
│   ├── debate_coordinator.py
│   ├── subagent_registry.py
│   └── goal_pursuit/
│       ├── decomposer.py
│       ├── dependency_resolver.py
│       ├── checkpoint_reporter.py
│       └── approval_gate.py
├── modes/                                  [NUEVO esta sesión — doc 02]
│   ├── mode_loader.py
│   ├── mode_registry.py
│   └── mode_resolver.py                    autodetección heurística+LLM
├── skills_marketplace/                     [NUEVO esta sesión — doc 04]
│   ├── k_dense_adapter.py                  carga scientific-agent-skills
│   ├── agency_agents_adapter.py            carga msitarzewski/agency-agents
│   ├── skill_loader.py
│   └── skill_curator.py                    promoción/deprecation lifecycle
├── intelligence/
│   ├── self_correction.py
│   ├── cove_verifier.py
│   ├── confidence_scorer.py
│   └── fewshot_retriever.py
├── triggers/
│   ├── event_listener.py
│   └── webhook_handler.py
├── auth/
│   ├── oauth_manager.py
│   ├── token_auth.py
│   ├── device_token.py
│   └── capability_tokens.py
├── governance/
│   ├── file_safety.py
│   ├── redact.py
│   ├── path_security.py
│   ├── url_safety.py
│   ├── website_policy.py
│   ├── pii_redactor.py
│   ├── language_router.py
│   ├── forget_user.py
│   ├── prompt_injection_detector.py
│   ├── anomaly_detector.py
│   ├── agent_modifier.py                   [NUEVO esta sesión — doc 05]
│   └── approval_queue.py
├── memory/
│   ├── frozen_snapshot.py
│   ├── context_compressor.py
│   └── fts_search.py
├── observability/
│   ├── metrics.py
│   ├── dashboard.py
│   └── health_monitor.py
├── ingestion/
│   ├── orchestrator.py
│   ├── connectors/{google_drive,onedrive,sharepoint,outlook,gmail,local_fs,network_drive,whatsapp,chatbot}.py
│   ├── chunking.py
│   ├── dedup.py
│   └── acl_resolver.py
├── optimization/
│   ├── standard_mapper.py
│   ├── gap_analyzer.py
│   ├── evidence_matrix.py
│   └── improvement_planner.py
├── artifacts/
│   ├── artifact_registry.py
│   ├── dashboard_builder.py
│   ├── pipeline_builder.py
│   └── metric_contracts.py
├── tooling/
│   ├── builtin/
│   │   ├── search/
│   │   ├── web/
│   │   ├── documents/
│   │   ├── productivity/
│   │   ├── meetings/
│   │   ├── crm/
│   │   ├── communication/
│   │   ├── finance/
│   │   ├── desktop/
│   │   ├── code/
│   │   ├── research/
│   │   ├── people/
│   │   ├── personalization/
│   │   ├── design/
│   │   ├── engineering/
│   │   ├── media/
│   │   └── analytics/
│   ├── tool_registry.py
│   ├── tool_schema_loader.py
│   ├── parallel_dispatcher.py
│   ├── local_app_detector.py
│   ├── adaptive_cache.py
│   └── output_formatter.py
├── dreaming/
│   ├── scheduler.py
│   ├── phases.py
│   ├── tasks/
│   │   ├── memory_consolidation.py
│   │   ├── skill_curator.py
│   │   ├── self_improvement_runner.py     [NUEVO esta sesión — Loop 3 doc 05]
│   │   ├── tool_composition_detector.py    [NUEVO esta sesión — Loop 4 doc 05]
│   │   ├── company_self_update.py          [NUEVO esta sesión — Loop 5 doc 05]
│   │   ├── config_refresher.py
│   │   ├── index_maintenance.py
│   │   ├── learned_skill_revalidation.py
│   │   ├── scheduled_reports.py
│   │   └── ingestion_sync.py
│   └── reporter.py
└── mcp/
    ├── process_supervisor.py
    ├── healthcheck.py
    └── admin_cli.py
```

Y fuera de `src/`:

```
plugins/
└── technology-watch/                       empaqueta el 2.0 como playbook
config/
├── modes/                                  [NUEVO esta sesión]
├── playbooks/
│   ├── technology-watch.yaml
│   ├── decision-debate.yaml
│   ├── market-research.yaml
│   ├── compliance-audit.yaml
│   ├── general.yaml
│   ├── deep-research.yaml
│   ├── goal-pursuit.yaml
│   └── app-development.yaml                [NUEVO esta sesión — flujo Spec-Kit]
├── soul.md
├── company/{identity,organization,processes,systems,policies}.md
├── templates/{informes,propuestas,contratos,presentaciones,correos}/
├── skills/
│   ├── curated/                            skills oficiales del repo
│   └── learned/                            skills aprendidos por el agente
└── mcp/external.yaml
```

---

## Plan de fases F0-F5

> **Cambio C1 esta sesión**: las fases F3-F5 se splittean en sub-fases **MVP (F3a/F4a/F5a)** y **roadmap completo (F3b/F4b/F5b/c/d)**. El MVP entrega en 12-16 semanas; el roadmap completo agrega ~16 semanas más. Detalle en [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md).

Cronograma:
- **MVP**: 12-16 semanas (F0 + F1 + F2 + F3a + F4a + F5a) con 1-2 ingenieros.
- **Roadmap completo**: +16 semanas adicionales tras MVP (F3b + F4b/c + F5b/c/d) con 2-3 ingenieros.

Cada fase tiene criterios verificables (constitución principio 6).

### Tabla MVP vs roadmap completo

| Fase | MVP (F#a) | Roadmap post-MVP (F#b/c/d) |
|---|---|---|
| F0 | Auditoría + setup (sin cambios) | — |
| F1 | Foundation: XiaomimimoClient + ToolRegistry + persistencia base (sin `agent_modifications` aún) | — |
| F2 | TurboVecIndex + ingestion básico Google Workspace MCP solo Drive | — |
| F3 | **F3a**: 4 tools Tier 1 nuevas + `google-workspace-mcp` Tier 2 vía MCPProcessSupervisor | **F3b**: resto de tools del catálogo (~59 capacidades) |
| F4 | **F4a**: 3 modos MVP (default, Vigilancia Tech, CEO) + 3 playbooks MVP (technology-watch, deep-research, general) + Frontend 5 superficies | **F4b**: playbooks goal-pursuit, app-development, artifact-development, company-optimization, compliance-audit, market-research<br>**F4c**: modos CFO, Consultor Legal, Marketing, Vendedor B2B, Operaciones PYME |
| F5 | **F5a**: Dreaming básico (memory consolidation + ingestion sync) + PI defense regex + tool-gating | **F5b**: 5 loops de autoaprendizaje + agent_modifications SQL<br>**F5c**: frontend completo (artefactos + optimización + admin)<br>**F5d**: DR + SSO + compliance avanzado + anomaly detector |



### F0 — Auditoría + setup (3-4 semanas)

**Objetivo**: validar supuestos A1-A14 + auditoría licencias + estructura base. Cero código de producto.

**Tareas**:
1. Verificar metadata DB existente y compatibilidad con migraciones necesarias del 3.0.
2. Verificar A3/A12 (TurboVec funciona en Windows 11).
3. Verificar A1/A2 (MiniMax M-2.5 disponible + CrewAI 0.x compatible).
4. Verificar A5/A6 (Hermes tools portables + providers de embeddings/reranker seleccionables: Gemini/Cohere existentes y locales opcionales).
5. Verificar A7/A8 (Presidio español + OAuth scopes sin delete).
6. Auditoría licencias ~30 archivos COPY-HERMES + 32 paquetes PyPI WRAP-SDK + 15 MCPs externos Tier 2.
7. Crear estructura de carpetas `enterprise/` vacía (sin código).
8. Crear `config/{modes,playbooks,company,templates,skills,mcp}/` con archivos placeholder.
9. Definir contrato `ToolWrapper` unificado (decisión #61) en `enterprise/tooling/tool_wrapper.py`.
10. Verificar MigrationRunner + SQL crudo existente (`infra/db/migrations/NNN_*.sql`).
11. Setup Prometheus + OpenTelemetry stubs.

**Criterios verificables F0**:
- [ ] Todos los supuestos A1-A14 marcados como validados/desmentidos con prueba.
- [ ] `tests/` del 2.0 siguen pasando 100%.
- [ ] Estructura `enterprise/` existe y compila (imports vacíos).
- [ ] CI corre `ruff` + `basedpyright` + `pytest` sin nuevas regresiones.
- [ ] Documento `docs/audit-licenses.md` listo con tabla de cada archivo + license + atribución.

**Rollback**: trivial. Si F0 falla → cero código nuevo, solo se descarta la estructura vacía.

### F1 — Foundation (5-6 semanas)

**Objetivo**: capa base operativa. `ToolRegistry`, persistencia, governance común.

**Tareas**:
1. Sprint A (5 archivos base de Hermes: registry, lazy_deps, schema_sanitizer, output_limits, debug_helpers).
2. Implementar `enterprise/domain/domain_profile.py` (extiende `BranchOverlay`).
3. Implementar `enterprise/tooling/tool_registry.py` con tool discovery progresivo.
4. Implementar `enterprise/governance/{file_safety,redact,path_security,url_safety,website_policy}.py` (COPY-HERMES).
5. Migrations SQL crudo (MigrationRunner) para: `oauth_credentials`, `subagents`, `prompt_versions`, `tool_health`, `pending_approvals`, `agent_modifications` (NUEVO esta sesión, doc 05).
6. Implementar `enterprise/observability/{metrics,health_monitor}.py` con fix CQS (#81).
7. Implementar `enterprise/auth/{oauth_manager,token_auth,device_token,capability_tokens}.py`.
8. Implementar `enterprise/governance/{language_router,pii_redactor,forget_user}.py` y telemetria de costo sin quotas por usuario.

**Criterios verificables F1**:
- [ ] Tests unitarios de cada componente pasan.
- [ ] Migration aplicable a base limpia + tablas creadas con `tenant_id` + uuidv7 en `agent_modifications`.
- [ ] `ToolRegistry` lista 0 tools al inicio (correcto — nada registrado aún).
- [ ] `health_monitor` corre cada 30s sin errores y actualiza `tool_health`.
- [ ] Métricas Prometheus expuestas en `/metrics`.

**Rollback**: el subpaquete `enterprise/` se ignora si se elimina; el 2.0 sigue corriendo.

### F2 — Ingestion + TurboVecIndex unico (5-6 semanas)

**Objetivo**: indexacion empresarial + TurboVecIndex como indice vectorial unico.

**Tareas**:
1. Implementar `enterprise/ingestion/{orchestrator,chunking,dedup,acl_resolver}.py`.
2. Implementar connectors nativos: `google_drive`, `onedrive/sharepoint`, `local_fs`, `network_drive`, `outlook/gmail`, `whatsapp`, `chatbot`.
3. Permitir via alternativa MCP cuando el usuario ya tenga MCP de nube/fuente configurado.
4. Implementar `enterprise/memory/{frozen_snapshot,context_compressor,fts_search}.py` (`fts_search` opcional).
5. Implementar seleccion de providers `EmbeddingGateway` y `Reranker` en onboarding/config.
6. Implementar `infra/persistence/turbovec_index.py` (nuevo adapter del port `VectorIndex`).
7. Integrar LlamaIndex solo si reduce loaders/chunking/retrieval sin ocultar los ports.

**Criterios verificables F2**:
- [ ] Connector Google Drive o local_fs ingiere 100 documentos sample y los indexa.
- [ ] Query semántica devuelve resultados con citations.
- [ ] Onboarding permite elegir embedding provider y reranker provider.
- [ ] TurboVecIndex implementa el port y puede reconstruirse desde fuentes/metadata.

**Rollback**: si TurboVecIndex falla → deshabilitar busqueda semantica nueva y reconstruir desde fuentes indexadas; el 2.0 sigue funcionando.

### F3a — Catálogo MVP de tools (3-4 semanas)

**Objetivo**: 20 capacidades operativas (4 Tier 1 nuevas + 16 Tier 2: 15 preservados del 2.0 + Google Workspace MCP).

**Tareas**:
1. `XiaomimimoClient` ya implementado en F1 — solo wiring final.
2. COPY-HERMES de `tools/file_tools.py` + `file_operations.py` + `file_state.py` + `file_safety.py` + `redact.py` modularizado (C0 #10: ≤300-400 LOC por módulo).
3. Implementar `template_render` (Jinja2 sobre MD/HTML/DOCX).
4. Implementar `docx_generate` (python-docx).
5. Implementar `pdf_generate` (WeasyPrint).
6. Declarar `google-workspace-mcp` en `config/mcp/external.yaml`.
7. `MCPProcessSupervisor` levanta 16 procesos al boot (15 del 2.0 + Google Workspace).
8. Tests E2E para los 4 tools nuevos + 1 test E2E del Google Workspace MCP.

**Criterios verificables F3a**:
- [ ] Las 4 tools Tier 1 nuevas tienen test E2E (~50 LOC).
- [ ] `MCPProcessSupervisor` arranca 16 procesos al boot con health OK.
- [ ] `vigilador-admin tools list` muestra 20 capacidades activas.
- [ ] Tool-gating funciona: sin Google Workspace credentials, el MCP no aparece en listing.

**Rollback F3a**: tool por tool con `enabled: false` en config. Sin afectar 2.0 ni runtime base.

### F3b — Catálogo completo (roadmap post-MVP, 6-8 semanas)

**Objetivo**: 79 capacidades operativas (resto de Tier 1 + Tier 2 + Tier 3 + sub-tools `*_local.py`).

**Tareas**: sprints B-K del plan maestro §5 (orden por dependencias). Detalle completo en `06-catalogo-tools-y-extraccion.md`.

**Criterios verificables F3b**:
- [ ] Cada tool nueva tiene test E2E (~50 LOC) que valida import + healthcheck + 1 llamada con mock-creds + schema JSON.
- [ ] `MCPProcessSupervisor` arranca ~23 procesos al boot con health OK.
- [ ] `LocalAppDetector` detecta apps instaladas y gating-out automático funciona.
- [ ] Catálogo final visible en `vigilador-admin tools list` con conteo 79.

**Rollback F3b**: tool por tool. Si una falla, se quita del registry con `enabled: false`.

### F4a — Orquestación MVP + Modos básicos + Frontend mínimo (2-3 semanas)

**Objetivo**: 3 modos MVP, 3 playbooks MVP, Frontend MVP 5 superficies. Sin loops avanzados ni audit trail SQL.

**Tareas MVP**:
1. Implementar `enterprise/orchestration/{complexity_classifier,playbook_runner,subagent_registry}.py`.
2. Implementar `enterprise/modes/{mode_loader,mode_registry,mode_resolver}.py`.
3. Crear 3 modos en `config/modes/`: `default.yaml`, `vigilancia-tech.yaml`, `CEO.yaml`. (CFO, Legal, Marketing, B2B, Operaciones PYME quedan para F4c.)
4. Crear 3 playbooks en `config/playbooks/`: `technology-watch.yaml` (envoltura del 2.0), `deep-research.yaml`, `general.yaml`.
5. Frontend MVP 5 superficies: login + onboarding + chat con modo + visor workstreams 2.0 + listado tools/MCPs con estado.
6. Plugin `technology-watch/` empaquetado.

**Criterios verificables F4a**:
- [ ] `/mode vigilancia-tech` ejecuta los 6 agentes de rama del 2.0 sin regresiones.
- [ ] `/mode CEO` ejecuta `deep-research` con outputs structured + free-form.
- [ ] Frontend onboarding completa empresa+ubicación+providers+Google Workspace en <15 min.
- [ ] Frontend lista los 20 tools/MCPs MVP con estado UP/DOWN.

**Rollback F4a**: deshabilitar Modes vía `features.modes: false`; runtime cae a comportamiento 2.0 puro.

### F4b — Playbooks avanzados (roadmap post-MVP, 3-4 semanas)

**Objetivo**: playbooks que requieren capacidades adicionales (CrewAI, intelligence loops, sandbox extendido).

**Tareas**:
1. Implementar `enterprise/orchestration/{crewai_bridge,debate_coordinator}.py`.
2. Implementar `enterprise/orchestration/goal_pursuit/` (4 archivos).
3. Implementar `enterprise/intelligence/{self_correction,cove_verifier,confidence_scorer,fewshot_retriever}.py`.
4. Implementar `enterprise/triggers/{event_listener,webhook_handler}.py`.
5. Implementar `enterprise/tooling/{adaptive_cache,output_formatter}.py`.
6. Crear playbooks: `decision-debate.yaml`, `market-research.yaml`, `compliance-audit.yaml`, `goal-pursuit.yaml`, `app-development.yaml`, `company-optimization.yaml`, `artifact-development.yaml`.

**Criterios verificables F4b**:
- [ ] Playbook `decision-debate` ejecuta 3-5 agentes con moderador.
- [ ] Playbook `goal-pursuit` ejecuta tarea autónoma con checkpoints.
- [ ] Playbook `app-development` genera un proyecto scaffold dado un goal.
- [ ] Playbook `company-optimization` produce brechas ISO/NTC con evidencia.
- [ ] Playbook `artifact-development` crea dashboard/pipeline verificable.

### F4c — Modos restantes (roadmap post-MVP, 1-2 semanas)

**Objetivo**: modos `CFO`, `Consultor Legal`, `Marketing`, `Vendedor B2B`, `Operaciones PYME`.

**Tareas**:
1. Crear 5 archivos en `config/modes/` con `company_geo` policies y skills permitidas.
2. Wiring con plugins skills `finance:`, `engineering:`, `design:`, etc.

**Criterios verificables F4c**:
- [ ] `/mode CFO` activable y carga skills `finance:*`.
- [ ] `/mode Consultor Legal` consulta normativa según `company_geo`.

### F5a — Dreaming básico + PI defense regex + Tool-gating (1 semana)

**Objetivo**: ciclo nocturno mínimo + protección básica.

**Tareas MVP**:
1. Implementar `enterprise/dreaming/{scheduler,phases,reporter}.py`.
2. Implementar tasks Dreaming MVP: `memory_consolidation`, `ingestion_sync`. Resto de tasks queda para F5b.
3. Implementar `enterprise/governance/prompt_injection_detector.py` con SOLO regex Lakera (sin embedding comparison todavía).
4. Tool-gating operativo: tools sin API key no aparecen en listing.
5. Audit trail básico operativo en JSONL (`~/.vigilador/audit/events_<fecha>.jsonl`). Tabla SQL `agent_modifications` queda para F5b.

**Criterios verificables F5a**:
- [ ] Cron 3 AM ejecuta Dreaming básico sin errores.
- [ ] PI defense regex bloquea correo con payload `"ignore previous instructions"`.
- [ ] Audit JSONL registra invocaciones de tools, decisiones del ComplexityClassifier y spawns de subagentes.

**Rollback F5a**: `features.dreaming: false` deshabilita ciclo nocturno.

### F5b — Autoaprendizaje completo + agent_modifications (roadmap post-MVP, 4-5 semanas)

**Objetivo**: 5 loops de autoaprendizaje + audit trail SQL + rollback de 1 click.

**Tareas**:
1. Implementar `enterprise/governance/{anomaly_detector,agent_modifier,approval_queue}.py`.
2. Tabla SQL `agent_modifications` con migration.
3. Implementar 5 loops Dreaming: Skill learning, Writing style, Prompt self-improvement, Tool composition, COMPANY self-update.
4. UI rollback de 1 click.
5. Implementar `enterprise/skills_marketplace/{k_dense_adapter,agency_agents_adapter,skill_loader,skill_curator}.py`.

**Criterios verificables F5b**:
- [ ] Los 5 loops generan al menos 1 propuesta cada uno tras 7 días de uso simulado.
- [ ] `AgentModifier` aplica un cambio a `config/soul.md` con audit trail visible.
- [ ] Rollback de 1 click revierte el cambio.

### F5c — Frontend completo (roadmap post-MVP, 2-3 semanas)

**Objetivo**: superficies de frontend restantes (artefactos + optimización + admin).

**Tareas**:
1. Frontend artefactos: dashboards/pipelines/metricas.
2. Frontend optimización: ISO/NTC plan de mejora.
3. Frontend admin: Dreaming Report viewer, audit changelog con rollback, MCP repo maintenance.

**Criterios verificables F5c**:
- [ ] Dashboard accesible en `/admin/dashboard` con métricas live.
- [ ] Audit changelog UI permite revertir cualquier cambio con 1 click.

### F5d — DR + SSO + compliance avanzado (roadmap post-MVP, 2-3 semanas)

**Objetivo**: producción enterprise-ready.

**Tareas**:
1. SSO/SAML/OIDC (Azure AD, Google Workspace SSO, Okta).
2. DR + backup automatizado (RTO 1h / RPO 24h).
3. Capability tokens granulares + revocación.
4. Compliance evidence (data residency, right-to-be-forgotten, DPA, SOC 2 checklist).
5. PII detection con Presidio (extiende PI defense de F5a).

**Criterios verificables F5d**:
- [ ] SSO funcional con Azure AD.
- [ ] DR test ejecutado: backup + restore semanal funciona.
- [ ] `forget_user(user_id)` borra en cascada todos los rastros.

---

## Onboarding wizard (F5 lo expone)

Primer arranque del 3.0 guía al usuario por:

1. Crear `COMPANY/*.md` vía formulario conversacional (decisión #42).
2. Conectar primer OAuth (Drive o OneDrive).
3. Lanzar primera ingestión (mostrar progreso).
4. Elegir Modos a activar del catálogo (default: todos).
5. Probar primer playbook con el modo seleccionado.
6. Elegir providers de embedding/reranker disponibles.
7. Declarar `company_geo` (pais/departamento/municipio) y fuentes iniciales.

Implementado en `frontend/src/enterprise/onboarding/` + endpoints `api/v2/enterprise/onboarding/*`.

---

## Plan de rollback por fase

| Fase | Riesgo principal | Rollback |
|---|---|---|
| F0 | Supuesto desmentido | Documentar y replantear; cero código que revertir. |
| F1 | Schema migration falla | DROP de tablas enterprise vía SQL; `enterprise/` no se importa todavía. |
| F2 | TurboVecIndex corrupto | Reconstruir TurboVecIndex desde fuentes/metadata indexadas; deshabilitar busqueda semantica nueva mientras se reconstruye. |
| F3 | Tool específica rota | Marcar `enabled: false` en `mcp-providers.json` o `external.yaml`; el resto del catálogo opera. |
| F4 | `AgentModifier` aplica cambio dañino | Rollback de 1 click vía audit trail; `AnomalyDetector` debería haber bloqueado antes. |
| F5 | Dreaming consume recursos excesivos | `features.dreaming: false`; loops vuelven a manual. |

---

## Gestión de la deuda 2.0 → 3.0

Lo que queda intocado por YAGNI (no se moderniza salvo demanda explícita):

| Elemento | Estado | Razón |
|---|---|---|
| 6 agentes de rama (AVANCES/COMERCIAL/...) | Intocados | Funcionan; el playbook `technology-watch` los envuelve. |
| Tests del 2.0 con `MemorySessionRepository` y `FakeDatabase` | Intocados | Patrón consolidado; los nuevos tests del 3.0 los reutilizan. |
| `infra/mcp/execution_client.py` del 2.0 | Intocado | Coexiste con `enterprise/tooling/mcp_client.py` (decisión #52). |
| Frontend React D3 actual | Intocado | El 3.0 añade vistas nuevas; las existentes siguen. |
| Specs 002-008 ya implementadas | Intocadas | Sus archivos en `specs/<NNN>-*/` quedan como histórico. |
| Gemini Embeddings del 2.0 | Intocado | El 3.0 permite seleccionarlo como provider API; `bge-m3` local es opcion, no reemplazo obligatorio. |
| Cohere Rerank del 2.0 | Intocado | `SemanticReranker` sigue disponible como provider API seleccionable. |

Si en F4-F5 emerge demanda concreta de modernizar algo del 2.0 (ej: migrar un agente de rama a `BaseAgent` con tool discovery progresivo), se hace como spec separado, no como parte de la migración base.

---

## Decisiones implementadas por este doc

Este doc consolida las decisiones de migración dispersas (ver `ANEXO-B-decision-log-por-tema.md`):

- **#3** (subpaquete `enterprise/` paralelo).
- **#9** (especialización por rol + tool discovery progresivo).
- **#26-35** (multi-tenancy, observability, DR, SSO, compliance, encryption, PII; quotas por usuario quedan obsoletas por C0).
- **#41** (embeddings/reranker seleccionables preservando providers API existentes).
- **#42** (onboarding wizard).
- **#43** (MigrationRunner + SQL crudo + update mechanism; reformulada).
- **#46** (Knowledge Graph dual).
- **#52** (MCPClient coexiste).
- **#54** (reducción de scope detectada por inventario).
- **#64** (MCPProcessSupervisor).
- **#72** (LocalAppDetector).
- **#82** (supuesto A10 capacidad de ejecución).
- **C0** canon operativo: frontend completo, preservacion workstreams/ports/infra, TurboVecIndex unico, providers seleccionables, indexacion empresarial, optimizacion, artefactos.
- **#84-95** (persistencia reformulada: metadata relacional + TurboVecIndex unico).

---

## Criterios de verificación globales

Tras completar las 6 fases:

1. **El 2.0 sigue funcionando idéntico**: `pytest` 100% verde, API `/api/v2/research/*` sin regresiones.
2. **El 3.0 expone su API en paralelo**: `/api/v2/enterprise/*` y `/api/channels/*` operativos.
3. **Los 7 Modos iniciales activables**: cada uno cambia SOUL aplicado, skills disponibles y tools allowlist.
4. **Los playbooks ejecutables**: incluyendo `app-development`, `company-optimization` y `artifact-development`.
5. **Audit trail operativo**: Dreaming Report llega con cambios revisables y rollback de 1 click funciona.
6. **MCPProcessSupervisor**: 15 procesos UP, restart automático funcional.
7. **TurboVecIndex unico** operativo con reconstruccion documentada desde fuentes/metadata.
8. **DR semanal**: backup + restore probados.
