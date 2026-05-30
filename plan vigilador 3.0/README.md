# Vigilador Tecnológico 3.0 Enterprise — Set de planes

> Refactorización del plan original hacia un set temático navegable. **Primera lectura obligatoria**: [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md). Ese canon manda sobre cualquier decisión anterior que haya quedado repetida, obsoleta o desincronizada.

---

## Visión 3.0 en 3 minutos

El **Vigilador Tecnológico 3.0** evoluciona el 2.0 (centrado en vigilancia tecnológica con 6 agentes de rama) hacia un **agente autónomo empresarial multi-propósito** que asiste al empresario en CUALQUIER área de la empresa:

- **Cero breaking changes al 2.0**: subpaquete `src/vigilancia_multiagente/enterprise/` paralelo. La API `/research/*` y los 6 agentes existentes siguen idénticos.
- **Frontend como consola principal**: login, onboarding, chat, modos, workstreams, configuracion de providers, indexacion, tools/MCPs, Dreaming, artefactos, optimizacion y admin. No es solo un canal de comunicacion.
- **Núcleo conceptual nuevo**: jerarquía `Channel → Mode → Agent → Playbook → Skill → Capability`, preservando el flujo `technology-watch` del 2.0.
- **Adapters por modelo/proveedor**: **Xiaomimimo `mimo-v2-flash` es el LLM default del MVP** (chat OpenAI-compatible + image understanding + web_search nativo). MiniMax queda como adapter opcional. Embeddings y rerankers ya existentes por API (`GeminiEmbeddingGateway`, `SemanticReranker`/Cohere) se preservan y se vuelven seleccionables. Adaptadores locales como `bge-m3` son opcionales.
- **Vectorizacion simplificada**: `TurboVecIndex` es el indice vectorial unico del 3.0; PostgreSQL queda para metadata/auditoria. Sin pgvector backup obligatorio ni A/B permanente.
- **Catalogo de capacidades con descubrimiento semantico**: tools y skills se listan por metadata corta y solo cargan fichas completas cuando son candidatas.
- **Modos por industria/rol y geografia**: `CEO`, `CFO`, `Consultor Legal`, `Vigilancia Tech`, `Marketing`, `Vendedor B2B`, `Operaciones PYME`; además cargan pais/departamento/municipio de la empresa para normativa, impuestos y fuentes locales.
- **Skills marketplace + Claude local**: integración de marketplaces externos y de `.claude/skills`/comandos como `external:claude-local`.
- **Spec-Kit como playbook interno** `app-development`: el agente puede generar apps DENTRO del PC del usuario siguiendo el flujo `constitution → specify → plan → tasks → analyze → implement`.
- **Artefactos y optimizacion empresarial**: dashboards, pipelines, metricas, reportes, ISO/NTC/normas tecnicas y planes de mejora.
- **Autoaprendizaje con audit trail**: el agente puede mejorar skills/prompts/config con diff/timestamp/rollback y approvals residuales.
- **Canales**: Web/SSE (existe) + Telegram + WhatsApp Cloud API.
- **Dreaming mode**: auto-mantenimiento nocturno, indexacion empresarial, revision normativa localizada y mantenimiento admin de repos tools/MCPs.

**Principio rector**: lo que ya funciona se preserva. Lo nuevo se construye al lado. Cada componente nuevo cumple SRP y se conecta vía port existente o nuevo (DIP).

---

## Decisiones vigentes de este refinamiento

Cristalizadas vía AskUserQuestion al inicio del refinamiento:

| ID | Decisión | Doc que la implementa |
|---|---|---|
| **C0** | **Canon operativo corregido**: 16 ajustes que mandan sobre el set anterior | [00](00-canon-operativo-corregido.md) |
| **C1** | **Alcance MVP reducido**: 20 capacidades (vs 79 roadmap), 4 dominios, 3 modos, 3 playbooks, frontend mínimo, LLM Xiaomimimo `mimo-v2-flash` default, Google Workspace MCP. Cronograma 12-16 sem | [00b](00b-mvp-scope-y-cronograma.md) |
| **D1** | Jerarquía **Agent compone Skills** (no son conceptos paralelos) | [01](01-vision-y-arquitectura.md), [04](04-skills-y-capacidades.md) |
| **D2** | **Modos por industria/rol** (CEO/CFO/Legal/Vigilancia Tech/Marketing/B2B/Operaciones PYME) | [02](02-modos-y-personalidades.md) |
| **D3** | **Spec-Kit como playbook interno** `app-development` (apps internas empresa, no para clientes finales) | [03](03-playbooks-y-orquestacion.md) |
| **D4** | **Autoaprendizaje full-autonomy con audit trail** — REESCRIBE decisión #44 del plan original | [05](05-autoaprendizaje-y-autonomia.md) |
| **D5** | **Split por temas** — set temático + canon operativo | este README |

---

## Mapa del set

| Doc | Propósito | Cuándo leer |
|---|---|---|
| [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md) | Fuente de verdad correctiva (C0): 16 decisiones vigentes y obsoletas | Primero, siempre |
| [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md) | **Alcance MVP (C1)**: 20 capacidades, 4 dominios, 3 modos, 3 playbooks, frontend mínimo, cronograma 12-16 sem | Inmediatamente después del canon C0 |
| [README.md](README.md) | Índice + visión rápida | Primero, siempre |
| [GLOSARIO.md](GLOSARIO.md) | Definiciones autoritativas | Cuando aparezca un término no claro |
| [01-vision-y-arquitectura.md](01-vision-y-arquitectura.md) | Jerarquía Agent/Mode/Skill/Capability + estructura de carpetas + stack | Antes de implementar cualquier cosa |
| [02-modos-y-personalidades.md](02-modos-y-personalidades.md) | Catálogo de Modos + schema YAML + composición | Para entender la unidad user-facing del 3.0 |
| [03-playbooks-y-orquestacion.md](03-playbooks-y-orquestacion.md) | Playbooks (incl. `app-development` Spec-Kit) + ComplexityClassifier + SubagentRegistry + MoA + goal-pursuit | Para diseñar un flujo multi-agente |
| [04-skills-y-capacidades.md](04-skills-y-capacidades.md) | Skill vs Capability vs Tool + schema `SKILL.md` + marketplaces externos | Para crear o integrar skills |
| [05-autoaprendizaje-y-autonomia.md](05-autoaprendizaje-y-autonomia.md) | Loops de mejora continua + audit trail + rollback | Para entender el ciclo de mejora del agente |
| [06-catalogo-tools-y-extraccion.md](06-catalogo-tools-y-extraccion.md) | **SSOT operacional**: 79 capacidades + estrategia COPY-HERMES/WRAP-SDK/CLONE | Para implementar tools concretas (Sprints A-K) |
| [07-migracion-2.0-a-3.0.md](07-migracion-2.0-a-3.0.md) | Matriz preservar/extender/nuevo + fases F0-F5 + rollback | Antes de tocar código del 2.0 |
| [08-gobernanza-seguridad-y-operaciones.md](08-gobernanza-seguridad-y-operaciones.md) | SOUL/COMPANY + auth + tool-gating + PI defense + multi-tenancy + DR + compliance | Para cualquier decisión que afecte seguridad o compliance |
| [ANEXO-A-mapa-dependencias.md](ANEXO-A-mapa-dependencias.md) | 4 diagramas Mermaid (componentes, skills/tools, modos→playbooks, persistencia) | Para visualizar relaciones |
| [ANEXO-B-decision-log-por-tema.md](ANEXO-B-decision-log-por-tema.md) | Las 114 decisiones del plan maestro reorganizadas por tema con status | Para auditar trazabilidad de cualquier decisión |

**Archivo histórico**: `_archive/plan-maestro-iter-1-12.md` (el plan cronológico de 1991 líneas, preservado por trazabilidad — constitución principio 5).
**Archivo deprecado**: `v3-enterprise-toolkit-extraction.md` (clasificación previa de 1800 líneas, conservado para auditabilidad).

---

## Cómo navegar este set

| Tu rol o pregunta | Lee en este orden |
|---|---|
| Soy nuevo en el proyecto | README → GLOSARIO → 01 → 02 → 07 |
| Voy a implementar una tool nueva | 06 → 04 → 01 (jerarquía) → 08 (governance) |
| Voy a diseñar un Modo nuevo | 02 → 04 (skills disponibles) → 03 (playbooks compatibles) |
| Voy a diseñar un playbook | 03 → 01 (orquestador) → 04 (skills) |
| Voy a modificar gobernanza/seguridad | 08 → 05 (autoaprendizaje vs guardrails) → 01 |
| Voy a auditar trazabilidad de una decisión | ANEXO-B → doc temático que la implementa |
| Necesito el "estado final" del sistema | 01 |
| Necesito el "camino desde 2.0" | 07 |
| Hay contradicción entre docs | 00 manda; luego corregir doc temático |

---

## Alineación con la constitución del proyecto

El set se alinea con `.specify/memory/constitution.md` v1.2.0:

| Principio constitución | Cómo se aplica en el set |
|---|---|
| 1. Pensar antes de codificar | Cada doc cita supuestos y referencias antes de proponer cambios. |
| 2. Simplicidad obligatoria (KISS, YAGNI, AHA) | El set se organiza por canon + docs temáticos. Cero abstracciones especulativas. |
| 3. Modularidad primero (SRP, SoC) | Cada doc tiene un único concern; overlaps mitigados (ver tabla en cada doc). |
| 4. Manejo de errores estricto | Sin try/except defensivos en el código que los docs proponen. Errores propagan con contexto. |
| 5. Cambios quirúrgicos | Los archivos originales se ARCHIVAN, no se borran. ANEXO-B preserva las 114 decisiones por trazabilidad. |
| 6. Entrega verificable | Cada doc temático cierra con criterios verificables (replicado en 07 fases F0-F5). |
| DRY | `00-canon-operativo-corregido.md` manda sobre decisiones; `06-catalogo-tools-y-extraccion.md` es el SSOT operacional de tools/MCPs. |
| WET | Se tolera duplicación temporal en F1 entre playbook YAML y matrix YAML. |
| LoD | Cada agente solo conoce su rol, sus tools y el moderador. |
| Bajo acoplamiento + DIP | Connectors implementan port `IngestionConnector`. ChannelAdapters implementan `ChannelAdapter`. |
| OCP | Nuevos playbooks por YAML sin tocar `PlaybookRunner`. Nuevos connectors implementan port sin tocar el `IngestionOrchestrator`. |
| ISP | Tool discovery progresivo: agentes ven solo el subset de tools que necesitan. |
| CQS | `ToolRegistry` solo LEE de `tool_health`; `HealthMonitor` solo escribe (decisión #81 del plan maestro). |
| POLA | `ComplexityClassifier` log su decisión por sesión. YAML declarativo. |
| Convención sobre configuración | Playbooks con defaults sensatos; config solo cuando se sobreescribe. |

---

## Estado por fase (MVP + roadmap)

Por C1, las fases F3-F5 se splittean en MVP y roadmap completo. Detalle granular en [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md) + [07-migracion-2.0-a-3.0.md](07-migracion-2.0-a-3.0.md).

**Camino MVP (12-16 semanas, 1-2 ingenieros)**:

| Fase MVP | Alcance | Estado |
|---|---|---|
| **F0** | Auditoría licencias + setup + supuestos | 🟡 Pendiente |
| **F1** | Foundation: XiaomimimoClient + ToolRegistry + persistencia base | 🔴 No iniciado |
| **F2** | TurboVecIndex + ingestion básico (Google Workspace MCP Drive) | 🔴 No iniciado |
| **F3a** | 4 tools Tier 1 nuevas + Google Workspace MCP Tier 2 | 🔴 No iniciado |
| **F4a** | 3 modos MVP + 3 playbooks MVP + Frontend MVP 5 superficies | 🔴 No iniciado |
| **F5a** | Dreaming básico + PI defense regex + tool-gating | 🔴 No iniciado |

**Roadmap post-MVP (+16 semanas adicionales, 2-3 ingenieros)**:

| Fase roadmap | Alcance | Estado |
|---|---|---|
| **F3b** | Resto de tools (~59 capacidades adicionales) | ⏸ Bloqueado hasta MVP |
| **F4b** | Playbooks avanzados (goal-pursuit, app-development, artifact-development, company-optimization, decision-debate, market-research, compliance-audit) | ⏸ Bloqueado hasta MVP |
| **F4c** | Modos restantes (CFO, Legal, Marketing, B2B, Operaciones PYME) | ⏸ Bloqueado hasta MVP |
| **F5b** | 5 loops de autoaprendizaje + agent_modifications SQL | ⏸ Bloqueado hasta MVP |
| **F5c** | Frontend completo (artefactos + optimización + admin) | ⏸ Bloqueado hasta MVP |
| **F5d** | DR + SSO + compliance avanzado + anomaly detector | ⏸ Bloqueado hasta MVP |

---

## Convención de actualización del set

1. **Cambio menor** (clarificación, typo, ejemplo): editar el doc temático directamente.
2. **Cambio mayor** (nueva decisión arquitectónica o conceptual): añadir entrada en el doc temático correspondiente **y** registrar en `ANEXO-B-decision-log-por-tema.md` con status `vigente`. Si reformula una decisión previa, marcar la previa como `reformulada` y enlazar.
3. **Nueva categoría completa**: discutir con el usuario antes; puede requerir un doc nuevo o sección nueva.
4. **El GLOSARIO manda**: si un término aparece distinto en dos docs, el del GLOSARIO es la verdad y los docs deben ajustarse.
5. **Especificaciones formales** (`specs/`): cada doc temático puede dar origen a 1-2 specs. Ver tabla "Origen de specs/" en el plan de refactorización.

---

## Origen de `specs/` posteriores

Cada doc temático genera 1-2 especificaciones formales bajo `specs/<NNN>-<slug>/`:

| Doc | specs/ candidatas |
|---|---|
| 00 | `specs/009-canon-operativo-corregido/` |
| 01 | `specs/010-jerarquia-agent-mode-skill/` |
| 02 | `specs/011-mode-router-catalogo-geo/` |
| 03 | `specs/012-playbook-app-development-spec-kit/` + `specs/013-goal-pursuit/` + `specs/014-artifact-development/` |
| 04 | `specs/015-skill-marketplace-claude-local/` |
| 05 | `specs/016-audit-trail-y-rollback/` + `specs/017-admin-maintenance-dreaming/` |
| 06 | `specs/018-tool-mcp-catalog-ssot/` |
| 07 | `specs/019-fase-F0-auditoria-baseline/` |
| 08 | `specs/020-pi-defense-quarantine/` |

---

## Cobertura de las 5 brechas estructurales

| Brecha | Dónde se cierra |
|---|---|
| 1. Inventario disperso "qué se mantiene del 2.0" | Doc 07 — matriz archivo-a-archivo |
| 2. Skills marketplace sin modelar | Doc 04 — sección "Marketplaces externos integrados" |
| 3. Modos de operación user-facing | Doc 02 entero |
| 4. Templates de apps tipo Spec-Kit | Doc 03 — playbook `app-development` |
| 5. Autoaprendizaje sin loop continuo + audit | Doc 05 entero + reescritura de decisión #44 |
