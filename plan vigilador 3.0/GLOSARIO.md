# Glosario — Vigilador Tecnológico 3.0 Enterprise

> Definiciones autoritativas. Todos los demás documentos del set asumen estos términos. Cuando un concepto aparezca por primera vez en otro doc, debe coincidir con esta definición o el doc está desactualizado.

> **Corrección vigente**: este glosario sigue [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md). Definiciones previas sobre pgvector backup, quotas por usuario o embeddings locales obligatorios quedan reformuladas.

---

## Conceptos arquitectónicos

**Agent** — Personalidad IA con rol empresarial, contexto COMPANY subset, catálogo de Skills permitidas y memoria. Hereda de `BaseBranchAgent` (preservado del 2.0) o se construye con CrewAI. Un Agent SIN Modo activo no opera; siempre se invoca dentro de un Modo. Ej: los 6 agentes de rama (`AvancesAgent`, `RiesgoAgent`, …) son Agents legacy del 2.0; `CFOAgent` es un Agent nuevo del 3.0.

**Mode** — Configuración preconfigurada que materializa una persona empresarial. `Mode = SOUL subset + COMPANY subset + company_geo + skills permitidas + playbooks default`. Activación: `/mode CFO` desde cualquier canal. Ejemplos: `CEO`, `CFO`, `Consultor Legal`, `Vigilancia Tech` (= playbook `technology-watch` preservado), `Marketing`, `Vendedor B2B`, `Operaciones PYME`. Un Modo es la **unidad user-facing** del 3.0.

**Skill** — Receta atómica reutilizable expresada en `SKILL.md` (formato heredado de los marketplaces externos `K-Dense-AI/scientific-agent-skills` y `msitarzewski/agency-agents`). Metadata declarativa + bloque Python opcional + ejemplos. Una Skill compone 1-N Capabilities. Ej: `skill: reconciliation` invoca `tool: excel_local` + `tool: quickbooks` + lógica propia.

**Capability** — Funcionalidad expuesta por una Tool (verbo + schema JSON). Ej: `tavily_search`, `firecrawl_scrape`, `excel_local.refresh_pivot`. El conteo exacto vive en el SSOT del doc 06; no se infla por conteo, se incorpora por utilidad y mantenimiento claro.

**Tool** — Módulo Python en `enterprise/tooling/builtin/<dominio>/` que implementa 1-N Capabilities y cumple el contrato `ToolWrapper` unificado (decisión #61). Ej: `tools/builtin/search/tavily.py` expone capability `tavily_search`. Sinónimos en contextos MCP: "MCP tool" = capability expuesta por un MCP externo Tier 2.

**Playbook** — YAML declarativo en `config/playbooks/<id>.yaml` que define un flujo multi-agente reutilizable. Ej: `technology-watch.yaml`, `decision-debate.yaml`, `app-development.yaml` (flujo Spec-Kit), `goal-pursuit.yaml`. El `PlaybookRunner` lo carga e instancia los agentes que declara.

**Domain** — Carpeta funcional bajo `enterprise/tooling/builtin/<dominio>/`. Dominios base: `search`, `web`, `documents`, `productivity`, `meetings`, `crm`, `communication`, `finance`, `desktop`, `code`, `research`, `people`, `personalization`, `design`, `engineering`, `media`, `analytics`, `optimization`, `artifacts`.

**DomainProfile** — Subclase de `BranchOverlay` que añade `connectors_required`, `acl_default_scopes`, `playbook_id`. Cada playbook tiene su DomainProfile asociado (decisión #46, evolución del 2.0).

**Company geo (`company_geo`)** — Contexto geografico de la empresa: pais, departamento/estado, municipio/ciudad y zona horaria. Se usa para adaptar normativa, impuestos, tasas, permisos, normas tecnicas y fuentes oficiales. Ejemplo inicial: Colombia, Santander, Barrancabermeja.

**Model adapter** — Adaptador por modelo/proveedor que implementa un contrato estable de LLM, embedding o reranker. Evita que el core dependa directamente de SDKs concretos.

---

## Conceptos de orquestación

**ComplexityClassifier** — Step de 1 llamada corta a MiniMax M-2.7 que clasifica una tarea entrante en `SIMPLE | MODERADA | COMPLEJA`. Despliega 1-N agentes según el resultado. Sin límite global de llamadas (decisión #8).

**BranchCoordinator** — Componente del 2.0 (`application/execution/branch_coordinator.py`) que ejecuta las 6 ramas de `technology-watch` en paralelo vía `asyncio.gather()`. Preservado intacto en 3.0; lo invoca el playbook `technology-watch`.

**OrchestratorService** — Componente del 2.0 (`application/orchestration/orchestrator_service.py`) que gestiona el ciclo de vida de una sesión. Preservado intacto.

**SubagentRegistry** — Persiste el árbol de sub-agentes (`parent_session_id`, `depth`, `spawn_reason`). Habilita recursión: cualquier agente puede spawnear sub-agentes (depth-aware con guardrails). Base copy-Hermes de `process_registry`.

**PlaybookRunner** — Carga YAML del playbook, instancia agentes según declaración, los conecta al `ToolRegistry` filtrado por rol. Vive en `enterprise/orchestration/playbook_runner.py`.

**CrewAI Bridge** — Wrapper en `enterprise/orchestration/crewai_bridge.py` sobre `crewai.Crew/Agent/Task` para combos nuevos (debate, market-research). Coexiste con `BranchCoordinator` (decisión #6).

**MoA (Mixture of Agents)** — Patrón arXiv:2406.04692. 3-4 instancias MiniMax M-2.7 con temperaturas distintas + 1 agregador M-2.7. Reescritura sustancial de `mixture_of_agents_tool.py` de Hermes (decisión #48).

**CoVe (Chain-of-Verification)** — Patrón Meta 2023. Antes de afirmar un hecho factual, agente genera 3-5 preguntas de verificación, las responde con tools y solo afirma si son consistentes. Reduce alucinaciones 40-60% (decisión #97).

**Goal-pursuit** — Playbook que persigue objetivos durante horas/días. Componentes: `GoalDecomposer`, `StepDependencyResolver`, `CheckpointReporter`, `ApprovalGate`. Diferencia con orquestador reactivo: persigue objetivos, no responde preguntas (decisión #100).

**Company optimization** — Playbook/modulo para diagnosticar y mejorar procesos empresariales contra ISO, NTC, SST, calidad, seguridad de informacion, gestion documental u otras normas aplicables. Produce brechas, evidencia, plan de accion y seguimiento.

**Artifact development** — Playbook/modulo para crear dashboards, pipelines, notebooks/scripts y reportes programados de metricas empresariales. Extiende `application/artifacts/` con `enterprise/artifacts/`.

---

## Conceptos de persistencia

**TurboVecIndex** — Implementacion del port `VectorIndex` y **indice vectorial unico del 3.0**. Persiste en `~/.vigilador/turbovec/<tenant>.tq`. Debe poder reconstruirse desde fuentes/metadata indexadas.

**pgvector** — Extension PostgreSQL para vectores. En el canon corregido no es backup obligatorio ni requisito del 3.0; puede existir por compatibilidad historica del 2.0 o instalaciones previas, pero el 3.0 usa TurboVecIndex como indice vectorial.

**SQLite FTS5** — Cross-session full-text search sobre transcripts. Built-in Python 3.11+. Modos DISCOVERY/SCROLL/BROWSE. COPY-HERMES de `session_search_tool.py` (decisión #51). NO usar Postgres tsvector.

**ACL scope** — Etiqueta declarativa por chunk (`tenant_id` + `roles[]` + `users[]`). Filtro WHERE en queries. Aplicado por `acl_resolver.py` en ingestion.

**Frozen snapshot** — Lectura única de `MEMORY.md` + `USER.md` + `SOUL.md` + `COMPANY/*.md` al inicio de la sesión. NO se vuelve a leer durante la sesión. Patrón de Hermes (`memory_tool.py`).

**Audit trail (`agent_modifications`)** — Tabla SQL + JSONL diario donde el agente registra TODA mutación a `config/` (skills, prompts, SOUL, COMPANY, templates, políticas). Columnas: `id, tenant_id, target_file, diff, applied_at, rollback_token, agent_id, justification, status`. Habilita rollback de un click. **Núcleo de la decisión D4 de esta sesión** (full autonomy con guardrails).

---

## Conceptos de governance

**SOUL** — `config/soul.md`. Personalidad del asistente (tono, valores, vocativos). Leído como frozen snapshot. Con D4: el agente puede proponer y aplicar cambios con audit trail.

**COMPANY** — Carpeta `config/company/` partida en 5 archivos (decisión #16): `identity.md`, `organization.md`, `processes.md`, `systems.md`, `policies.md`. Contexto empresarial declarativo.

**Capability token** — Token efímero, revocable, con scope/TTL/rate-limit per-token. En lugar de "agente tiene acceso a Slack", específicamente "agente puede enviar mensajes a `#ventas` hasta las 18:00 hoy". Tabla `capability_tokens` (decisión #107).

**Quota por usuario** — Decision obsoleta para la version de prueba. Se mantiene telemetria de uso/costo y circuit breakers tecnicos, pero no tiers ni bloqueo `429` por consumo de usuario.

**Tool-gating** — Mecanismo que oculta tools del listing del agente cuando: (a) falta API key (decisión #18), (b) circuit breaker DOWN (decisión #61), (c) app local no instalada para `*_local.py` (decisión #72), (d) capability token expirado/revocado (decisión #107).

**MCPProcessSupervisor** — Gestor de pool de ~15 procesos STDIO de MCPs externos Tier 2. Auto-restart con backoff exponencial, healthcheck cada 60s, alerta tras 5 fallos consecutivos. CLI admin `vigilador-admin mcp <list|restart|...>` (decisión #64).

**LocalAppDetector** — Detecta apps locales instaladas al boot vía registry Windows + `/Applications/` macOS. Auto-gating de tools `*_local.py` (decisión #72).

**LanguageRouter** — Componente en `PromptComposer` que detecta locale del usuario por turno. Interno (lo que ve el LLM) en inglés; externo (lo que ve el usuario) en idioma detectado, default español (decisión #40).

**Prompt injection defense (PI defense)** — Detector que cuarentena inputs externos (correos, PDFs, scrapeo, mensajes) ANTES de tocar el LLM. Patrones custom + dataset Lakera + embeddings vs corpus ataques. Tabla `pi_quarantine` (decisión #106).

**Anomaly detector** — Stats sobre `audit_events_jsonl_index`. Baseline de patrones del usuario; detección de desviaciones bloquea acciones autónomas anormales (decisión #108).

---

## Conceptos del autoaprendizaje

**Dreaming** — Auto-mantenimiento del harness. Triggers: cron nocturno 3 AM + idle > 10 min. Fases: consolidación memoria, curador de skills, self-improvement, refresh SOUL/COMPANY, ingestion sync, regulatory/local watch, index maintenance, scheduled artifacts/reports, admin repo maintenance y audit report.

**Writing Style learning** — Módulo que analiza correos previos del usuario, infiere estilo personal (tono, longitud, formalidad, firma) y lo aplica al redactar (decisión #20).

**Skill Learning** — El agente aprende a usar sitios/apps por demostración y guarda el procedimiento como skill reutilizable. Auto-corrección por vision + AX tree (decisión #15).

**Prompt self-improvement** — Loop NUEVO (doc 05). Analiza outputs rechazados por el usuario, genera variante del prompt, A/B test, promueve la mejor. Audit trail.

**Tool composition** — Loop NUEVO (doc 05). Detecta patrones de invocación repetidos en `audit_events_jsonl_index`, genera macro como skill, propone al usuario.

**COMPANY self-update** — Loop NUEVO (doc 05). Detecta gaps en COMPANY/*.md por preguntas no respondidas, propone update vía audit trail.

**Regulatory/local watcher** — Loop de Dreaming que usa `company_geo` para buscar fuentes oficiales vigentes por pais/departamento/municipio antes de proponer cambios normativos, tributarios o de normas tecnicas.

**Admin repository maintenance** — Loop de Dreaming que revisa repos clonados de tools/MCPs/skills contra upstream, detecta releases/CVEs/nuevas capabilities y genera propuestas admin con pruebas antes de promover cambios.

**Claude local skill** — Skill importada desde `.claude/skills/*/SKILL.md` o comando local equivalente. Source: `external:claude-local`. Se carga por adapter, con hash, origen, permisos y sandbox/approval si tiene efectos.

**Skill curator** — Sub-tarea de Dreaming. Lifecycle: skill propuesto → quarantine → ejecuciones de prueba → promoción a `skills/learned/` o descarte. Base COPY-HERMES de `skill_provenance.py` + `skill_usage.py`.

---

## Tabla de siglas

| Sigla | Significado |
|---|---|
| **SRP** | Single Responsibility Principle |
| **OCP** | Open/Closed Principle |
| **ISP** | Interface Segregation Principle |
| **DIP** | Dependency Inversion Principle |
| **LSP** | Liskov Substitution Principle |
| **KISS** | Keep It Simple, Stupid |
| **YAGNI** | You Aren't Gonna Need It |
| **DRY** | Don't Repeat Yourself |
| **WET** | Write Everything Twice (tolerado temporalmente — constitución) |
| **AHA** | Avoid Hasty Abstractions |
| **CQS** | Command-Query Separation |
| **POLA** | Principle Of Least Astonishment |
| **LoD** | Law of Demeter |
| **PI** | Prompt Injection |
| **PII** | Personally Identifiable Information |
| **OTel** | OpenTelemetry |
| **SSE** | Server-Sent Events |
| **FTS** | Full-Text Search |
| **MCP** | Model Context Protocol |
| **MoA** | Mixture of Agents |
| **CoVe** | Chain-of-Verification |
| **DR** | Disaster Recovery |
| **RTO** | Recovery Time Objective |
| **RPO** | Recovery Point Objective |
| **SSO** | Single Sign-On |
| **SAML** | Security Assertion Markup Language |
| **OIDC** | OpenID Connect |
| **TDE** | Transparent Data Encryption |
| **DAG** | Directed Acyclic Graph |
| **SSOT** | Single Source Of Truth |

---

## Convención de versionado de este glosario

Cuando se añade/modifica un concepto en cualquier doc del set, se actualiza esta entrada **en el mismo PR**. Si una definición de aquí entra en conflicto con un doc temático, la del glosario manda (los docs deben ajustarse, no al revés).
