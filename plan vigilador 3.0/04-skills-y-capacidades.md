# 04 — Skills y Capacidades

> Documento que cierra la **brecha 2** del set: integración formal de los 2 marketplaces externos como bibliotecas de skills + modelo conceptual Skill vs Capability vs Tool.

> **Decisión D1 de esta sesión**: jerarquía **Agent compone Skills**. Skills son recetas atómicas reutilizables (compatibles con los marketplaces externos). Agents son personalidades empresariales (Modos) que tienen un catálogo de Skills permitidas. Un mismo Skill puede usarse desde N Modos/Agents distintos.

> **Corrección vigente**: el SkillLoader tambien puede importar `.claude/skills/*/SKILL.md` y comandos locales como `external:claude-local`, y debe usar descubrimiento semantico con carga progresiva para no enviar todo el catalogo al contexto. Ver [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md).

---

## Concepto: Skill vs Capability vs Tool

Causa común de confusión. Definiciones autoritativas (ver también `GLOSARIO.md`):

| Concepto | Granularidad | Vive en | Quién lo invoca | Ejemplo |
|---|---|---|---|---|
| **Skill** | Receta atómica reutilizable (declarativa + opcional Python) | `config/skills/` (curated y learned) o marketplace externo | Un Agent | `reconciliation` (skill del plugin `finance:`) |
| **Capability** | Verbo concreto con schema JSON | Expuesto por una Tool | Un Skill (o un Agent directamente) | `excel_local.refresh_pivot`, `tavily_search` |
| **Tool** | Módulo Python que implementa N capabilities | `enterprise/tooling/builtin/<dominio>/<tool>.py` | El runtime (vía `ToolRegistry`) | `tools/builtin/finance/excel_local.py` |
| **CommandSkill** | Comando parametrizable modelado como skill | `.claude/commands` o adapters locales | Un Agent con approval/sandbox si aplica | `speckit-implement`, `git-validate` |

**Ejemplo concreto**:
- Skill `monthly-financial-close` (en `skills/curated/finance/monthly-financial-close.md`).
- El Skill invoca capabilities: `excel_local.refresh_all_pivots` + `quickbooks.fetch_journal_entries` + `template_render(month_close_template)` + `docx_generate`.
- Esas capabilities son ofrecidas por las tools `excel_local.py`, `quickbooks.py`, `template_render.py`, `docx_generate.py`.

**Regla de contexto minimo**:
- El agente primero ve una lista corta de skills candidatas (`id`, descripcion, tags, permisos, estado).
- Solo si una skill queda en top-k se carga su ficha resumida.
- Solo si se va a ejecutar se carga el `SKILL.md` completo, procedimiento largo o codigo opcional.

---

## Schema unificado `SKILL.md`

Diseñado para ser compatible con los formatos de los 2 marketplaces externos (`K-Dense-AI/scientific-agent-skills` y `msitarzewski/agency-agents`) + extensiones específicas del Vigilador.

Ubicación: `config/skills/{curated|learned}/<categoria>/<id>.md` o cargado en runtime desde marketplace externo.

```markdown
---
id: monthly-financial-close
display_name: "Cierre Financiero Mensual"
description: "Ejecuta el cierre contable mensual: reconciliación bancaria, ajustes, generación de reporte ejecutivo."
version: "1.2.0"
license: "MIT"
author: "vigilador-team"
source: "curated"  # curated | learned | external:k-dense | external:agency-agents | external:claude-local
category: "finance"
tags: ["close", "reconciliation", "monthly"]

mode_compatible:
  - CFO
  - CEO

triggers:
  intent_keywords:
    - "cierre del mes"
    - "monthly close"
    - "cierre contable"
  cron: "0 9 25 * *"   # día 25 de cada mes 9 AM (opcional, para auto-ejecutar)

required_capabilities:
  - excel_local.refresh_all_pivots
  - quickbooks.fetch_journal_entries
  - quickbooks.fetch_trial_balance
  - documents.template_render
  - documents.docx_generate
  - communication.send_email

required_company_files:
  - organization.md   # leer plan de cuentas + responsables
  - processes.md      # leer protocolo de cierre específico de la empresa

inputs:
  - name: "month"
    type: "string"   # "YYYY-MM"
    required: true
  - name: "send_to"
    type: "array<email>"
    required: false
    default_from: "organization.md > finance_team"

outputs:
  - name: "report_path"
    type: "path"
    description: "DOCX con resumen ejecutivo"
  - name: "exceptions"
    type: "array<object>"
    description: "Items que requieren atención manual"
  - name: "tools_used"
    type: "array<string>"

audit:
  level: "high"   # bajo | medio | alto — define cuánto detalle se loggea
  require_cove: true   # decisión #97
---

## Procedimiento

1. **Refrescar Excel pivots** del archivo `D:/finanzas/cierre_mensual.xlsx` (path en `organization.md`).
2. **Fetch journal entries de QuickBooks** para el rango `[month-01, month-último_día]`.
3. **Fetch trial balance** de QuickBooks al último día del mes.
4. **Reconciliar** cuentas bancarias vs. transacciones QuickBooks (skill `bank-reconciliation` invocada como sub-skill).
5. **Detectar excepciones**: diferencias > $100, transacciones sin clasificar, asientos manuales pendientes.
6. **Generar reporte** con template `config/templates/informes/cierre_mensual.docx.jinja2`.
7. **Enviar por email** a la lista del usuario (o `organization.md > finance_team` por default).

## Código opcional (si la receta requiere lógica no expresable en YAML)

\`\`\`python
async def execute(ctx, inputs):
    month = inputs["month"]
    company = ctx.company_loader.load("organization.md")
    xlsx_path = company.systems.finance.excel_path
    
    await ctx.cap("excel_local.refresh_all_pivots", {"file_path": xlsx_path})
    entries = await ctx.cap("quickbooks.fetch_journal_entries", {"from": f"{month}-01", "to": f"{month}-31"})
    tb = await ctx.cap("quickbooks.fetch_trial_balance", {"as_of": f"{month}-last"})
    
    recon_result = await ctx.invoke_skill("bank-reconciliation", {"month": month, "tb": tb})
    
    report_path = await ctx.cap("documents.template_render", {
        "template": "informes/cierre_mensual.docx.jinja2",
        "context": {"month": month, "entries": entries, "tb": tb, "reconciliation": recon_result},
    })
    
    return {
        "report_path": report_path,
        "exceptions": recon_result["exceptions"],
        "tools_used": ["excel_local", "quickbooks", "template_render", "docx_generate"],
    }
\`\`\`
```

### Reglas del schema

- **`source`**: declara origen. Tools del runtime solo cargan skills cuya source esté habilitada en `config/settings.yaml > skills.sources_enabled: [curated, learned, external:k-dense]`.
- **`required_capabilities`**: el `SkillLoader` valida al cargar que todas existan en el `ToolRegistry`. Si falta una, la skill se marca como `unavailable` y no aparece para los Agents.
- **`required_company_files`**: si el archivo no existe o está vacío → el Agent recibe warning al invocar pero la skill puede ejecutar con defaults.
- **`mode_compatible`**: tabla cruzada con `config/modes/*.yaml`. Una skill no compatible con ningún Modo activo no aparece en su listing.
- **`audit.level`**: `bajo` = entry mínima en `audit_events_jsonl_index`; `medio` = + inputs/outputs; `alto` = + diff de archivos tocados + trace de capabilities (recomendado para skills que mueven dinero / modifican config crítico).

## Descubrimiento semantico y carga progresiva

El `SkillRegistry` mantiene un indice semantico de metadata, no de instrucciones completas:

| Nivel | Contenido | Cuándo se carga |
|---|---|---|
| `SkillCard` | `id`, `display_name`, descripcion corta, tags, source, modos compatibles, permisos, estado | Siempre disponible para busqueda y filtrado |
| `SkillSummary` | inputs/outputs, capabilities requeridas, ejemplos cortos, riesgos | Solo para top-k tras busqueda semantica |
| `SkillBody` | `SKILL.md` completo, procedimiento, codigo opcional, comandos | Solo al ejecutar o al preparar plan detallado |

Ranking inicial:
1. Filtrar por Mode, Playbook, permisos, health de capabilities y `company_geo`.
2. Buscar por embeddings sobre descripcion/tags/capabilities/historico.
3. Reordenar por uso exitoso, costo, disponibilidad de credenciales y frescura.
4. Cargar `SkillSummary` solo de las mejores candidatas.

Esto evita que los marketplaces externos, Claude local y skills aprendidas saturen el contexto.

---

## Marketplaces externos integrados

### 1. K-Dense-AI / scientific-agent-skills

Repo: `https://github.com/K-Dense-AI/scientific-agent-skills`

**Qué ofrece**: ~138 skills organizadas en `<categoria>/<id>/SKILL.md`. Categorías: bioinformática, quiminformática, machine learning, genómica, descubrimiento de fármacos, imagenología médica, análisis de datos, automatización de laboratorios.

**Formato**: `SKILL.md` con metadata YAML frontmatter + cuerpo descriptivo + ejemplos de código. Compatible con el schema unificado del Vigilador con adapter mínimo.

**Adapter**: `enterprise/skills_marketplace/k_dense_adapter.py` (~150 LOC).
- Clona el repo a `~/.vigilador/marketplaces/k-dense-skills/` al boot (o pull si ya existe).
- Itera por las carpetas, normaliza el frontmatter al schema del Vigilador.
- Registra cada skill con `source: external:k-dense`.
- Mapping de categorías al taxonomía del Vigilador (ej: `bioinformatics` → `research:bio`).

**Modos que las usan**: principalmente skills científicas → modo `default` y modos custom de empresas en sector salud/farma/biotech. Cualquier Modo custom puede declarar `skills.individual: ["external:k-dense/<id>"]`.

### 2. msitarzewski / agency-agents

Repo: `https://github.com/msitarzewski/agency-agents`

**Qué ofrece**: ~147 "agentes" organizados en 12 divisiones (Engineering, Design, Marketing, Sales, Operations, etc.). Cada uno con identidad, misión, reglas críticas, flujo de trabajo y métricas.

**Reconciliación conceptual con D1**: el repo llama "agents" a lo que en la jerarquía del Vigilador es más cercano a **Skills compuestos con personalidad embebida** (no llegan a ser un Mode porque no tienen SOUL/COMPANY ni configuración completa). El adapter los carga como **Skills enriquecidos** que aportan: instructions + skills sub-invocadas + métricas de éxito.

**Adapter**: `enterprise/skills_marketplace/agency_agents_adapter.py` (~200 LOC).
- Clona el repo a `~/.vigilador/marketplaces/agency-agents/` al boot.
- Parsea cada "agent" como Skill con:
  - `source: external:agency-agents`.
  - `description` = misión central.
  - `tags` = división + roles específicos.
  - `audit.level: alto` por default (son skills complejas).
- Los "do_rules" / "dont_rules" del agent se inyectan como instructions adicionales cuando un Mode invoca la skill.

**Modos que las usan**:
- Skills de `Strategy` y `Operations` → `CEO`.
- Skills de `Marketing` → `Marketing`.
- Skills de `Sales` → `Vendedor B2B`.
- Skills de `Engineering` y `Design` → modos custom de empresas tech.
- Skills de `Finance` (no incluidas en este repo, las cubrimos con el plugin `finance:` interno) → `CFO`.

### 3. Claude local — `.claude/skills` y comandos

Fuente: `.claude/skills/*/SKILL.md` y comandos equivalentes del entorno local.

**Qué aporta en este repo**: skills Spec-Kit ya instaladas (`speckit-constitution`, `speckit-specify`, `speckit-plan`, `speckit-tasks`, `speckit-analyze`, `speckit-implement`, `speckit-checklist`, `speckit-clarify`, `speckit-git-*`). Estas skills alimentan directamente el playbook `app-development`.

**Adapter**: `enterprise/skills_marketplace/claude_local_adapter.py` (~150 LOC).
- Escanea `.claude/skills/*/SKILL.md` fuera de worktrees generados.
- Calcula hash de contenido, origen y ruta.
- Normaliza metadata al schema del Vigilador con `source: external:claude-local`.
- Modela comandos como `CommandSkill` con parametros, permisos y precondiciones.
- Marca como `requires_sandbox: true` cualquier comando que escriba archivos, ejecute shell o toque git.

**Reglas de seguridad**:
- No se ejecuta ningun comando destructivo sin approval.
- Git, filesystem y shell siempre pasan por capability tokens o sandbox segun playbook.
- Las skills importadas quedan versionadas por hash; si cambian, Dreaming admin las revalida antes de promoverlas.

### Política de actualización de marketplaces

- **Pull semanal** durante Dreaming (Fase 4 `config_refresher`): trae cambios upstream.
- **Quarantine**: skills externas con cambios significativos quedan en `external:<source>/_pending/` hasta que el `skill_curator` (Dreaming Fase 2) las revalida con tests sintéticos.
- **Override local**: el operador puede sobrescribir una skill externa colocando un archivo con mismo `id` en `config/skills/curated/<categoria>/`. El loader prioriza curated > learned > external.
- **Atribución**: cada invocación de skill externa loggea origen + license en el audit trail (compliance).

---

## Plugins de skills internos

Además de los marketplaces externos, el Vigilador 3.0 incluye **plugins internos** mantenidos por el equipo:

| Plugin | Categoría | Origen | Skills incluidas (ejemplos) |
|---|---|---|---|
| `finance:` | Plugin oficial Cowork (ver instalado en `.claude/plugins/`) | Pre-instalado | `reconciliation`, `journal-entry`, `variance-analysis`, `audit-support`, `close-management`, `sox-testing`, `financial-statements` |
| `engineering:` | Plugin oficial Cowork | Pre-instalado | `code-review`, `debug`, `incident-response`, `architecture`, `tech-debt`, `deploy-checklist`, `documentation`, `system-design`, `standup`, `testing-strategy` |
| `design:` | Plugin oficial Cowork | Pre-instalado | `user-research`, `research-synthesis`, `design-system`, `design-handoff`, `ux-copy`, `design-critique`, `accessibility-review` |
| `productivity:` | Plugin oficial Cowork | Pre-instalado | `start`, `update`, `task-management`, `memory-management` |
| `frontend-design:` | Plugin oficial Cowork | Pre-instalado | `frontend-design` |
| `vigilador-core:` | Plugin propio del 3.0 | Built-in | `technology-watch`, `bank-reconciliation`, `lead-research`, `proposal-generation`, `email-cadence`, `process-automation`, `document-generation`, `report-scheduling`, `standard-gap-analysis`, `dashboard-pipeline` |
| `claude-local:` | Skills y comandos locales Claude | `.claude/skills` | `speckit-*`, comandos de desarrollo, validacion y git bajo sandbox/approval |

Los plugins se montan vía namespace en el `SkillLoader`: `finance:reconciliation` se carga desde el plugin Cowork; `vigilador-core:lead-research` desde el propio.

---

## Catálogo inicial de skills curados v3.0

Skills priorizados para incluir en `config/skills/curated/` desde F4:

| Skill ID | Plugin/Source | Categoría | Modo principal | Capabilities clave |
|---|---|---|---|---|
| `reconciliation` | `finance:` | finance | CFO | excel, quickbooks, banking |
| `journal-entry` | `finance:` | finance | CFO | quickbooks |
| `variance-analysis` | `finance:` | finance | CFO | excel, power_bi_file_reader |
| `close-management` | `finance:` | finance | CFO | excel, quickbooks, template_render, docx_generate |
| `sox-testing` | `finance:` | finance | CFO | docs, web_search, template_render |
| `audit-support` | `finance:` | finance | CFO, Consultor Legal | docs, web_search |
| `financial-statements` | `finance:` | finance | CFO | excel, quickbooks, template_render |
| `bank-reconciliation` | `vigilador-core:` | finance | CFO | quickbooks, csv, excel |
| `lead-research` | `vigilador-core:` | sales | Vendedor B2B | hubspot, apollo, tavily |
| `proposal-generation` | `vigilador-core:` | sales | Vendedor B2B | template_render, docx_generate |
| `email-cadence` | `vigilador-core:` | sales | Vendedor B2B | gmail/ms365, writing_style |
| `process-automation` | `vigilador-core:` | operations | Operaciones PYME | code:e2b, file_system |
| `document-generation` | `vigilador-core:` | operations | Operaciones PYME | template_render, docx/pdf/pptx_generate |
| `report-scheduling` | `vigilador-core:` | operations | Operaciones PYME, CFO | dreaming.scheduled_reports |
| `standard-gap-analysis` | `vigilador-core:` | optimization | CEO, CFO, Consultor Legal, Operaciones PYME | enterprise-index, web_search, template_render |
| `dashboard-pipeline` | `vigilador-core:` | artifacts | CEO, CFO, Operaciones PYME, Marketing | analytics, code:e2b, file_system |
| `code-review` | `engineering:` | engineering | modo custom Tech | code:e2b, file_system |
| `incident-response` | `engineering:` | engineering | modo custom Tech | docs, monitoring |
| `user-research` | `design:` | design | Marketing | survey, document_generation |
| `accessibility-review` | `design:` | design | Marketing, modo Tech | web, screenshot |
| `frontend-design` | `frontend-design:` | design | Marketing, modo Tech | code:e2b, file_system |
| `start` / `update` / `task-management` | `productivity:` | productivity | todos | file_system, kanban |

Plus las skills cargadas desde los 2 marketplaces externos (~285 adicionales). El `SkillLoader` deduplica por `id` priorizando curated.

---

## Skills aprendidos por demostración (Skill Learning)

Decisión #15 del plan maestro. El agente aprende a usar sitios/apps por demostración y guarda el procedimiento como skill reutilizable.

**Flujo**:

1. Usuario solicita una tarea que no resuelve ninguna skill existente (ej: "extrae los datos de ventas del portal proveedor X que requiere login y exporta a Excel").
2. Agente detecta gap (no encuentra skill) → activa modo demostración.
3. Usuario realiza la tarea con `computer_use` (vision + AX tree del Vigilador observa).
4. Tras finalizar: agente parametriza inputs/outputs, genera `SKILL.md` con `source: learned`, ubicación `config/skills/learned/<categoria>/<id>.md`.
5. Audit entry con `triggered_by: demonstration` (doc 05).
6. **Primera ejecución autónoma**: approval-gate explícito (única excepción a la full-autonomy de D4 — porque el skill nuevo no ha sido probado).
7. Tras 5 ejecuciones exitosas: promoción a "estable", el approval no se pide más.

**Self-correction**: si una ejecución posterior falla (estructura del sitio cambió, app actualizada), el agente intenta auto-corregir con vision + AX tree antes de pedir intervención humana.

**Mantenimiento en Dreaming**: el `skill_curator` (Fase 2) revalida skills aprendidos ejecutando tests sintéticos periódicamente; los que fallan repetidamente se marcan como `deprecated`.

---

## Cómo añadir un skill nuevo

### Opción A: Skill curado (mantenido por el equipo)

1. Crear `config/skills/curated/<categoria>/<id>.md` con frontmatter completo (ver schema arriba).
2. Si requiere código: añadir bloque ```python después del procedimiento.
3. Validar con `vigilador-admin skill validate <id>`.
4. Registrar con `vigilador-admin skill register <id>`.
5. Verificar que aparece en `vigilador-admin skill list --mode CFO` (o el Modo correspondiente).
6. Commitear al repo (skills curated van versionadas en git).

### Opción B: Skill aprendido por demostración

Ver flujo arriba. Sin intervención del operador del Vigilador — lo hace el agente solo durante la sesión.

### Opción C: Skill compuesto detectado automáticamente

Loop 4 (Tool composition) del Dreaming detecta patrones repetidos y propone una skill macro al usuario. Si acepta, queda registrada con `source: learned`.

### Opción D: Override de skill externa

Si una skill de los marketplaces externos necesita adaptación para el cliente:

1. Crear `config/skills/curated/<categoria>/<id>.md` con el mismo `id` que la externa.
2. El loader prioriza curated > learned > external (la externa queda oculta).
3. La versión curated puede heredar la externa explícitamente:

```yaml
inherits: "external:k-dense/molecular-docking"
overrides:
  required_capabilities:
    - chimerax_local.dock   # versión local en lugar de cloud
```

---

## Skill curator (lifecycle)

Implementado en `enterprise/skills_marketplace/skill_curator.py` (~250 LOC). Sub-tarea del Dreaming (Fase 2).

**Tareas del curator**:

1. **Pull marketplaces externos** (semanal): clona/pull los repos externos; nuevas skills entran a `_pending/`.
2. **Validar skills `_pending/`**: ejecuta tests sintéticos (si la skill declara `tests:` en su frontmatter); promueve a registro activo si pasan.
3. **Revalidar skills `learned/`**: ejecuta tests sintéticos sobre skills aprendidas; marca `deprecated` las que fallan 3 veces consecutivas.
4. **Detectar duplicados**: skills con descripciones similares (embedding) → flag al usuario en Dreaming Report para decidir cuál mantener.
5. **Stats de uso**: registra `vigilador_skill_invocations_total{skill_id,mode}` y `vigilador_skill_success_rate{skill_id}`; skills con success_rate < 0.5 en N invocaciones → flag para revisión.
6. **Promoción de skills compuestas** (Loop 4): si una skill macro detectada por composición se invoca con éxito ≥5 veces → propone usuario formalizarla en curated.

---

## Integración con el resto del set

| Doc | Cómo se integra |
|---|---|
| [01 Arquitectura](01-vision-y-arquitectura.md) | Define la jerarquía Agent → Playbook → Skill → Capability donde este doc detalla la capa Skill. |
| [02 Modos](02-modos-y-personalidades.md) | `mode_compatible` filtra qué Skills están disponibles por Mode. |
| [03 Playbooks](03-playbooks-y-orquestacion.md) | `skills_allowed` declara qué subset de Skills puede invocar cada Agent del playbook. |
| [05 Autoaprendizaje](05-autoaprendizaje-y-autonomia.md) | Loop 1 (Skill learning), Loop 4 (Tool composition) y Skill curator modifican el catálogo de skills. |
| [06 Catálogo tools](06-catalogo-tools-y-extraccion.md) | `required_capabilities` referencia capabilities expuestas por las tools catalogadas ahí; discovery semantico comparte metadata con ToolRegistry. |
| [08 Gobernanza](08-gobernanza-seguridad-y-operaciones.md) | `audit.level` declarado aquí dispara el nivel de logging definido ahí. |

---

## Decisiones implementadas por este doc

Este doc consolida (ver `ANEXO-B-decision-log-por-tema.md`):

- **D1** esta sesión: jerarquía Agent compone Skills + integración de 2 marketplaces externos.
- **#9** Especialización rol + tool discovery progresivo.
- **#15** Skill learning por demostración.
- **#20** Writing style learning (skill especial).
- **#22** Módulo de Templates (skills de templating).
- **#47-56** Inventario formal (skills cuyo origen es COPY-HERMES están aquí también).
- **#66** Legal cubierto por skills + templates (no MCP dedicado).
- **#69** 17 tools FREE — sus skills wrappers tienen `audit.level: bajo` por economía.
- **C0** Claude local + descubrimiento semantico + carga progresiva de skills.

---

## Criterios de verificación

Tras implementar este doc:

1. **Test de carga**: `vigilador-admin skill list` muestra ≥40 skills curated + ≥285 externas = ~325+ totales.
2. **Test de filtrado por Modo**: `vigilador-admin skill list --mode CFO` muestra solo skills compatibles con CFO.
3. **Test de invocación**: skill `reconciliation` invocada desde Modo CFO ejecuta todas sus capabilities con resultado válido.
4. **Test de Skill Learning**: simular gap → activar modo demostración → tras finalizar usuario, skill nueva aparece en `config/skills/learned/`.
5. **Test de override**: crear curated con mismo `id` que externa, verificar que el listing muestra solo la curated.
6. **Test de curator pull**: simular cambio en repo externo → curator pull la trae a `_pending/` → tests sintéticos pasan → promoción a activo.
7. **Test de duplicate detection**: 2 skills con descripción semánticamente similar → curator las flagea en Dreaming Report.
8. **Test de stats**: invocar skill 10 veces, 5 con error → `vigilador_skill_success_rate{skill_id="X"}` = 0.5; flag para revisión.
9. **Test Claude local**: `.claude/skills/speckit-plan/SKILL.md` aparece como `external:claude-local/speckit-plan` con hash, source y permisos.
10. **Test contexto minimo**: una busqueda de skill carga `SkillCard` de todo el catalogo, `SkillSummary` solo de top-k y `SkillBody` solo de la skill seleccionada.
