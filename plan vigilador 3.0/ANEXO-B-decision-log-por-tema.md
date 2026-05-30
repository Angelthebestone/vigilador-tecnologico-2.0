# ANEXO B — Decision log por tema

> Las **114 decisiones** del plan maestro original (`_archive/plan-maestro-iter-1-12.md`) reorganizadas por dominio en lugar de cronológicamente. Cumple **decisión #83** del plan original ("futuras revisiones deberían consolidar en secciones temáticas").

> **Las 5 decisiones nuevas de esta sesión** (D1-D5) se incluyen en sus dominios correspondientes con marca `D[1-5]`.

> **C0 vigente desde 2026-05-25**: [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md) agrega 16 correcciones que reformulan frontend, providers de embedding/reranker, vectorizacion, preservacion 2.0, geografia, Claude local, quotas, automantenimiento, indexacion empresarial, optimizacion y artefactos.

> **C1 vigente desde 2026-05-26**: [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md) reduce el alcance a un MVP de 20 capacidades, 4 dominios, 3 modos, 3 playbooks y frontend mínimo. Introduce Xiaomimimo `mimo-v2-flash` como LLM default + MCP Google Workspace. Reformula #4, #7, #38, #75, #82.

> **Status**: `vigente` (aplica), `obsoleta` (preservada por trazabilidad), `reformulada` (sobrescrita por una decisión posterior — enlace al reformulador).

---

## Índice por dominio

1. [Arquitectura y orquestación](#1-arquitectura-y-orquestaci%C3%B3n)
2. [LLM y embeddings](#2-llm-y-embeddings)
3. [Persistencia y datos](#3-persistencia-y-datos)
4. [Catálogo de tools y extracción](#4-cat%C3%A1logo-de-tools-y-extracci%C3%B3n)
5. [Skills y marketplaces](#5-skills-y-marketplaces)
6. [Modos y personalidades](#6-modos-y-personalidades)
7. [Autonomía y autoaprendizaje](#7-autonom%C3%ADa-y-autoaprendizaje)
8. [Gobernanza, seguridad y compliance](#8-gobernanza-seguridad-y-compliance)
9. [Migración 2.0 → 3.0 y cronograma](#9-migraci%C3%B3n-20--30-y-cronograma)
10. [Canales y UX](#10-canales-y-ux)
11. [Templates y app-development](#11-templates-y-app-development)

---

## 1. Arquitectura y orquestación

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| #2 | 6 ramas actuales → playbook `technology-watch` (preservado) | vigente | [03](03-playbooks-y-orquestacion.md), [07](07-migracion-2.0-a-3.0.md) |
| #3 | Subpaquete `enterprise/` paralelo. Cero breaking changes | vigente | [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md) |
| #6 | CrewAI para combos nuevos + `BranchCoordinator` preservado | vigente | [03](03-playbooks-y-orquestacion.md), [07](07-migracion-2.0-a-3.0.md) |
| #8 | Orquestador complexity-aware. Sin límite de llamadas. Sub-agentes recursivos | vigente | [03](03-playbooks-y-orquestacion.md) |
| #9 | Especialización: rol + tools restringidas + tool discovery progresivo | vigente | [03](03-playbooks-y-orquestacion.md), [04](04-skills-y-capacidades.md) |
| #10 | Debate multi-agente con moderador (3-5 agentes + sintetizador) | vigente | [03](03-playbooks-y-orquestacion.md) |
| #21 | Deep-research como playbook explícito | vigente | [03](03-playbooks-y-orquestacion.md) |
| #46 | Knowledge Graph dual (investigación + empresarial) | vigente | [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md) |
| #48 | MoA reescritura sustancial para MiniMax | vigente | [03](03-playbooks-y-orquestacion.md) |
| #54 | Reducción de scope ~30% al detectar componentes ya en Hermes | vigente | [07](07-migracion-2.0-a-3.0.md) |
| #80 | Aclaración ContextCompressor (diseño propio inspirado en Hermes) | vigente | [05](05-autoaprendizaje-y-autonomia.md) |
| #81 | Fix CQS — health monitor proceso aparte | vigente | [01](01-vision-y-arquitectura.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| **C0** | Canon operativo corregido: preservar 2.0, frontend completo, adapters, discovery semantico, artefactos, optimizacion | vigente | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md) |
| #96 | Self-correction loop (Reflexion pattern) | vigente | [03](03-playbooks-y-orquestacion.md) |
| #97 | Chain-of-Verification (CoVe) | vigente | [03](03-playbooks-y-orquestacion.md) |
| #98 | Confidence scoring + abstention | vigente | [03](03-playbooks-y-orquestacion.md) |
| #99 | Few-shot retrieval para outputs consistentes | vigente | [03](03-playbooks-y-orquestacion.md) |
| #100 | Goal-driven mode (playbook `goal-pursuit`) | vigente | [03](03-playbooks-y-orquestacion.md) |
| #101 | Long-running tasks con pause/resume | vigente | [03](03-playbooks-y-orquestacion.md) |
| #102 | Proactive triggers event-driven | vigente | [03](03-playbooks-y-orquestacion.md) |
| #103 | Tool result caching adaptativo | vigente | [03](03-playbooks-y-orquestacion.md) |
| #104 | Citations obligatorias verificables | vigente | [03](03-playbooks-y-orquestacion.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #105 | Outputs duales structured + free-form | vigente | [03](03-playbooks-y-orquestacion.md) |
| #109 | Webhook bidireccional (subset de #102) | vigente | [03](03-playbooks-y-orquestacion.md) |

---

## 2. LLM y embeddings

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| **C1.1** **(esta sesión)** | **Xiaomimimo `mimo-v2-flash` como LLM default del MVP** (chat OpenAI-compatible + image understanding + web_search nativo). MiniMax queda como adapter opcional activable. | vigente | [00b](00b-mvp-scope-y-cronograma.md), [01](01-vision-y-arquitectura.md) |
| #7 | ~~Solo MiniMax: M-2.7 principal, M-2.5 para debates~~ | **reformulada por C1.1**: Xiaomimimo es default MVP; MiniMax pasa a adapter opcional implementable cuando se necesite | [00b](00b-mvp-scope-y-cronograma.md), [01](01-vision-y-arquitectura.md) |
| #38 | ~~Sin multi-LLM. Si MiniMax cae, harness inservible~~ | **reformulada por C1.1 + C0 #6**: adapters por proveedor; multi-LLM como capability seleccionable; el "solo MiniMax" original era política, ahora se relaja | [00b](00b-mvp-scope-y-cronograma.md), [01](01-vision-y-arquitectura.md) |
| #39 | Sin plan de continuidad si LLM principal cae | vigente (aplicada ahora a Xiaomimimo + MiniMax) | [01](01-vision-y-arquitectura.md) |
| #41 | ~~Embeddings + reranker locales con switch a Gemini~~ | **reformulada por C0**: providers API existentes (Gemini/Cohere) se preservan y se vuelven seleccionables; local es opcional | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md) |
| #79 | Aclaración embeddings vs LLM (solo MiniMax aplica al LLM generativo) | vigente | [01](01-vision-y-arquitectura.md) |
| #90 | Convención: vectores `float32` 768d en toda la pila | vigente | [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md) |

---

## 3. Persistencia y datos

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| #1 | TurboVec como índice vectorial primario | reformulada por C0: TurboVecIndex como indice vectorial unico del 3.0 | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md) |
| #51 | Session search: SQLite FTS5 (NO Postgres tsvector) | vigente | [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md) |
| #84 | ~~Arquitectura de persistencia: 5 motores con rol único~~ | **reformulada por C0**: metadata relacional + TurboVecIndex unico + JSONL/YAML; SQLite FTS opcional | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md) |
| #85 | ~~TurboVec primario + pgvector backup con A/B~~ | **obsoleta por C0**: no hay pgvector backup obligatorio ni A/B permanente | [00](00-canon-operativo-corregido.md), [07](07-migracion-2.0-a-3.0.md) |
| #86 | Multi-tenancy aplica a todas las capas | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #87 | Backup unifica 3 fuentes vivas (PG + TurboVec + SQLite) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #88 | ~~Migraciones: Alembic para PG; TurboVec/SQLite sin migrations~~ | **reformulada**: el 2.0 usa MigrationRunner + SQL crudo (`infra/db/migrations/NNN_*.sql`); Alembic descartado en spec 009 T009 (ver `docs/postgres-readiness.md`) | [07](07-migracion-2.0-a-3.0.md) |
| #89 | Configuración en `config/settings.yaml` | vigente | [01](01-vision-y-arquitectura.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #91 | ~~PostgreSQL 18+ como versión oficial mínima~~ | **reformulada por C0**: usar metadata DB existente; versiones concretas se validan en F0 | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md) |
| #92 | ~~UUIDv7 en tablas de alto volumen como requisito PG 18~~ | **reformulada por C0**: UUID ordenable es optimizacion opcional con fallback | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md) |
| #93 | ~~Async I/O de PG 18 como tuning recomendado en F0~~ | reformulada: tuning segun metadata DB instalada | [07](07-migracion-2.0-a-3.0.md) |
| #94 | Features de PG 18 descartados v3.0 | obsoleta por C0: no se fija PG 18 como condicion arquitectonica | [00](00-canon-operativo-corregido.md) |
| #95 | ~~Sin downgrade-path declarado (asume PG 18+)~~ | obsoleta por C0: no se asume PG 18+ | [00](00-canon-operativo-corregido.md), [07](07-migracion-2.0-a-3.0.md) |

---

## 4. Catálogo de tools y extracción

> **Sub-set C1 esta sesión** (alcance MVP):
>
> | ID | Decisión | Status | Doc destino |
> |---|---|---|---|
> | **C1.2** | Conservar Tiers 1 y 2; no eliminar archivos de Tier 3 ni sub-tools `*_local.py` (quedan documentados pero diferidos) | vigente | [06](06-catalogo-tools-y-extraccion.md), [00b](00b-mvp-scope-y-cronograma.md) |
> | **C1.3** | Dominios MVP: solo `search`, `web`, `research`, `documents`. Otros 13 documentados pero fuera del MVP | vigente | [06](06-catalogo-tools-y-extraccion.md), [00b](00b-mvp-scope-y-cronograma.md) |
> | **C1.4** | Añadir MCP `google-workspace-mcp` al Tier 2 como única adición del MVP vía `MCPProcessSupervisor` | vigente | [06](06-catalogo-tools-y-extraccion.md), [00b](00b-mvp-scope-y-cronograma.md) |
> | **C1.5** | Dominios nuevos (design/engineering/media/analytics) se conservan documentados pero NO se implementan en MVP. Arquitectura preparada para activarlos sin refactor | vigente | [06](06-catalogo-tools-y-extraccion.md), [00b](00b-mvp-scope-y-cronograma.md) |

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| #5 | ~~20 MCPs internalizados~~ | **obsoleta** (reformulada por #58, #75, #77) | [06](06-catalogo-tools-y-extraccion.md) |
| #11 | Origen explícito por tool (COPY-HERMES / CLONE-UPSTREAM / WRAP-SDK) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #12 | Computer Use copiada de Hermes adaptada a Windows 11 | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #14 | ~~35 tools sub-carpetizadas por dominio~~ | **obsoleta** (reformulada por #65, #75) | [06](06-catalogo-tools-y-extraccion.md) |
| #19 | File system tool COPY-HERMES | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #22 | Módulo de Templates (Jinja2 + DOCX/PDF/PPTX) | vigente | [04](04-skills-y-capacidades.md), [06](06-catalogo-tools-y-extraccion.md) |
| #24 | Módulo de reuniones (Teams + Zoom) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #25 | Google Forms en `google_workspace.py` | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #47 | Inventario de extracción formal como SSOT (=doc 06) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #48 | COPY-HERMES ampliado a ~45 archivos | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #49 | OpenClaw NO se traduce | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #50 | Browser tool: reescribir con playwright-python | vigente | [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md) |
| #52 | MCPClient de Hermes coexiste con el del 2.0 | vigente | [07](07-migracion-2.0-a-3.0.md) |
| #53 | `file_safety.py` y `redact.py` COPY-HERMES obligatorios | vigente | [06](06-catalogo-tools-y-extraccion.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #55 | Auditoría de licencias obligatoria en F0 | vigente | [06](06-catalogo-tools-y-extraccion.md), [07](07-migracion-2.0-a-3.0.md) |
| #56 | Orden de extracción: 11 sprints A-K | vigente | [06](06-catalogo-tools-y-extraccion.md), [07](07-migracion-2.0-a-3.0.md) |
| #57 | Regla de oro: Python → INTERNALIZAR; TS completo → externo; TS simple → traducir | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #58 | Catálogo final 3-tier (Tier 1/2/3) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #59 | MCPs LATAM bajo demanda (YAGNI) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #60 | MCPExecutionClient del 2.0 reutilizable para Tier 2 | vigente | [07](07-migracion-2.0-a-3.0.md) |
| #61 | Contrato `ToolWrapper` unificado + circuit breaker + logs estructurados | vigente | [06](06-catalogo-tools-y-extraccion.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #62 | ~55 capacidades (40 internas + 15 externas) | reformulada (final ~79 en #75) | [06](06-catalogo-tools-y-extraccion.md) |
| #63 | F3 reducida a ~8-10 sem (vs 12-15) | reformulada por #112 (sube a 16-26) | [07](07-migracion-2.0-a-3.0.md) |
| #64 | MCPProcessSupervisor para 15 procesos STDIO | vigente | [06](06-catalogo-tools-y-extraccion.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #65 | 4 dominios nuevos: design, engineering, media, analytics. Total 17 | vigente como roadmap (C1.5 los difiere al post-MVP, documentación conservada) | [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md), [00b](00b-mvp-scope-y-cronograma.md) |
| #66 | Legal no es dominio MCP (skills + templates) | vigente | [04](04-skills-y-capacidades.md) |
| #67 | API keys declaradas por cada tool (4 campos en contrato) | vigente | [06](06-catalogo-tools-y-extraccion.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #68 | Deduplicación estricta (1 entrada por función) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #69 | 17 tools FREE sin API key para Tier 1 | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #70 | 11 tools paid premium descartadas v3.0 inicial | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #71 | Sub-tools `*_local.py` por dominio (10 sub-tools) | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #72 | LocalAppDetector — gating automático | vigente | [06](06-catalogo-tools-y-extraccion.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #73 | Resolución cloud vs local: preferencia `local` por privacidad | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #74 | Plataformas soportadas por sub-tools locales | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #75 | Total catálogo: 79 capacidades (10 sub-tools locales nuevas) | vigente como roadmap completo (C1: MVP implementa solo 20; resto diferido) | [06](06-catalogo-tools-y-extraccion.md), [00b](00b-mvp-scope-y-cronograma.md) |
| #76 | Beneficio sub-tools locales: cobertura PYMEs no-cloud + privacidad | vigente | [06](06-catalogo-tools-y-extraccion.md) |
| #77 | SSOT del número de tools: ~79 desglosado | vigente | [01](01-vision-y-arquitectura.md), [06](06-catalogo-tools-y-extraccion.md) |
| #78 | Decisiones #5 y #14 marcadas obsoletas | vigente | (este anexo) |
| #113 | Catálogo capacidades funcionales finales sube a ~85 (+6 intelligence/autonomy) | vigente | [06](06-catalogo-tools-y-extraccion.md), [03](03-playbooks-y-orquestacion.md) |
| **C0** | SSOT de tools/MCPs con estado, owner, health, update_policy; copiar Hermes/OpenClaw solo modularizado | vigente | [00](00-canon-operativo-corregido.md), [06](06-catalogo-tools-y-extraccion.md) |

---

## 5. Skills y marketplaces

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| **D1** **(esta sesión)** | Jerarquía Agent compone Skills + integración de 2 marketplaces externos | vigente | [01](01-vision-y-arquitectura.md), [04](04-skills-y-capacidades.md) |
| #15 | Computer Use con Skill Learning (aprende por demostración) | vigente | [04](04-skills-y-capacidades.md), [05](05-autoaprendizaje-y-autonomia.md) |
| #20 | Writing style learning (módulo extensión Dreaming) | vigente | [04](04-skills-y-capacidades.md), [05](05-autoaprendizaje-y-autonomia.md) |
| **C0** | Importar `.claude/skills` y comandos como `external:claude-local` + discovery semantico | vigente | [00](00-canon-operativo-corregido.md), [04](04-skills-y-capacidades.md) |

---

## 6. Modos y personalidades

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| **D2** **(esta sesión)** | Modos por industria/rol preconfigurados (CEO, CFO, Legal, Vigilancia Tech, Marketing, B2B, Operaciones PYME) | vigente | [02](02-modos-y-personalidades.md) |
| #13 | COMPANY.md como contexto empresarial declarativo | vigente | [02](02-modos-y-personalidades.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #16 | COMPANY partido en 5 archivos (`identity`, `organization`, `processes`, `systems`, `policies`) | vigente | [02](02-modos-y-personalidades.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #40 | Idioma: interno inglés, externo en idioma del usuario (LanguageRouter) | vigente | [02](02-modos-y-personalidades.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #42 | Onboarding wizard (primer arranque guiado) | vigente | [02](02-modos-y-personalidades.md), [07](07-migracion-2.0-a-3.0.md) |
| **C0** | Modos sensibles a `company_geo` (pais/departamento/municipio) | vigente | [00](00-canon-operativo-corregido.md), [02](02-modos-y-personalidades.md) |

---

## 7. Autonomía y autoaprendizaje

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| **D4** **(esta sesión)** | Autoaprendizaje full-autonomy con audit trail + rollback de 1 click | vigente | [05](05-autoaprendizaje-y-autonomia.md) |
| #17 | Modo Dreaming (auto-mantenimiento nocturno 3 AM + idle 10 min) | vigente | [05](05-autoaprendizaje-y-autonomia.md) |
| #23 | Indexación automatizada en Dreaming (`ingestion_sync`) | vigente | [05](05-autoaprendizaje-y-autonomia.md) |
| #35 | Versionado de prompts/playbooks (`prompt_versions`) | reformulada — subsumida en `agent_modifications` por D4 | [05](05-autoaprendizaje-y-autonomia.md) |
| #44 | ~~Approval workflows acotados~~ — el agente NUNCA modifica config | **REFORMULADA por D4** (esta sesión) — full autonomy con audit trail. Approvals residuales en doc 08 | [05](05-autoaprendizaje-y-autonomia.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #82 | Supuesto A10 — capacidad de ejecución (28 sem con 2-3 ingenieros) | reformulada por C1: **MVP en 12-16 sem con 1-2 ingenieros**; roadmap completo conserva ~28 sem post-MVP | [07](07-migracion-2.0-a-3.0.md), [00b](00b-mvp-scope-y-cronograma.md) |
| #83 | Consolidar decisiones temáticamente (=este anexo) | vigente (cumplido por este anexo) | (este anexo) |
| #100 | Goal-driven mode | vigente (ya en sec. 1 — Arquitectura) | [03](03-playbooks-y-orquestacion.md) |
| #101 | Long-running tasks con pause/resume | vigente (ya en sec. 1) | [03](03-playbooks-y-orquestacion.md) |
| #110 | Scheduled outputs (cron Dreaming) | vigente | [05](05-autoaprendizaje-y-autonomia.md), [03](03-playbooks-y-orquestacion.md) |
| **C0** | Dreaming incluye automantenimiento admin y regulatory/local watcher | vigente | [00](00-canon-operativo-corregido.md), [05](05-autoaprendizaje-y-autonomia.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #112 | +3700 LOC adicionales — F3 sube a 16-26 sem, F4 a 22-25 sem | vigente | [07](07-migracion-2.0-a-3.0.md) |
| #114 | Supuesto A10 reforzado. Núcleo defendible: self-correction + CoVe + Citations + Caching + PI defense | vigente | [07](07-migracion-2.0-a-3.0.md) |

---

## 8. Gobernanza, seguridad y compliance

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| #18 | Tool-gating por API key (no aparece en listing si falta key) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #26 | Multi-tenancy desde día 1 (`tenant_id UUID NOT NULL`) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #27 | Observability (Prometheus + OpenTelemetry) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #28 | DR + backup (RTO 1h / RPO 24h) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #29 | ~~Quotas por usuario + circuit breaker per-user~~ | **obsoleta por C0**: version de prueba usa telemetria + circuit breakers tecnicos, no quotas por usuario | [00](00-canon-operativo-corregido.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #30 | SSO/SAML/OIDC (Azure AD, Google Workspace, Okta) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #31 | Compliance evidence (data residency, right-to-be-forgotten, DPA, SOC 2) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #32 | Encryption at rest + in transit + key rotation 90 días | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #33 | PII detection + redaction (Presidio, español+inglés) | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #34 | Conversational analytics + metrics dashboard | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #36 | Sin transacciones bancarias (cero capacidad de mover dinero) | vigente | [02](02-modos-y-personalidades.md), [08](08-gobernanza-seguridad-y-operaciones.md) |
| #37 | Sin CLI pública (solo canales) | vigente | [01](01-vision-y-arquitectura.md) |
| #45 | Política "no delete" en OAuth + gating-out de `delete_*` | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #106 | Prompt injection defense con cuarentena | vigente | [08](08-gobernanza-seguridad-y-operaciones.md) |
| #107 | Capability tokens granulares por sesión | vigente | [08](08-gobernanza-seguridad-y-operaciones.md), [05](05-autoaprendizaje-y-autonomia.md) |
| #108 | Anomaly detection en uso del agente | vigente | [08](08-gobernanza-seguridad-y-operaciones.md), [05](05-autoaprendizaje-y-autonomia.md) |
| **C0** | Sin quotas por usuario; company_geo y mantenimiento admin bajo gobernanza | vigente | [00](00-canon-operativo-corregido.md), [08](08-gobernanza-seguridad-y-operaciones.md) |

---

## 9. Migración 2.0 → 3.0 y cronograma

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| #43 | Update mechanism + migration runner (~~Alembic~~ → MigrationRunner + SQL crudo + auto-update sec) | **reformulada**: el 2.0 usa `MigrationRunner` forward-only con SQL crudo en `infra/db/migrations/NNN_*.sql`; Alembic descartado (spec 009 T009, `docs/postgres-readiness.md`) | [07](07-migracion-2.0-a-3.0.md), [08](08-gobernanza-seguridad-y-operaciones.md) |

(El resto de decisiones de migración están distribuidas en sus dominios respectivos; las dependencias entre fases y supuestos A1-A14 se consolidan en el doc 07 directamente.)

---

## 10. Canales y UX

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| #4 | Canales prioritarios: Web/SSE + Telegram + WhatsApp Cloud API | reformulada por C1.6: MVP solo Web/SSE; Telegram + WhatsApp difieren a roadmap | [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md), [00b](00b-mvp-scope-y-cronograma.md) |
| #111 | Voice channel descartado v3.0 (roadmap v3.1) | vigente | [07](07-migracion-2.0-a-3.0.md) |
| **C0** | Frontend web es consola principal completa, no solo canal de comunicacion | vigente | [00](00-canon-operativo-corregido.md), [01](01-vision-y-arquitectura.md), [07](07-migracion-2.0-a-3.0.md) |
| **C1.6** | Frontend MVP mínimo: 5 superficies (auth + onboarding + chat con modo + visor workstreams + tools/MCPs). Otras 3 (artefactos + optimización + admin) difieren a F5c | vigente | [00b](00b-mvp-scope-y-cronograma.md), [07](07-migracion-2.0-a-3.0.md) |

---

## 11. Templates y app-development

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| **D3** **(esta sesión)** | Spec-Kit como playbook interno `app-development` | vigente | [03](03-playbooks-y-orquestacion.md) |
| #22 | Módulo de Templates (ya listado en sec. 4) | vigente | [03](03-playbooks-y-orquestacion.md), [04](04-skills-y-capacidades.md) |
| **C0** | `company-optimization` y `artifact-development` como playbooks/modulos nuevos | vigente | [00](00-canon-operativo-corregido.md), [03](03-playbooks-y-orquestacion.md), [06](06-catalogo-tools-y-extraccion.md) |

---

## Estructura del set (D5)

| # | Decisión (resumen) | Status | Doc destino |
|---|---|---|---|
| **D5** **(esta sesión)** | Split por temas — set temático con canon operativo | vigente | [README](README.md) |
| **C0** | Canon operativo corregido como primera lectura y fuente de verdad | vigente | [00](00-canon-operativo-corregido.md), [README](README.md) |

---

## Resumen estadístico

| Métrica | Valor |
|---|---|
| Total decisiones del plan maestro original | 114 |
| Decisiones D1-D5 (sesión refinamiento) | 5 |
| Decisiones C0 (canon operativo corregido) | 16 |
| Decisiones C1 (alcance MVP) | 6 (C1.1-C1.6) |
| **Total decisiones en este anexo** | **141** |
| Decisiones vigentes | Ver tablas temáticas |
| Decisiones obsoletas (preservadas por trazabilidad) | Incluye #5, #14, #29, #62, #85 |
| Decisiones reformuladas | Incluye #1, #4, #7, #35, #38, #41, #44, #63, #82, #84 |

Las reformulaciones mantienen su entry para auditabilidad — solo cambia su status. Las dos reformulaciones más impactantes:
- **D4 sobre #44**: del "el agente NUNCA modifica config" al "puede modificar TODO con audit trail".
- **C1.1 sobre #7/#38**: del "solo MiniMax" al "Xiaomimimo `mimo-v2-flash` default; MiniMax adapter opcional".

---

## Cómo actualizar este anexo

Cada nueva decisión del proyecto debe:

1. **Identificarse con un número secuencial** (la próxima sería #115 o D6 si es de sesión de refinamiento).
2. **Categorizarse** en uno de los 11 dominios de esta tabla (o crear nuevo dominio si no encaja).
3. **Documentarse con su status inicial** (`vigente` por default).
4. **Enlazarse al doc que la implementa** (los docs temáticos del set 01-08).
5. **Si reformula una decisión previa**: marcar la previa como `reformulada` con link al reformulador.
6. **Si obsoleta una decisión previa**: marcar la previa como `obsoleta` con link al sucesor.

Nunca eliminar entradas. Constitución principio 5: trazabilidad histórica.
