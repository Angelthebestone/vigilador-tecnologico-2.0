# 02 — Modos y Personalidades

> Documento que cierra la **brecha 3** del set: modos de operación como concepto user-facing del Vigilador 3.0. Antes los "modos" se confundían con playbooks; aquí se modela una capa explícita por encima.

> **Decisión D2 de esta sesión**: Modos por industria/rol preconfigurados. Cada Modo materializa una persona empresarial (CEO, CFO, Consultor Legal, Vigilancia Tech, Marketing, Vendedor B2B, Operaciones PYME).

> **Corrección vigente**: los Modos no solo cambian tono/skills. Tambien cargan `company_geo` para adaptar busquedas, normativa, impuestos y fuentes al pais/departamento/municipio del usuario. Ver [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md).

---

## Concepto

Un **Modo** es la unidad user-facing del Vigilador 3.0. Se define como:

```
Mode = SOUL subset + COMPANY subset + company_geo + skills permitidas + playbooks default + tools allowlist
```

**Por qué Modo y no solo Playbook**: un playbook describe un flujo (`technology-watch`, `goal-pursuit`); un modo describe **quién es el asistente en ese momento**. Un mismo playbook puede ejecutarse desde varios modos con tono, contexto, vocabulario y skills diferentes.

**Por qué Modo y no solo Agent**: en CrewAI un `Agent` es un rol dentro de una `Crew` (ej: "Investigador en `decision-debate`"). Un Modo, en cambio, es una **persona empresarial completa** que el usuario adopta al hablar con el sistema (`/mode CFO`). Un Modo orquesta múltiples Agents según el playbook activo.

Ejemplo:
- Usuario en canal Telegram: `/mode CFO`
- Sistema carga: SOUL (tono ejecutivo financiero) + COMPANY/organization.md + COMPANY/policies.md (subset financiero) + skills (`reconciliation`, `variance-analysis`, `journal-entry`, `audit-support` del plugin `finance:`) + playbooks default (`compliance-audit`, `decision-debate`) + tools (`excel_local`, `quickbooks`, `power_bi_file_reader`, `markitdown`).
- Usuario: "¿Cómo cerramos el mes?"
- Sistema responde como CFO, no como Vigilancia Tech genérico.

Ejemplo con geografia:
- Empresa ubicada en Barrancabermeja, Santander, Colombia.
- Usuario en modo `Consultor Legal`: "¿Qué obligaciones locales debo revisar para abrir una nueva sede?"
- Sistema carga habilidades legales estandar, pero busca fuentes oficiales vigentes de municipio/departamento/nacion antes de responder; diferencia impuestos, tasas, permisos, uso del suelo y normas tecnicas aplicables.

---

## Activación

### Por canal explícito

```
/mode CFO
/mode Vigilancia Tech
/mode Consultor Legal
```

Persiste durante la sesión hasta `/mode default` o cierre. Aplica en Web/SSE, Telegram, WhatsApp.

### Por autodetección (heurística + LLM)

Si el usuario no especifica modo:

1. **Heurística por canal**: el operador puede preconfigurar un modo default por canal en `config/channels/<channel>.yaml` (ej: WhatsApp del equipo de ventas → default `Vendedor B2B`).
2. **Heurística por turno**: regex sobre el primer mensaje del usuario detecta keywords (`flujo de caja`, `conciliación` → `CFO`; `propuesta`, `cotización` → `Vendedor B2B`).
3. **Fallback LLM**: si heurísticas no resuelven, 1 llamada corta a MiniMax clasifica intent → modo. Log de la decisión para auditabilidad (POLA).

Default si todo falla: modo `general` (1 agente generalista sin contexto empresarial específico, equivale al comportamiento del 2.0 sin Modos).

### Por evento (Dreaming + Proactive triggers)

Cuando el agente actúa proactivamente (decisión #102), el trigger declara qué modo asumir:

```yaml
event_subscriptions:
  - source: gmail_push
    filter: "from:cliente_principal@*"
    playbook: deal-research
    mode: Vendedor B2B
```

---

## Catálogo inicial de Modos

| Modo | Persona | SOUL hints | COMPANY subset | Skills permitidas (categorías) | Playbooks default | Tools allowlist (dominios) |
|---|---|---|---|---|---|---|
| **default** | Asistente generalista | Tono neutro, formal | identity.md | todas las FREE | `general` | search, web, documents |
| **CEO** | Director ejecutivo | Tono estratégico, decisivo, prioriza ROI y oportunidad | identity.md, organization.md (resumen), policies.md (resumen) | `agency-agents/Strategy`, `Marketing`, `Operations` (subset alto nivel) | `decision-debate`, `market-research`, `goal-pursuit` | search, research, productivity, communication, analytics |
| **CFO** | Director financiero | Tono ejecutivo financiero, riguroso con cifras | organization.md, processes.md (finanzas), policies.md (financieras) | plugin `finance:` (reconciliation, variance-analysis, journal-entry, audit-support, close-management, sox-testing, financial-statements) | `compliance-audit`, `decision-debate` | finance, analytics, documents, productivity |
| **Consultor Legal** | Asesor jurídico | Tono cauto, cita fuentes legales, define alcances | identity.md, policies.md, processes.md (contratos), company_geo | skill custom legal-* + templates contratos + busqueda normativa local | `compliance-audit`, `general`, `company-optimization` | documents, web, research (con énfasis legal) |
| **Vigilancia Tech** | Analista tecnológico | Hereda comportamiento del 2.0 (6 agentes de rama) | identity.md, systems.md | skills del 2.0 (técnicas, riesgo, normativa) | `technology-watch` (= playbook que envuelve `BranchCoordinator`) | search, research, web, analytics |
| **Marketing** | Director de marketing | Tono creativo, orientado a marca y conversión | identity.md, organization.md (marketing) | `agency-agents/Marketing`, `Design`, `UX Copy` | `market-research`, `goal-pursuit` | design, media, communication, analytics |
| **Vendedor B2B** | Account executive | Tono persuasivo profesional, foco en lead/deal | organization.md (ventas), processes.md (CRM) | skills `lead-research`, `proposal-generation`, `email-cadence` | `deal-research` (subset goal-pursuit), `general` | crm, communication, productivity, documents |
| **Operaciones PYME** | Gerente operacional | Tono práctico, foco en productividad y automatización | identity.md, processes.md, systems.md | skills `process-automation`, `document-generation`, `report-scheduling` | `general`, `goal-pursuit` | productivity, documents, communication, code, analytics |

**Notas**:
- El modo **Vigilancia Tech** garantiza compatibilidad total con el 2.0: invoca el playbook `technology-watch` que ejecuta los 6 agentes de rama mediante `BranchCoordinator` (preservado).
- Los demás modos son nuevos y se construyen en F4 (decisión #100 del plan maestro: orquestación avanzada).
- Cualquier organización puede definir Modos custom (sección "Cómo crear un Mode custom").

---

## Schema YAML de un Mode

Ubicación: `config/modes/<id>.yaml`.

```yaml
id: CFO
display_name: "Director Financiero"
description: "Asistente con perspectiva financiera ejecutiva. Riguroso con cifras, cita fuentes, propone con tradeoffs."
version: "1.0.0"

soul_overlay:
  # Subset/extensión sobre config/soul.md base
  tone: "ejecutivo, riguroso, conciso"
  vocabulary_emphasis:
    - "EBITDA"
    - "flujo de caja"
    - "conciliación"
  do_rules:
    - "Cita siempre la fuente de cualquier cifra"
    - "Si no hay dato en COMPANY, pide aclaración antes de inventar"
  dont_rules:
    - "No emitir juicios de auditoría sin evidencia documentada"
    - "No proyectar a futuro sin marcar 'estimado'"

company_subset:
  # Qué archivos de config/company/ se cargan como frozen snapshot
  files:
    - "organization.md"
    - "processes.md"
    - "policies.md"
  sections_filter:
    organization.md: ["finanzas", "contabilidad"]
    processes.md: ["cierre mensual", "reconciliación", "presupuesto"]

company_geo:
  country: "Colombia"
  department: "Santander"
  municipality: "Barrancabermeja"
  timezone: "America/Bogota"
  regulatory_sources_policy: "buscar fuentes oficiales vigentes antes de afirmar"

skills:
  # Categorías (cargan todas las skills del namespace) y skills individuales
  categories:
    - "finance:*"
  individual:
    - "agency-agents/CFO"
    - "scientific-agent-skills/data-analysis"
  excluded:
    - "finance:transactional"  # mover dinero está prohibido (decisión #36)

playbooks:
  default: "compliance-audit"
  allowed:
    - "compliance-audit"
    - "decision-debate"
    - "company-optimization"
    - "general"
    - "goal-pursuit"

tools:
  # Dominios completos permitidos
  domains:
    - "finance"
    - "analytics"
    - "documents"
    - "productivity"
    - "web"       # requerido para normativa/impuestos vigentes por geografia
  # Tools específicas explícitamente excluidas
  excluded:
    - "plaid.transfer"  # cero capacidad de mover dinero
    - "quickbooks.send_payment"

mode_settings:
  language_default: "es"
  language_external_auto_detect: true  # decisión #40
  intensity: "PROACTIVE"  # REACTIVE | PROACTIVE | AUTONOMOUS — solo cambia agresividad del Dreaming
  require_approval_for:
    - "outbound_email_count > 5"  # más estricto que el default (>10)
    - "company_md_modification"

audit:
  full_autonomy: true  # D4 esta sesión — el agente puede modificar todo
  approval_required_for_files:
    - "config/company/policies.md"  # única excepción
```

### Validación del schema

`enterprise/modes/mode_loader.py` valida al boot:
- Referencias a skills existen en `skills/` o en marketplaces declarados en `04-skills-y-capacidades.md`.
- Referencias a playbooks existen en `config/playbooks/`.
- `tools.excluded` tienen formato válido `<tool>.<capability>`.
- `audit.approval_required_for_files` tienen rutas válidas.
- `company_geo` tiene al menos `country`; si incluye `department`/`municipality`, las busquedas normativas deben usar esos niveles antes de generalizar.

Si la validación falla: el Modo no se registra y queda fuera del listing de `/mode`. Log de error con causa específica.

---

## Composición Mode ↔ Playbook ↔ Skill

```
┌──────────────────────────────────────────┐
│ Usuario (Web/SSE | Telegram | WhatsApp)  │
└──────────────┬───────────────────────────┘
               │ /mode CFO
               ▼
┌──────────────────────────────────────────┐
│ Mode CFO                                 │
│  ├─ SOUL overlay                         │
│  ├─ COMPANY subset (frozen snapshot)     │
│  ├─ Skills permitidas: finance:*         │
│  ├─ Playbooks default: compliance-audit  │
│  └─ Tools allowlist: finance, analytics  │
└──────────────┬───────────────────────────┘
               │ usuario pregunta algo
               ▼
┌──────────────────────────────────────────┐
│ ComplexityClassifier                     │
│ (SIMPLE | MODERADA | COMPLEJA)           │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ PlaybookRunner carga                     │
│ playbook compliance-audit                │
│  ├─ Agents: AuditorAgent, FinanceLead    │
│  └─ Tools: filtradas por Mode.tools      │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ Cada Agent invoca Skills permitidas      │
│ Cada Skill invoca Tools/Capabilities     │
└──────────────────────────────────────────┘
```

**Reglas de composición**:

1. **Mode filtra Skills**: el `ToolRegistry` aplica `Mode.skills` como allowlist + `Mode.skills.excluded` como denylist.
2. **Mode filtra Tools**: `Mode.tools.domains` + `Mode.tools.excluded` se aplican como segundo filtro encima de skills.
3. **Playbook respeta Mode**: si un playbook declara un agent que necesita una skill no permitida por el Mode, el `PlaybookRunner` rechaza la sesión con error explícito ("Mode CFO no permite skill X requerida por playbook Y").
4. **Sin Mode no hay sesión**: cada sesión TIENE un Mode (incluso `default`). No existe "modo nulo".
5. **Mode no puede ser modificado mid-sesión** salvo con `/mode <otro>` explícito (rebuild de contexto).
6. **Mode adapta por geografia**: cuando una respuesta depende de regulacion, impuestos, permisos o normas tecnicas, el agente debe buscar primero fuentes vigentes del municipio/departamento/pais declarados en `company_geo`.

---

## Diferencia entre Modes y Roles (CrewAI agents)

Confusión frecuente:

| Concepto | Vive en | Granularidad | Ciclo de vida |
|---|---|---|---|
| **Mode** | `config/modes/<id>.yaml` | Sesión entera | Cambia con `/mode` o cierre |
| **Role (CrewAI Agent)** | Dentro de un playbook YAML (`config/playbooks/<id>.yaml`) | Una tarea o sub-tarea del playbook | Vive lo que dura el playbook |

**Ejemplo concreto**:
- Modo activo: `CFO`
- Playbook: `decision-debate`
- Agents del playbook: `RiskAdvocate`, `OpportunityAdvocate`, `Moderator`
- Cada Agent del debate "habla como CFO" porque el SOUL overlay del Mode se inyecta en su prompt base, pero cumple su rol específico dentro del debate.

Un mismo playbook (`decision-debate`) ejecutado desde modo `CEO` vs `CFO` produce el mismo flujo lógico, pero la voz, vocabulario, tradeoffs priorizados y skills disponibles cambian.

---

## Guía: cómo crear un Mode custom en 5 pasos

Para que el operador del Vigilador adapte un Modo a su industria específica:

### Paso 1: clonar un Mode base como punto de partida

```bash
cp config/modes/CFO.yaml config/modes/CFO-fintech.yaml
```

### Paso 2: ajustar `display_name`, `description`, `id`

```yaml
id: CFO-fintech
display_name: "CFO Fintech LATAM"
description: "CFO con expertise en regulación financiera fintech LATAM, énfasis en compliance SARLAFT/SOX."
```

### Paso 3: extender `company_subset` y `soul_overlay`

Añadir secciones específicas:

```yaml
soul_overlay:
  do_rules:
    - "Cita siempre Circular Externa SFC cuando aplique"
    - "Considera regulación SARLAFT/UIAF al sugerir flujos"

company_subset:
  files:
    - "organization.md"
    - "processes.md"
    - "policies.md"
    - "compliance-fintech.md"  # archivo custom de la empresa

company_geo:
  country: "Colombia"
  department: "Santander"
  municipality: "Barrancabermeja"
```

### Paso 4: declarar skills custom (opcional)

Si la empresa tiene skills aprendidas en `skills/learned/` específicas (decisión #15), añadirlas:

```yaml
skills:
  individual:
    - "learned/sarlaft-monthly-report"
    - "learned/sfc-circular-tracker"
```

### Paso 5: validar y registrar

```bash
vigilador-admin mode validate CFO-fintech
vigilador-admin mode register CFO-fintech
```

`mode validate` ejecuta el `ModeLoader.validate()`. `mode register` lo añade al listing global. Tras esto, `/mode CFO-fintech` está disponible en todos los canales.

---

## Modos vs intensidad operacional

Aunque el usuario optó por "Modos por industria/rol" en lugar de "intensidad operacional" como concepto principal, la **intensidad** se conserva como campo dentro de cada Modo:

```yaml
mode_settings:
  intensity: "PROACTIVE"  # REACTIVE | PROACTIVE | AUTONOMOUS
```

| Intensidad | Comportamiento |
|---|---|
| **REACTIVE** | Solo responde cuando se le pregunta. Dreaming corre pero sin enviar alertas. Goal-pursuit deshabilitado. |
| **PROACTIVE** | Default para la mayoría de modos. Dreaming envía resúmenes y sugiere acciones. Goal-pursuit pide aprobación por checkpoint. |
| **AUTONOMOUS** | Goal-pursuit ejecuta sin checkpoints intermedios (solo al inicio y al final). Más decisiones autónomas dentro del audit trail (D4). Requiere modos con `audit.full_autonomy: true`. |

El operador puede sobrescribir por sesión: `/mode CFO --intensity AUTONOMOUS`.

---

## Integración con el resto del set

| Doc | Cómo se integra |
|---|---|
| [01 Arquitectura](01-vision-y-arquitectura.md) | La jerarquía `Channel → Mode → Agent → Playbook → Skill → Capability` se define ahí; este doc instancia la capa `Mode`. |
| [03 Playbooks](03-playbooks-y-orquestacion.md) | Los playbooks declaran `mode_compatible: [CFO, CEO]`. Si el Mode activo no está en esa lista, el playbook no se ofrece. |
| [04 Skills](04-skills-y-capacidades.md) | `skills.categories` y `skills.individual` referencian el catálogo de Skills definido ahí. |
| [05 Autoaprendizaje](05-autoaprendizaje-y-autonomia.md) | `audit.full_autonomy` y `audit.approval_required_for_files` aplican el ciclo definido ahí. |
| [06 Catálogo tools](06-catalogo-tools-y-extraccion.md) | `tools.domains` y `tools.excluded` referencian las 79 capacidades catalogadas ahí. |
| [08 Gobernanza](08-gobernanza-seguridad-y-operaciones.md) | `mode_settings.require_approval_for` y `mode_settings.language_*` aplican las políticas globales. |

---

## Decisiones implementadas por este doc

Este doc implementa la **decisión D2 de esta sesión** y referencia las siguientes del plan maestro (ver `ANEXO-B-decision-log-por-tema.md` para trazabilidad completa):

- **#13** (COMPANY.md como contexto empresarial declarativo) → `company_subset` lo segmenta por Modo.
- **#16** (COMPANY partido en 5 archivos) → `company_subset.files` referencia esos archivos.
- **#21** (deep-research como playbook explícito) → cualquier Modo puede invocarlo si está en `playbooks.allowed`.
- **#40** (LanguageRouter por turno) → `mode_settings.language_*`.
- **#42** (Onboarding wizard) → el wizard pregunta al usuario qué Modos quiere activar al inicio.
- **C0** (geografia empresarial) → `company_geo` adapta normativa, impuestos, fuentes oficiales y normas tecnicas por pais/departamento/municipio.

---

## Criterios de verificación

Tras implementar este doc:

1. **Test de carga**: cada Modo del catálogo inicial valida sin error con `vigilador-admin mode validate`.
2. **Test de activación**: `/mode CFO` desde Telegram cambia el SOUL aplicado a la siguiente respuesta (verificable en log).
3. **Test de filtrado**: con Modo `CFO` activo, intentar invocar tool `plaid.transfer` debe fallar con error explícito.
4. **Test de compatibilidad**: con Modo `Vigilancia Tech` activo, el playbook `technology-watch` ejecuta los 6 agentes de rama del 2.0 sin diferencias funcionales.
5. **Test de creación custom**: clonar `CFO.yaml` a `CFO-fintech.yaml`, modificar 1 campo, registrar; debe aparecer en `/mode <list>`.
6. **Test geo**: con `company_geo` Colombia/Santander/Barrancabermeja, una consulta legal/tributaria debe registrar busquedas en fuentes municipales/departamentales/nacionales antes de producir respuesta.
