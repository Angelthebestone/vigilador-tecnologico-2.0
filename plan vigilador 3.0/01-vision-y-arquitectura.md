# 01 — Visión y Arquitectura

> Documento de entrada técnico al set. Define la jerarquía conceptual, la estructura de carpetas final, los componentes nuevos vs preservados vs extendidos, y el stack tecnológico oficial. Cualquier otro doc del set asume estas definiciones.

> **Corrección vigente**: este documento se lee junto con [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md). El canon corrige frontend, providers de embeddings/reranker, vectorizacion, preservacion del 2.0, geografia, tools/MCPs, automantenimiento, optimizacion y artefactos.

---

## Visión

El **Vigilador Tecnológico 3.0 Enterprise** evoluciona el 2.0 (vigilancia tecnológica con 6 agentes de rama) hacia un **agente autónomo empresarial multi-propósito** que asiste al empresario en cualquier área de la empresa (finanzas, legal, marketing, ventas, operaciones, vigilancia tecnológica, desarrollo de apps internas, etc.).

**Principio rector**: lo que ya funciona se preserva. Lo nuevo se construye al lado. Cada componente nuevo cumple SRP y se conecta vía port existente o nuevo (DIP).

**Lo que el 3.0 NO es**:
- No es un reemplazo del 2.0 — el 2.0 sigue corriendo bajo el playbook `technology-watch`.
- No es un asistente de chat genérico — opera bajo un Modo empresarial con contexto cargado.
- No mueve dinero — todas las tools de finance son read-only o generan borradores (decisión #36).
- No depende de CLI pública para el usuario final — el **frontend web** es la consola primaria para login, onboarding, modos, workstreams, configuracion, tools/MCPs, indexacion, artefactos, optimizacion y admin. CLI interna solo para ops del propio harness.

---

## Alineación con la constitución v1.2.0

Tabla de alineación con `.specify/memory/constitution.md`:

| Principio | Cómo se aplica en la arquitectura 3.0 |
|---|---|
| 1. Pensar antes de codificar | Plan formal con supuestos explícitos (A1-A14, ver doc 07). |
| 2. Simplicidad obligatoria (KISS, YAGNI, AHA) | TurboVecIndex unico para vectores; sin pgvector backup obligatorio. Sin quotas por usuario en version de prueba. Subpaquete paralelo sin refactor lateral. |
| 3. Modularidad primero (SRP, SoC) | `enterprise/` con subcarpetas por concern (orchestration, ingestion, tooling, memory, modes, skills_marketplace, intelligence, triggers, auth, governance, dreaming, mcp, observability). Cada módulo una responsabilidad. |
| 4. Manejo de errores estricto | Sin try/except defensivos. Errores propagan con contexto. Circuit breakers solo en boundaries (MCPs externos, decisión #61). |
| 5. Cambios quirúrgicos | Doc 07 declara exactamente qué se preserva/extiende/crea. Cero refactor lateral en 2.0. |
| 6. Entrega verificable | Doc 07 define criterios verificables por fase F0-F5. Cada doc cierra con sección "Criterios de verificación". |
| DRY | TurboVecIndex implementa port `VectorIndex` existente. `DomainProfile` hereda de `BranchOverlay`. `AgentSkillPolicy` se reutiliza extendida. `00` es canon de decisiones y `06` es SSOT operacional de tools/MCPs. |
| WET | Tolerado temporalmente en F1 (playbook YAML duplica algo de matrix YAML) antes de abstraer. |
| LoD | Cada agente solo conoce su rol, sus tools y el moderador. No alcanza estado de hermanos. |
| Bajo Acoplamiento + DIP | Connectors implementan port `IngestionConnector`. ChannelAdapters implementan `ChannelAdapter`. ModeResolver implementa port `ModeResolutionStrategy`. |
| OCP | Nuevos playbooks/modos/skills se añaden por YAML sin tocar runners. Nuevos connectors implementan port. |
| ISP | Tool discovery progresivo: agentes ven solo el subset que necesitan. Mode filtra Skills y Tools antes de exponerlas. |
| CQS | `ToolRegistry.list_tools_for_role` solo LEE de `tool_health`; `HealthMonitor` solo escribe (decisión #81). |
| POLA | ComplexityClassifier loggea su decisión por sesión. YAML declarativo. ModeResolver log su elección. |
| Convención sobre configuración | Playbooks/Modos con defaults sensatos; config solo cuando se sobreescribe. |

---

## Jerarquía conceptual

El núcleo conceptual del 3.0 es esta jerarquía de **6 niveles** (D1 de esta sesión):

```
Channel                              ← interfaz: Web frontend | SSE | Telegram | WhatsApp | webhook
  └─ Mode                            ← persona empresarial activa + geografia: CEO | CFO | Legal | Vigilancia Tech | ...
      └─ Agent                       ← rol dentro del flujo: BranchAgent | DebateModerator | GoalDecomposer | ...
          └─ Playbook                ← flujo declarativo YAML: technology-watch | decision-debate | app-development | ...
              └─ Skill               ← receta atómica reutilizable: reconciliation | lead-research | sox-testing | ...
                  └─ Capability      ← verbo + schema: tavily_search | excel_local.refresh_pivot | docx_generate | ...
                      └─ Tool        ← módulo Python que implementa N capabilities
```

**Reglas de composición**:

| Nivel | ¿Quién lo invoca? | ¿Qué compone? |
|---|---|---|
| Channel | Sistema externo (HTTP, webhook) | Activa una sesión con un Mode |
| Mode | Sistema (al recibir `/mode X` o autodetectar) | Filtra qué Skills/Playbooks/Tools están disponibles + carga SOUL y COMPANY subset |
| Agent | PlaybookRunner | Invoca Skills permitidas por el Mode activo |
| Playbook | Mode (default o explícito) | Declara qué Agents instanciar y su flujo |
| Skill | Agent | Invoca Capabilities en orden definido por la receta |
| Capability | Skill (o Agent directamente) | Es la unidad ejecutable concreta |
| Tool | Capability | Es el módulo Python que implementa N capabilities y cumple `ToolWrapper` |

**Diferencia clave Agent vs Mode** (causa común de confusión):
- **Mode**: persona empresarial completa con SOUL/COMPANY/tono/vocabulario. Vive en `config/modes/<id>.yaml`. Ej: `CFO`.
- **Agent**: rol dentro de un flujo. Vive en `enterprise/agents/*.py` o se declara dentro de un playbook YAML. Ej: `RiskAdvocate` en `decision-debate`.
- Un Agent ejecutándose dentro de Mode `CFO` "habla como CFO" porque el SOUL overlay del Mode se inyecta en su prompt base.

Detalle de cada nivel:
- Mode → `02-modos-y-personalidades.md`
- Playbook → `03-playbooks-y-orquestacion.md`
- Skill → `04-skills-y-capacidades.md`
- Capability/Tool → `06-catalogo-tools-y-extraccion.md`

---

## Diagrama de capas (flujo end-to-end)

```
┌─────────────────────────────────────────────────────────────┐
│  Usuario por canal: Frontend Web/SSE | Telegram | WhatsApp   │
└──────────────────────────┬──────────────────────────────────┘
                           │ mensaje (con o sin /mode <X>)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ChannelGateway (api/channels/gateway.py)                   │
│  Adapta payload por canal, normaliza a InboundMessage       │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ModeResolver (enterprise/modes/mode_resolver.py)           │
│  Explícito (/mode CFO) → autodetect canal → autodetect      │
│  heurística → fallback LLM → default                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ Mode resuelto, sesión creada
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ModeContext (frozen snapshot al inicio de la sesión)       │
│  SOUL overlay + COMPANY subset + Skills allowlist           │
│  + Playbooks allowed + Tools allowlist                      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  OrchestratorService (preservado del 2.0)                   │
│  ↓ ↓ ↓ delega ↓ ↓ ↓                                         │
│  ComplexityClassifier → SIMPLE | MODERADA | COMPLEJA        │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PlaybookRunner (enterprise/orchestration/playbook_runner)  │
│  Carga YAML del playbook activo, instancia Agents           │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
        ┌──────────────────┴──────────────────────┐
        │                                          │
        ▼                                          ▼
┌──────────────────┐                  ┌────────────────────────┐
│ technology-watch │                  │ decision-debate /      │
│ → BranchCoord    │                  │ market-research /      │
│   (6 ramas 2.0)  │                  │ compliance-audit /     │
│ [PRESERVADO]     │                  │ goal-pursuit /         │
│                  │                  │ app-development /      │
│                  │                  │ general                │
│                  │                  │ → CrewAI Bridge        │
│                  │                  │                        │
│                  │                  │ Cada Agent puede       │
│                  │                  │ spawnear sub-agentes   │
│                  │                  │ recursivamente         │
│                  │                  │ (SubagentRegistry)     │
└──────────────────┘                  └────────────────────────┘
        │                                          │
        └──────────────────┬───────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Cada Agent invoca Skills (filtradas por Mode)              │
│  Cada Skill invoca Capabilities                             │
│  ToolRegistry.discover(role, intent)                        │
│  ParallelToolDispatcher → asyncio.gather de tool_calls      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
        ┌──────────────────┴──────────────────────┐
        ▼                                          ▼
┌──────────────────┐                  ┌────────────────────────┐
│ Tools Tier 1     │                  │ Tools Tier 2 (MCPs ext)│
│ Python local     │                  │ → MCPProcessSupervisor │
│ (40 + 10 *_local)│                  │ → STDIO procesos       │
└────────┬─────────┘                  └────────────┬───────────┘
         │                                          │
         └──────────────────┬───────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Persistencia                                                │
│  PostgreSQL (metadata relacional, audit, config operacional) │
│  TurboVecIndex (índice vectorial único del 3.0)              │
│  SQLite FTS5 opcional (busqueda textual de sesiones)         │
│  JSONL (logs ops + audit trail)                              │
│  YAML/Markdown (SOUL, COMPANY, playbooks, modes, skills)     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│  En paralelo, siempre corriendo                              │
│  • HealthMonitor cada 30s → actualiza tool_health            │
│  • Dreaming (cron 3 AM + idle > 10 min) → 8 fases            │
│    incluye autoaprendizaje, indexacion, normativa local      │
│    y automantenimiento admin de tools/MCPs (doc 05)          │
│  • Event listeners → triggers proactivos                     │
│  • Approval queue → mostrar pendientes al usuario            │
└─────────────────────────────────────────────────────────────┘
```

---

## Estructura de carpetas

Estructura final del repo tras F0-F5. Detalle completo de qué va en cada archivo en doc 07.

```
src/vigilancia_multiagente/
├── api/
│   ├── routes/                              [EXISTENTE 2.0 — preservado]
│   ├── channels/                [NUEVO 3.0] adapters por canal
│   │   ├── sse_adapter.py
│   │   ├── telegram_adapter.py
│   │   └── whatsapp_adapter.py
│   └── webhooks/                [NUEVO 3.0] triggers proactivos
├── application/                             [EXISTENTE 2.0 — preservado intacto]
│   ├── orchestration/orchestrator_service.py
│   ├── execution/branch_coordinator.py
│   ├── agents/{base.py + 6 agentes}
│   ├── governance/{prompt_composer.py + contract_loader.py}
│   ├── memory/, evaluation/, forecasting/, graph/, routing/, etc.
│   └── (preservar todo)
├── enterprise/                  [NUEVO — núcleo del 3.0]
│   ├── orchestration/
│   ├── modes/                   [NUEVO esta sesión — doc 02]
│   ├── skills_marketplace/      [NUEVO esta sesión — doc 04]
│   ├── intelligence/
│   ├── triggers/
│   ├── auth/
│   ├── governance/              incl. agent_modifier.py [NUEVO esta sesión — doc 05]
│   ├── memory/
│   ├── observability/
│   ├── ingestion/
│   ├── optimization/            [NUEVO] ISO/NTC/normas tecnicas + mejora procesos
│   ├── artifacts/               [NUEVO] dashboards, pipelines, metricas, notebooks
│   ├── tooling/                 incl. builtin/ con 17 dominios
│   ├── dreaming/                incl. 10 tasks (3 nuevas esta sesión — doc 05)
│   └── mcp/                     incl. process_supervisor.py
├── domain/                                  [EXISTENTE 2.0 — se amplía con DomainProfile]
│   ├── system_base.py                       intacto (SystemBase + BranchOverlay)
│   ├── domain_profile.py        [NUEVO]     DomainProfile(BranchOverlay)
│   ├── agent_role.py            [NUEVO]
│   ├── soul.py                  [NUEVO]
│   └── ports/
│       ├── channel_adapter.py   [NUEVO]
│       ├── ingestion_connector.py [NUEVO]
│       ├── mode_resolution_strategy.py [NUEVO]
│       └── vector_index.py                  intacto, lo implementa TurboVecIndex
└── infra/
    ├── mcp/                                 intacto 2.0
    ├── embeddings/
    │   ├── gemini_gateway.py                intacto 2.0, provider API seleccionable
    │   └── local_embeddings.py  [OPCIONAL]  bge-m3 si el usuario lo elige
    ├── reranking/
    │   └── semantic_reranker.py             intacto 2.0, Cohere API + fallback embeddings
    ├── model_adapters/          [NUEVO]     adapter por LLM/embedding/reranker provider
    ├── persistence/
    │   ├── vector_index.py                  intacto 2.0 (Postgres actual)
    │   ├── turbovec_index.py    [NUEVO]
    │   ├── ingestion_repository.py [NUEVO]
    │   ├── oauth_repository.py  [NUEVO]
    │   └── agent_modifications_repository.py [NUEVO esta sesión]
    ├── channels/                [NUEVO]
    └── llm/
        └── minimax_client.py                añade param `model` (M-2.7 | M-2.5)

plugins/                          [NUEVO — fuera de src/]
└── technology-watch/                        empaqueta el 2.0 como playbook

config/
├── skills/
│   ├── skill_matrix_default.yaml            intacto 2.0
│   ├── curated/                 [NUEVO]
│   └── learned/                 [NUEVO]
├── playbooks/                   [NUEVO]
│   ├── technology-watch.yaml
│   ├── decision-debate.yaml
│   ├── market-research.yaml
│   ├── compliance-audit.yaml
│   ├── general.yaml
│   ├── deep-research.yaml
│   ├── goal-pursuit.yaml
│   └── app-development.yaml     [NUEVO esta sesión — flujo Spec-Kit]
├── modes/                       [NUEVO esta sesión]
│   ├── default.yaml
│   ├── CEO.yaml
│   ├── CFO.yaml
│   ├── consultor-legal.yaml
│   ├── vigilancia-tech.yaml
│   ├── marketing.yaml
│   ├── vendedor-b2b.yaml
│   └── operaciones-pyme.yaml
├── soul.md                      [NUEVO]
├── company/                     [NUEVO]
│   ├── identity.md
│   ├── organization.md
│   ├── processes.md
│   ├── systems.md
│   └── policies.md
├── templates/                   [NUEVO]
│   ├── informes/
│   ├── propuestas/
│   ├── contratos/
│   ├── presentaciones/
│   └── correos/
├── channels/                    [NUEVO]
│   ├── web.yaml
│   ├── telegram.yaml
│   └── whatsapp.yaml
└── mcp/
    └── external.yaml            [NUEVO] ~15 MCPs externos Tier 2

frontend/
├── src/                                     intacto 2.0
└── src/enterprise/              [NUEVO 3.0]
    ├── auth/                    login + perfiles + credenciales
    ├── modes/                   selector de modo
    ├── onboarding/              wizard
    ├── configuration/           providers LLM/embedding/reranker, fuentes, preferencias
    ├── workstreams/             activacion y monitoreo de workstreams 2.0/3.0
    ├── sources/                 conectores cloud/locales + estado de indexacion
    ├── artifacts/               dashboards, pipelines y reportes internos
    ├── optimization/            ISO/NTC, planes de mejora, evidencia
    ├── audit/                   changelog + rollback
    ├── dreaming/                report viewer
    └── admin/                   MCP status, tool health
```

---

## Componentes nuevos vs preservados vs extendidos

Tabla consolidada (detalle granular en doc 07).

| Categoría | Componente | Acción | Principio |
|---|---|---|---|
| Preservar | `OrchestratorService` | Sin cambios | Cambios quirúrgicos |
| Preservar | `BranchCoordinator` | Sin cambios. Playbook `technology-watch` lo invoca | DRY |
| Preservar | `BaseBranchAgent` + 6 agentes | Sin cambios | OCP |
| Preservar | `PromptComposer`, `ContractLoader` | Sin cambios | DRY |
| Preservar | `MCPExecutionClient` + cache 2.0 | Sin cambios. v3.0 usa cliente paralelo | DIP |
| Preservar | 15 MCP providers actuales | Sin cambios | — |
| Preservar | Workstreams 2.0 (`application/evaluation/ws_a..ws_e`, pipeline steps, graph, artifacts, observability) | Sin cambios; se exponen en frontend 3.0 | Cambios quirúrgicos |
| Preservar | Ports existentes (`domain/ports/*`) | Son frontera contractual del 3.0 | DIP |
| Preservar | Infra existente (`mcp`, `embeddings`, `reranking`, `persistence`, `llm`) | Se envuelve con adapters, no se reemplaza | DRY |
| Preservar | Tests 2.0 + frontend D3 actual | Sin cambios; nuevas vistas se agregan al lado | Cambios quirúrgicos |
| Extender | `BranchOverlay` → `DomainProfile` | Subclase añade `connectors_required`, `acl_default_scopes`, `playbook_id` | OCP, LSP |
| Extender | port `VectorIndex` → adapter `TurboVecIndex` | Indice vectorial unico del 3.0 | DIP, OCP |
| Extender | `MiniMaxClient` y futuros modelos vía adapters | Adapter por modelo/proveedor; librerias para el resto | OCP |
| Extender | port `EmbeddingGateway` | `GeminiEmbeddingGateway` API existente + adapters opcionales configurables | DIP |
| Extender | port `Reranker` | `SemanticReranker` API existente + adapters opcionales configurables | DIP |
| Extender | `MCPProviderRegistry` carga `config/mcp/external.yaml` | Coexisten Tier 2 con providers 2.0 | OCP |
| Nuevo | Todo `enterprise/*` (orchestration, modes, skills_marketplace, intelligence, triggers, auth, governance, memory, observability, ingestion, tooling, dreaming, mcp) | Subsistema 3.0 | SRP |
| Nuevo | `plugins/technology-watch/` | Encapsula 2.0 como playbook | OCP, DRY |
| Nuevo | `config/{modes,playbooks,company,templates,skills/{curated,learned}}` | Config declarativa | OCP |
| Nuevo | Tabla SQL `agent_modifications` | Audit trail D4 | SRP |
| Nuevo | `frontend/src/enterprise/*` | Vistas admin 3.0 | SoC |
| Nuevo | `enterprise/optimization/*` | ISO, NTC, normas tecnicas, mejora de procesos | SRP |
| Nuevo | `enterprise/artifacts/*` | Dashboards, pipelines, metricas empresariales | SRP |

---

## Stack tecnológico oficial

| Componente | Tecnología | Razón |
|---|---|---|
| **LLM** | **Xiaomimimo `mimo-v2-flash` como default MVP** (chat OpenAI-compatible + image understanding + web_search nativo). MiniMax M-2.7/M-2.5 quedan como adapters opcionales activables. Adapter por modelo/proveedor (C0 #6) | C1.1 esta sesión: ver [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md). Evita acoplar el core al SDK/modelo. |
| **Embeddings** | Provider seleccionable: `GeminiEmbeddingGateway` API existente por defecto si ya está configurado; `bge-m3` local opcional | El 2.0 ya tiene embeddings API; no se reemplaza. |
| **Reranker** | Provider seleccionable: `SemanticReranker` existente con Cohere Rerank API + fallback por embeddings; local opcional | El 2.0 ya tiene reranker API. |
| **Lenguaje** | Python 3.11+ puro | Decisión #50 (cero Node en runtime para tools; MCPs externos via STDIO sí pueden ser Node) |
| **Framework agentes** | CrewAI 0.x para combos nuevos + `BranchCoordinator` preservado | Decisión #6 |
| **API** | FastAPI + asyncpg + SQLAlchemy | Mantener stack actual; versiones concretas se validan en F0 según entorno instalado |
| **Persistencia metadata** | PostgreSQL existente del proyecto | Metadata, auditoria, estados, credenciales y configuracion operacional. |
| **Índice vectorial** | TurboVecIndex como unico indice vectorial del 3.0 | Simplifica base/vectorizacion. |
| **RAG helpers** | LlamaIndex opcional si reduce loaders/chunking/retrieval | Preferir libreria estable antes de reimplementar. |
| **Full-text search** | SQLite FTS5 opcional | Solo si aporta busqueda textual de sesiones sin complejidad extra. |
| **Logs ops** | JSONL con rotación diaria | Decisión #84 |
| **Config** | YAML versionado en git | Decisión #84 |
| **Migrations** | MigrationRunner + SQL crudo | #43 reformulada (ver ANEXO-B) |
| **UUIDs** | UUID ordenable si la metadata DB lo soporta; fallback a UUID estándar | Optimización opcional, no condiciona la arquitectura |
| **Auth** | OAuth (Drive/OneDrive/Slack/GitHub) + SSO/SAML/OIDC para tenants empresariales | Decisión #30 |
| **Secrets** | Fernet-encrypted en `~/.vigilador/credentials/` | Decisión #53 (basado en patrón propio, no Hermes) |
| **Canales** | Web/SSE (existe), Telegram, WhatsApp Cloud API | Decisión #4 |
| **MCP transport** | STDIO para Tier 2 externos + HTTP para algunos | Decisión #57, #64 |
| **Process supervisor** | `MCPProcessSupervisor` ~150 LOC con backoff exponencial | Decisión #64 |
| **Observability** | Prometheus + OpenTelemetry tracing | Decisión #27 |
| **PII detection** | Microsoft Presidio (opt-in, español + inglés) | Decisión #33 |
| **Computer use** | Hermes adaptado a Windows 11 (`pyautogui` + `pygetwindow` + `mss`) | Decisión #12, #15 |
| **Browser** | playwright-python (cero Node) | Decisión #50 |
| **Apps locales** | `xlwings`, `pywin32`, `tableauhyperapi`, `pbi-tools` | Decisión #71-72 |
| **Scheduler Dreaming** | APScheduler (cron + idle trigger) | Decisión #17 |
| **Frontend** | React + D3 existente + consola completa en `src/enterprise/` | Producto principal para usuario/admin |
| **Skills marketplaces externos** | `K-Dense-AI/scientific-agent-skills` + `msitarzewski/agency-agents` + Spec-Kit como playbook | D1, D3 esta sesión |

---

## Adapter LLM — Xiaomimimo (C1.1)

El MVP usa **Xiaomimimo `mimo-v2-flash`** como LLM default. Documentación oficial:
- Chat OpenAI-compatible: `https://platform.xiaomimimo.com/docs/en-US/api/chat/openai-api`
- Image understanding: `https://platform.xiaomimimo.com/docs/en-US/usage-guide/multimodal-understanding/image-understanding`
- Web search nativo built-in: `https://platform.xiaomimimo.com/docs/en-US/usage-guide/tool-calling/web-search`

**Implementación**: `infra/llm/xiaomimimo_client.py` (nuevo adapter del port LLM). Usa el SDK OpenAI con `base_url="https://platform.xiaomimimo.com/v1"`. Reemplaza el papel default que tenía `MiniMaxClient` en el plan original.

**Multi-adapter por C0 #6**: el runtime no se acopla al SDK concreto. `MiniMaxClient` se preserva intacto y queda activable con `llm.adapters.minimax.enabled: true` en `config/settings.yaml`. Casos de uso para activar MiniMax: combos M-2.7/M-2.5 en `decision-debate` cuando se quiera diversidad cognitiva con dos modelos.

**Web search nativo del LLM**: complementa (no reemplaza) los MCPs `tavily`/`exa`/`brave`. Útil para queries simples de bajo costo sin invocar MCP externo. El `OrchestratorService` decide cuándo usar uno u otro según la complejidad detectada.

**Image understanding nativo**: puede sustituir el MCP `minimax-image` del 2.0 si se prefiere unificar provider; `minimax-image` se mantiene registrado como fallback.

Detalle completo del alcance, cronograma y criterios de salida del MVP en [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md).

---

## Decisiones implementadas por este doc

Este doc consolida decisiones arquitectónicas y de visión (ver `ANEXO-B-decision-log-por-tema.md`):

- **D1** esta sesión: jerarquía Agent>Mode>Skill>Capability.
- **C0** canon operativo corregido: frontend completo, providers seleccionables, TurboVecIndex unico, preservacion 2.0, geografia, automantenimiento, optimizacion y artefactos.
- **C1.1** Xiaomimimo `mimo-v2-flash` como LLM default del MVP. MiniMax como adapter opcional. Ver [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md).
- **#1-2** plan maestro: TurboVecIndex + 6 ramas como playbook.
- **#3-5** estructura subpaquete + canales + (#5 obsoleto).
- **#6-10** CrewAI + LLM + orquestador complexity-aware + tool discovery progresivo + debate.
- **#11** origen explícito por tool (COPY-HERMES / CLONE-UPSTREAM / WRAP-SDK).
- **#46** Knowledge Graph dual.
- **#57-63** estrategia 3-tier MCPs.
- **#71-76** sub-tools `*_local.py`.
- **#79** clarificación embeddings vs LLM.
- **#81** fix CQS health monitor.
- **#84-95** stack persistencia reformulado por C0: metadata relacional + TurboVecIndex unico.

---

## Criterios de verificación

Tras implementar la arquitectura:

1. **Test estructural**: `src/vigilancia_multiagente/enterprise/` existe con las 13 subcarpetas listadas.
2. **Test de aislamiento**: borrar `enterprise/` no rompe ningún test del 2.0.
3. **Test de jerarquía**: una sesión que entra por Telegram con `/mode CFO` produce un log que muestra Mode resuelto → Playbook seleccionado → Agents instanciados → Skills invocadas → Capabilities ejecutadas (auditabilidad POLA).
4. **Test de stack**: `vigilador-admin stack info` reporta adapter LLM activo, embedding provider activo, reranker provider activo, TurboVecIndex y metadata DB.
5. **Test de constitución**: ejecutar `python scripts/check-layer-imports.py` (existe en el 2.0, spec 006) sobre el código del 3.0 — sin violaciones de capa.
