# 03 — Playbooks y Orquestación

> Documento que define el catálogo de playbooks, los componentes de orquestación complexity-aware y el playbook `app-development` que cierra la **brecha 4** del set (Spec-Kit como pipeline interno reutilizable).

> **Decisión D3 de esta sesión**: el flujo `constitution → specify → plan → tasks → analyze → implement` de [github/spec-kit](https://github.com/github/spec-kit) se adopta como **playbook interno `app-development`** del Vigilador 3.0. Genera apps DENTRO del PC del usuario para uso interno empresa (dashboards, automatizaciones, herramientas internas). NO se exporta a cliente final del cliente.

> **Corrección vigente**: además de `app-development`, el 3.0 incluye `company-optimization` para ISO/NTC/normas tecnicas y `artifact-development` para dashboards, pipelines y visualizacion de metricas empresariales. Ver [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md).

---

## Concepto

Un **Playbook** es un flujo declarativo en YAML que:
- Define qué Agents instanciar.
- Define el orden o paralelismo entre ellos.
- Declara qué Skills puede invocar cada Agent.
- Declara qué Modos son compatibles (`mode_compatible: [CFO, CEO]`).
- Opcionalmente declara `output_schema` para outputs structured.

El **PlaybookRunner** (`enterprise/orchestration/playbook_runner.py`) lo carga al recibir una sesión, valida compatibilidad con el Mode activo, instancia agents y orquesta su ejecución.

---

## Catálogo de playbooks

| ID | Origen | Mode default | Cuándo se usa |
|---|---|---|---|
| `technology-watch` | Preservado del 2.0 (`BranchCoordinator` + 6 agentes de rama) | `Vigilancia Tech` | Vigilancia tecnológica clásica — 6 ramas paralelas |
| `decision-debate` | Nuevo (CrewAI) | `CEO`, `CFO` | Decisiones estratégicas con N agentes debatiendo + moderador (MoA) |
| `market-research` | Nuevo (CrewAI) | `Marketing`, `CEO` | Investigación de mercado con sub-agentes especializados |
| `compliance-audit` | Nuevo (CrewAI) | `CFO`, `Consultor Legal` | Auditoría de cumplimiento (SOX, SARLAFT, regulación) |
| `general` | Nuevo | `default`, todos | 1 agente generalista con tool discovery progresivo |
| `deep-research` | Preservado del 2.0 (Clarify → Plan → Approve → Execute → Fuse → Report) | todos los modos | Investigación profunda multi-rama estilo `technology-watch` pero genérica (decisión #21) |
| `goal-pursuit` | Nuevo esta fase | todos los modos (con `intensity: AUTONOMOUS` recomendado) | Perseguir objetivos durante horas/días con checkpoints |
| **`company-optimization`** | **NUEVO por C0** | `CEO`, `Operaciones PYME`, `CFO`, `Consultor Legal` | Diagnosticar y mejorar procesos contra ISO, NTC, SST, calidad, seguridad, gestion documental u otras normas aplicables |
| **`artifact-development`** | **NUEVO por C0** | `CEO`, `CFO`, `Operaciones PYME`, `Marketing` | Crear dashboards, pipelines, notebooks/scripts y visualizaciones de metricas empresariales |
| **`app-development`** | **NUEVO esta sesión** (D3) | `Operaciones PYME`, `CEO`, `default` | Generar apps internas siguiendo flujo Spec-Kit |

Detalle de cada playbook a continuación.

---

## Schema YAML extendido

Ubicación: `config/playbooks/<id>.yaml`.

```yaml
id: decision-debate
display_name: "Debate de decisión"
description: "N agentes debaten una decisión con moderador. Output: resumen + recomendación + tradeoffs."
version: "1.1.0"

mode_compatible:
  - CEO
  - CFO
  - Consultor Legal
  - Operaciones PYME

complexity_routing:
  # ComplexityClassifier decide cuántos agentes según complejidad detectada
  SIMPLE:
    agents_count: 1
    skip: true  # SIMPLE va a playbook 'general' en lugar de debate
  MODERADA:
    agents_count: 3
  COMPLEJA:
    agents_count: 5

agents:
  - id: pro_advocate
    role: "Defensor de la opción A"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "analysis:*"
      - "research:web_search"
    instructions: |
      Defiende la opción A con argumentos basados en evidencia.
      Busca riesgos en B y oportunidades en A.

  - id: con_advocate
    role: "Defensor de la opción B"
    base_llm: minimax-m-2.5  # diversidad cognitiva con M-2.5 (decisión #7)
    skills_allowed:
      - "analysis:*"
      - "research:web_search"
    instructions: |
      Defiende la opción B con argumentos basados en evidencia.

  - id: moderator
    role: "Moderador imparcial"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "analysis:*"
      - "intelligence:cove_verify"
    instructions: |
      Modera el debate. Pide aclaraciones. Sintetiza decisión final con tradeoffs.

flow:
  type: rounds  # rounds | sequential | dag | hierarchical
  rounds_count: 3
  final_synthesis_by: moderator

output_schema:
  type: object
  properties:
    decision: { type: string }
    rationale: { type: string }
    tradeoffs: { type: array, items: { type: string } }
    confidence: { type: number, minimum: 0, maximum: 1 }

require_approval_at_end: false
checkpoint_every_n_steps: null

guardrails:
  max_total_llm_calls: 50
  max_session_duration_seconds: 600
  cove_required: true  # decisión #97
```

### Validación

`PlaybookRunner.validate()` al cargar:
- `mode_compatible` referencia Modos existentes en `config/modes/`.
- `skills_allowed` referencia Skills existentes (categoría o id).
- `base_llm` en `[minimax-m-2.7, minimax-m-2.5]`.
- `output_schema` es JSON Schema válido.

---

## ComplexityClassifier

Preservado conceptualmente del plan maestro §3.1, ahora ubicado en `enterprise/orchestration/complexity_classifier.py`.

**Función**: 1 llamada corta (~50 tokens prompt + ~10 respuesta) a MiniMax M-2.7 que clasifica la tarea entrante en `SIMPLE | MODERADA | COMPLEJA`.

**Inputs**: mensaje del usuario + Mode activo + COMPANY context resumido (1-2 líneas).

**Output**: `ComplexityLevel` + razón (1 línea, loggeada para POLA).

**Uso**: el `PlaybookRunner` consulta el `complexity_routing` del playbook activo para saber cuántos agentes desplegar.

**Por qué no usar siempre el playbook completo**: ahorro de tokens. Una pregunta SIMPLE no necesita 5 agentes debatiendo; un 1 agente generalista con tool discovery progresivo basta.

**Ejemplo de log**:

```
[ComplexityClassifier] session=01H... mode=CFO message="¿Cuál es la fecha del próximo cierre?" → SIMPLE (razón: pregunta factual única, sin tradeoffs)
[ComplexityClassifier] session=01H... mode=CFO message="¿Deberíamos refinanciar la deuda con BBVA o Bancolombia?" → COMPLEJA (razón: decisión estratégica con tradeoffs financieros, riesgo y plazo)
```

---

## SubagentRegistry

Componente nuevo (`enterprise/orchestration/subagent_registry.py`) que persiste el árbol de sub-agentes. Habilita la **recursión**: cualquier agente puede spawnear sub-agentes (decisión #8).

**Tabla**:

```sql
CREATE TABLE subagents (
    id              UUID PRIMARY KEY DEFAULT uuidv7(),
    tenant_id       UUID NOT NULL,
    parent_session_id UUID,
    parent_agent_id TEXT,
    depth           INT NOT NULL DEFAULT 0,
    role            TEXT NOT NULL,
    spawn_reason    TEXT,
    status          TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE | PAUSED | COMPLETED | FAILED | WAITING_APPROVAL
    pause_reason    TEXT,
    resume_token    TEXT,
    last_progress_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
```

**Guardrails** (depth-aware):
- `depth` max configurable por playbook (`guardrails.max_depth`, default 3).
- Cada sub-agente cuenta contra `max_total_llm_calls` global del playbook.
- Si `depth > max`, el spawn falla con error explícito → el agente padre debe simplificar.

**Operaciones**:

```
vigilador-admin subagent list                            # árbol actual
vigilador-admin subagent show <id>                       # detalle + diff trace
vigilador-admin subagent pause <id>                      # cambia status a PAUSED + resume_token
vigilador-admin subagent resume <id>                     # WAITING_APPROVAL → ACTIVE
vigilador-admin subagent cancel <id>                     # ACTIVE → FAILED (kill switch)
```

---

## Multi-agent debate y MoA

### Debate

Playbook `decision-debate` orquesta N agentes (3 o 5 según complejidad) con moderador. Implementado en `enterprise/orchestration/debate_coordinator.py`.

**Patrón**: rounds → cada round los agentes responden conociendo las respuestas previas del round anterior → el moderador sintetiza al final.

**Diversidad cognitiva**: mezclar M-2.7 y M-2.5 (decisión #7 — único caso donde se usan los dos modelos del catálogo MiniMax).

### MoA (Mixture of Agents)

Patrón arXiv:2406.04692. Reescritura sustancial de `tools/mixture_of_agents_tool.py` de Hermes (decisión #48 — el original usa OpenRouter+multi-LLM).

**Implementación 3.0**: 3-4 instancias de MiniMax M-2.7 con **temperaturas distintas** (0.3, 0.7, 1.0, 1.2) generan respuestas en paralelo. 1 instancia agregadora M-2.7 (temp 0.5) las sintetiza.

**Cuándo usar MoA**: dentro de un debate como "voting de proposers"; o como skill standalone `intelligence:moa_synthesize` para outputs de alto valor.

---

## Goal-pursuit

Playbook nuevo (`goal-pursuit.yaml`). Implementado en `enterprise/orchestration/goal_pursuit/` (4 archivos).

**Diferencia clave**: el orquestador clásico (`technology-watch`, `general`, `decision-debate`) es **reactivo** — responde a una pregunta. `goal-pursuit` es **proactivo** — persigue un objetivo durante horas/días.

**Componentes**:

| Archivo | Responsabilidad |
|---|---|
| `decomposer.py` | Descompone goal complejo en sub-goals con dependencias |
| `dependency_resolver.py` | Secuencia y paraleliza pasos según DAG |
| `checkpoint_reporter.py` | Reporta progreso por canal cada N pasos o al detectar bloqueo |
| `approval_gate.py` | Pide aprobación humana en puntos críticos (reusa `approval_queue.py` de governance) |

**Persistencia**: extiende `subagents` con columnas `parent_goal_id`, `status: ACTIVE|PAUSED|COMPLETED|FAILED|WAITING_APPROVAL`, `pause_reason`, `resume_token`, `last_progress_at`. Sobrevive restart del harness.

**Ejemplo**:
- Usuario: `/mode Vendedor B2B` → `consigue 10 leads B2B sector logística Colombia y agéndalos en HubSpot`
- `GoalDecomposer` produce: (1) buscar empresas logística >50 empleados Colombia, (2) extraer contactos decisores, (3) clasificar por score, (4) crear contactos en HubSpot, (5) enviar email de outreach al top 10.
- Tras paso 3: checkpoint con preview de los top 10 → usuario aprueba.
- Tras paso 4: checkpoint mostrando contactos creados → usuario aprueba envío.
- Paso 5: envía emails con writing_style aprendido (decisión #20).
- Reporta resultado final al canal.
- Duración total: 4-8 horas con 2-3 checkpoints.

**Ejecución autónoma extendida**: opera con capability token (decisión #107) de TTL 8 horas; si expira mid-loop, re-solicita aprobación.

---

## Playbook `company-optimization`

Flujo nuevo para transformar informacion empresarial indexada en diagnosticos y planes de mejora. Vive en `config/playbooks/company-optimization.yaml` y usa `enterprise/optimization/`.

**Casos de uso**:
- Preparar una empresa para ISO 9001, ISO 27001, ISO 45001, NTC, BPM, gestion documental u otras normas tecnicas.
- Diagnosticar brechas por proceso usando evidencia indexada en Drive/OneDrive/local.
- Generar plan de accion con responsable, evidencia requerida, riesgo, prioridad y fecha objetivo.
- Crear formatos, procedimientos, checklists y dashboards de seguimiento.

**Regla geo-normativa**: si la empresa tiene `company_geo` Colombia/Santander/Barrancabermeja, el playbook debe buscar fuentes oficiales vigentes municipales, departamentales y nacionales antes de afirmar obligaciones, impuestos, tasas o requisitos.

```yaml
id: company-optimization
display_name: "Optimizacion empresarial"
mode_compatible: [CEO, CFO, Consultor Legal, Operaciones PYME]

agents:
  - id: standard_mapper
    role: "Mapeador de norma tecnica"
    skills_allowed:
      - "optimization:standard-mapping"
      - "research:web_search"
  - id: evidence_auditor
    role: "Auditor de evidencia empresarial"
    skills_allowed:
      - "enterprise-index:search"
      - "documents:markitdown"
  - id: improvement_planner
    role: "Planificador de mejora"
    skills_allowed:
      - "optimization:gap-analysis"
      - "artifacts:dashboard_spec"

output_schema:
  type: object
  properties:
    standard: { type: string }
    gaps: { type: array }
    action_plan: { type: array }
    evidence_required: { type: array }
    dashboard_spec: { type: object }
```

---

## Playbook `artifact-development`

Flujo nuevo para construir artefactos de gestion sin pasar siempre por una app completa. Vive en `config/playbooks/artifact-development.yaml` y usa `enterprise/artifacts/`, extendiendo lo ya existente en `application/artifacts/`.

**Artefactos soportados**:
- Dashboards HTML/Streamlit/React internos.
- Pipelines de datos locales o cloud para KPIs.
- Notebooks reproducibles.
- Reportes programados.
- Graficas para frontend o export a PPT/PDF.

**Diferencia con `app-development`**: `artifact-development` se enfoca en metricas, visualizacion y pipelines; `app-development` se usa cuando el usuario necesita una aplicacion interna completa con UI, persistencia o workflow propio.

```yaml
id: artifact-development
display_name: "Crear artefacto de metricas"
mode_compatible: [CEO, CFO, Operaciones PYME, Marketing]

flow:
  type: sequential
  fases_order: [source_inventory, metric_model, pipeline_plan, build, verify, publish]

agents:
  - id: source_inventory_agent
    role: "Inventaria fuentes de datos"
    skills_allowed: ["enterprise-index:search", "analytics:source_profile"]
  - id: metric_model_agent
    role: "Define KPIs y contratos de datos"
    skills_allowed: ["analytics:kpi_modeling", "documents:template_render"]
  - id: builder_agent
    role: "Construye dashboard/pipeline"
    skills_allowed: ["code:file_system", "code:e2b_sandbox", "analytics:dashboard_generate"]

output_schema:
  type: object
  properties:
    artifact_type: { type: string }
    artifact_path: { type: string }
    data_sources: { type: array }
    refresh_policy: { type: string }
    metrics: { type: array }
```

---

## Playbook `app-development` (Spec-Kit como pipeline interno)

**Decisión D3 de esta sesión**: Vigilador 3.0 adopta el flujo `constitution → specify → plan → tasks → analyze → implement` de [github/spec-kit](https://github.com/github/spec-kit) como un playbook interno reutilizable.

### Alcance

**Sí**: genera apps DENTRO del PC del usuario para uso interno de su empresa. Ejemplos:
- Dashboard de KPIs financieros con datos de Excel + Power BI Desktop.
- Automatización de generación de reportes mensuales con templates Jinja2.
- Herramienta interna para que el equipo de ventas consulte el CRM con queries en lenguaje natural.
- Script Python para procesar archivos de un proceso recurrente del usuario.
- Si el objetivo es solo dashboard/pipeline de metricas, usar primero `artifact-development`; si requiere producto interno completo, usar `app-development`.

**No**: NO genera apps standalone para distribuir a clientes finales del cliente (eso sería un scope mucho mayor — build pipeline, packaging, deployment, soporte).

### Estructura del playbook

```yaml
id: app-development
display_name: "Generar aplicación interna"
description: "Pipeline tipo Spec-Kit para generar una app/script/dashboard interno para la empresa del usuario."
version: "1.0.0"

mode_compatible:
  - Operaciones PYME
  - CEO
  - default
  - CFO   # CFO puede usarlo para dashboards financieros

complexity_routing:
  SIMPLE:
    skip: true  # SIMPLE va a 'general'
  MODERADA:
    fases_active: [constitution, specify, plan, tasks, implement]
  COMPLEJA:
    fases_active: [constitution, specify, plan, tasks, analyze, implement, test]

agents:
  - id: constitution_agent
    role: "Encargado de definir principios del proyecto"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "documents:template_render"
      - "code:clarify"
    instructions: |
      Pregunta al usuario por los principios rectores del proyecto:
      - Lenguaje y stack preferidos
      - Estándares de calidad esperados
      - Restricciones (offline, sin cloud, debe correr en Windows, etc.)
      - Forma de uso (CLI, GUI, web local, scheduled job)
      Materializa en `<project>/constitution.md`.

  - id: specify_agent
    role: "Especificador de requisitos"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "documents:template_render"
      - "code:clarify"
    instructions: |
      Genera `<project>/spec.md` con: problema, usuarios, requisitos funcionales,
      no funcionales, casos de uso, criterios de éxito.

  - id: plan_agent
    role: "Arquitecto de plan de implementación"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "documents:template_render"
      - "code:e2b_sandbox"
    instructions: |
      Lee constitution.md + spec.md. Produce `<project>/plan.md` con stack final,
      estructura de archivos, dependencias, pasos clave.

  - id: tasks_agent
    role: "Generador de tareas"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "documents:template_render"
    instructions: |
      Lee plan.md. Genera `<project>/tasks.md` con tareas ordenadas por dependencias.
      Cada tarea: ID, descripción, dependencias, criterio de done.

  - id: analyze_agent
    role: "Verificador cruzado constitution↔spec↔plan↔tasks"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "intelligence:cove_verify"
      - "documents:template_render"
    instructions: |
      Verifica coherencia entre los 4 documentos. Genera `<project>/analyze-report.md`.
      Bloquea si hay inconsistencias críticas.

  - id: implement_agent
    role: "Implementador iterativo"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "code:e2b_sandbox"
      - "code:file_system"
      - "code:kanban"
      - "documents:template_render"
    instructions: |
      Lee tasks.md. Itera tarea por tarea generando código en `<project>/src/`.
      Cada tarea cierra cuando pasa su criterio de done.

  - id: test_agent
    role: "Validador de tests + checklist final"
    base_llm: minimax-m-2.7
    skills_allowed:
      - "code:e2b_sandbox"
      - "code:file_system"
    instructions: |
      Ejecuta tests del proyecto. Genera `<project>/checklist.md` con resultados.
      Bloquea si alguno falla; sugiere fix.

flow:
  type: sequential
  fases_order: [constitution, specify, plan, tasks, analyze, implement, test]
  approval_at_end_of:
    - constitution    # usuario aprueba principios antes de pasar a specify
    - analyze         # usuario revisa inconsistencias antes de implementar

output_schema:
  type: object
  properties:
    project_path: { type: string }
    constitution_path: { type: string }
    spec_path: { type: string }
    plan_path: { type: string }
    tasks_path: { type: string }
    implementation_summary: { type: string }
    tests_passed: { type: boolean }

guardrails:
  max_total_llm_calls: 500   # generosos — proyectos pueden ser grandes
  max_session_duration_seconds: 86400  # hasta 24h (es goal-pursuit-like)
  cove_required: true        # crítico para evitar inconsistencias entre fases
  sandbox_required: true     # toda ejecución de código en e2b_sandbox (decisión #36 — cero riesgo al host)
```

### Templates Jinja2 asociados

`config/templates/app-development/`:

```
constitution.template.md
spec.template.md
plan.template.md
tasks.template.md
analyze-report.template.md
checklist.template.md
src/                                # scaffold base por tipo de app
├── python_cli/
├── python_streamlit_dashboard/
├── python_fastapi_internal/
└── jupyter_notebook/
```

El `constitution_agent` elige el scaffold según las decisiones del usuario en `constitution.md`.

### Dónde se ejecuta el código generado

**Cero ejecución directa en el host**. Toda generación + ejecución de tests pasa por `code:e2b_sandbox` (skill que wrappea el MCP `sandbox` existente del 2.0). Si el usuario aprueba al final, el código se copia al directorio destino del PC del usuario (path absoluto declarado en `constitution.md`).

### Audit trail

Cada fase del playbook deja entrada en `agent_modifications` (doc 05) con `triggered_by: app_development_phase` + `target_file: <project>/{fase}.md`. Rollback de cualquier fase posible.

### Ejemplo de ejecución completa

```
Usuario (modo Operaciones PYME): "Necesito una herramienta interna para que el equipo
de ventas vea el ranking de leads en tiempo real con datos del HubSpot"

→ ComplexityClassifier: COMPLEJA
→ PlaybookRunner carga app-development.yaml
→ Fase 1 (constitution_agent): pregunta stack (Python+Streamlit recomendado),
  ubicación (D:/herramientas/), restricciones (offline OK, debe refrescar cada 15min)
  → genera D:/herramientas/leads_ranking/constitution.md
  → APPROVAL_GATE: usuario aprueba
→ Fase 2 (specify_agent): genera spec.md
→ Fase 3 (plan_agent): genera plan.md (Streamlit + httpx + HubSpot API + cache 15min)
→ Fase 4 (tasks_agent): genera tasks.md (12 tareas ordenadas)
→ Fase 5 (analyze_agent): verifica coherencia → genera analyze-report.md (sin issues)
  → APPROVAL_GATE: usuario aprueba
→ Fase 6 (implement_agent): genera src/app.py, src/hubspot_client.py, requirements.txt, README.md
  itera en e2b_sandbox tarea por tarea
→ Fase 7 (test_agent): ejecuta tests, genera checklist.md
→ Output final: app lista en D:/herramientas/leads_ranking/, instrucciones de uso en README.md
```

Tiempo estimado: 30 min - 2 horas según complejidad. Costo aprox: 0.50-3 USD en llamadas LLM (depende del tamaño del proyecto).

---

## Self-correction loop (Reflexion)

Implementado en `enterprise/intelligence/self_correction.py` (#96). Patrón `generate → critique → revise → return`. **Solo aplica a outputs de alto valor** (reportes, correos, código, decisiones de debate) — NO en chitchat.

Trigger configurable per-playbook:

```yaml
self_correction:
  enabled: true
  applies_to:
    - "agent.final_output"
    - "skill:report_generation.output"
  max_iterations: 2  # critique → revise; máximo 2 ciclos
```

---

## Chain-of-Verification (CoVe)

Implementado en `enterprise/intelligence/cove_verifier.py` (#97). Antes de afirmar un hecho factual, agente genera 3-5 preguntas de verificación, las responde con sus tools, y solo afirma si las respuestas son consistentes.

**Trigger automático**: regex detecta patrones de afirmación factual (cifras financieras, citas legales, datos de clientes, afirmaciones técnicas específicas) en la respuesta del LLM.

**Trigger explícito**: `playbook.guardrails.cove_required: true` fuerza CoVe en todas las respuestas del playbook (usado en `decision-debate` y `app-development`).

---

## Confidence scoring + abstention

Implementado en `enterprise/intelligence/confidence_scorer.py` (#98). Cada respuesta lleva score 0.0-1.0 calculado de:

- Consistencia entre múltiples llamadas con misma query (sample N=3).
- Cantidad y calidad de citations recuperadas.
- Match con frozen snapshot de COMPANY.md.

Si confianza < 0.5 → agente se abstiene ("no tengo información suficiente para responder con certeza") o pide aclaración. Métrica `vigilador_response_confidence{playbook,domain}`.

---

## Few-shot retrieval

Implementado en `enterprise/intelligence/fewshot_retriever.py` (#99). Antes de generar reporte/correo/análisis, busca en TurboVec 3-5 ejemplos previos similares aprobados por el usuario y los inyecta como few-shot en el prompt.

**Integración natural con Writing Style Learning** (decisión #20): los ejemplos aprobados ya son la base del style profile.

---

## Triggers proactivos (event-driven)

Implementado en `enterprise/triggers/event_listener.py` (#102). Distinto de Dreaming (cron periódico).

| Trigger | Source | Disparo | Modo + Playbook ejecutado |
|---|---|---|---|
| Email triggers | Webhook Gmail / IMAP IDLE | Nuevo email | Modo elegido por filtro + playbook `general` |
| Slack/Teams triggers | Webhook menciones | Cliente importante menciona | Modo + playbook por filtro |
| Metric anomaly | Prometheus alert | Caída >X% en métrica de negocio | Modo + `goal-pursuit` para investigar causa |
| Calendar/deadline | COMPANY/processes.md con fecha próxima | Cron diario detecta | Recordatorio inteligente con contexto preparado |
| CRM triggers | HubSpot webhook | Nuevo deal | Modo `Vendedor B2B` + playbook `deal-research` |

Tabla `event_subscriptions(tenant_id, source, filter, mode, playbook, enabled)`.

---

## Output formatter (structured + free-form)

Implementado en `enterprise/tooling/output_formatter.py` (#105). Cada respuesta tiene dos versiones:

- **Free-form**: lo que se muestra al usuario en el canal (Telegram, WhatsApp, Web).
- **Structured JSON**: consumible por programas/webhooks/integraciones, según `playbook.output_schema`.

Habilita pipelines como: "respuesta de análisis de mercado → POST a webhook propio del usuario que dispara otro proceso interno".

---

## Tool result caching adaptativo

Implementado en `enterprise/tooling/adaptive_cache.py` (#103), extensión de `MCPSmartCache` del 2.0.

**TTL por tipo de query**:
- Búsqueda noticias: 1h
- Definición técnica: 30d
- Datos de cliente: 5min
- Dashboard analytics: 15min

**Invalidación por evento**: `ingestion_sync` detecta cambio en doc X → invalida entradas que lo referencian.

Métrica `vigilador_cache_hit_ratio{tool,domain}`.

---

## Integración con el resto del set

| Doc | Cómo se integra |
|---|---|
| [01 Arquitectura](01-vision-y-arquitectura.md) | Define el `PlaybookRunner` como componente core; este doc detalla su funcionamiento. |
| [02 Modos](02-modos-y-personalidades.md) | `mode_compatible` declara qué Modos pueden invocar cada playbook. Detalle del filtrado en doc 02. |
| [04 Skills](04-skills-y-capacidades.md) | `skills_allowed` referencia el catálogo de Skills. |
| [05 Autoaprendizaje](05-autoaprendizaje-y-autonomia.md) | `app-development` deja entradas en `agent_modifications`. Loop 3 (Prompt self-improvement) puede modificar playbooks. |
| [06 Catálogo tools](06-catalogo-tools-y-extraccion.md) | Las tools que invocan los skills permitidos están catalogadas ahí. |
| [08 Gobernanza](08-gobernanza-seguridad-y-operaciones.md) | `approval_gate`, `capability_tokens`, `anomaly_detector` viven ahí; este doc los CONSUME. |

---

## Decisiones implementadas por este doc

Este doc consolida (ver `ANEXO-B-decision-log-por-tema.md`):

- **D3** esta sesión: Spec-Kit como playbook `app-development`.
- **C0** canon operativo: `company-optimization` y `artifact-development`.
- **#6** CrewAI + BranchCoordinator coexisten.
- **#8** ComplexityClassifier sin límite de llamadas, recursión.
- **#9** Tool discovery progresivo.
- **#10** Debate multi-agente con moderador.
- **#21** deep-research como playbook explícito.
- **#48** MoA reescritura para MiniMax.
- **#96-99** Intelligence loops (self_correction, cove, confidence, fewshot).
- **#100-101** Goal-pursuit + long-running tasks pause/resume.
- **#102** Proactive triggers.
- **#103** Tool result caching adaptativo.
- **#104** Citations obligatorias verificables.
- **#105** Outputs duales structured + free-form.

---

## Criterios de verificación

Tras implementar este doc:

1. **Test ComplexityClassifier**: 10 mensajes de ejemplo (3 SIMPLE, 4 MODERADA, 3 COMPLEJA) producen clasificación correcta ≥80%.
2. **Test debate**: `decision-debate.yaml` con MODERADA → 3 agentes ejecutan 3 rounds → output con `decision`, `rationale`, `tradeoffs`, `confidence`.
3. **Test goal-pursuit**: lanzar tarea de 4 pasos con 1 checkpoint → ejecuta, espera approval, continua, completa.
4. **Test app-development**: pedir app sencilla ("script Python que cuente líneas de un .csv y genere histograma matplotlib") → fases ejecutan en orden → output final con código funcional + tests pasando.
5. **Test company-optimization**: con `company_geo` Colombia/Santander/Barrancabermeja, diagnosticar ISO/NTC debe producir brechas, fuentes citadas y plan de accion.
6. **Test artifact-development**: con un CSV o fuente indexada, genera dashboard/pipeline verificable y registra `artifact_path`.
7. **Test recursión**: agente con `max_depth=3` spawna sub-agente que spawna sub-sub-agente; intento de spawnear nivel 4 falla con error explícito.
8. **Test CoVe**: respuesta con cifra financiera específica dispara CoVe automáticamente; respuesta de chitchat no.
9. **Test confidence abstention**: query sobre tema sin datos suficientes en COMPANY → respuesta con `vigilador_response_confidence < 0.5` y mensaje de abstención.
10. **Test trigger proactivo**: webhook simulado de Gmail dispara playbook → entrada en log.
