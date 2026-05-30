# Feature Specification: Jerarquia Conceptual Channel-Mode-Agent-Playbook-Skill-Capability

**Feature ID**: 010-jerarquia-agent-mode-skill
**Created**: 2026-05-29
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/01-vision-y-arquitectura.md](../../plan%20vigilador%203.0/01-vision-y-arquitectura.md) (fuente principal: seccion "Jerarquia conceptual", "Estructura de carpetas", "Stack tecnologico oficial")
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (delimitacion MVP vs roadmap)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md) (C0 reglas de estructura)

---

## Problem Statement

El Vigilador 3.0 introduce una jerarquia de 6 niveles (Channel, Mode, Agent, Playbook, Skill, Capability/Tool) que organiza toda la logica del agente empresarial. Esta jerarquia necesita estar definida formalmente como modelo conceptual, con reglas de composicion claras, estructura de carpetas alineada y preservacion explicita del flujo technology-watch del 2.0 como playbook dentro de la nueva jerarquia.

Sin una definicion formal de esta jerarquia y su mapeo a la estructura de carpetas `src/vigilancia_multiagente/enterprise/`, los specs posteriores (modos, playbooks, skills, tools) no tienen un marco de referencia comun para declarar donde vive cada componente ni como se componen entre si.

Este spec documenta la jerarquia como modelo conceptual y su proyeccion a la estructura de carpetas. La implementacion concreta de cada nivel se materializa en specs separados: 009 (foundation + ToolRegistry), 012 (modos + playbooks), 011 (tools Tier 1).

---

## Scope Boundaries

### In Scope

- Definicion formal de los 6 niveles de la jerarquia y sus reglas de composicion (traza: doc 01, seccion "Jerarquia conceptual").
- Mapeo de cada nivel a su ubicacion en la estructura de carpetas `src/vigilancia_multiagente/enterprise/` y `config/` (traza: doc 01, seccion "Estructura de carpetas").
- Declaracion del stack tecnologico que soporta la jerarquia: Python 3.11+, CrewAI para combos nuevos, BranchCoordinator preservado, YAML declarativo para playbooks/modos/skills (traza: doc 01, seccion "Stack tecnologico oficial").
- Preservacion explicita del flujo technology-watch del 2.0 como playbook dentro de la jerarquia, invocando BranchCoordinator sin modificaciones (traza: doc 01, tabla "Componentes nuevos vs preservados").
- Distincion MVP vs roadmap para cada nivel de la jerarquia segun 00b.
- Contratos de composicion entre niveles: quien invoca a quien, que filtra que.

### Out of Scope

- Implementacion de modos concretos (default, Vigilancia Tech, CEO) y sus YAMLs -> spec 012 (F4a).
- Implementacion de playbooks concretos y PlaybookRunner -> spec 012 (F4a).
- Implementacion de ToolRegistry y ToolWrapper -> spec 009 (F1, ya cubierto).
- Implementacion de tools Tier 1 nuevas -> spec 011 (F3a).
- Implementacion de ModeResolver y ComplexityClassifier -> spec 012 (F4a).
- Channels Telegram y WhatsApp -> roadmap post-MVP (solo Web/SSE en MVP, decision 00b).
- Skills marketplace externo (K-Dense, agency-agents) -> roadmap post-MVP.
- SubagentRegistry operativo -> spec 012 (F4a).
- Dreaming, autoaprendizaje, loops autonomos -> roadmap post-MVP (F5b+).

---

## Assumptions

- **A-01**: La jerarquia de 6 niveles definida en doc 01 (D1 de la sesion de planificacion) es la arquitectura conceptual definitiva del 3.0. No se anticipan niveles adicionales en MVP.
- **A-02**: El BranchCoordinator del 2.0 se preserva intacto y se invoca desde el playbook `technology-watch` sin modificaciones (principio "Cambios quirurgicos", constitucion #5).
- **A-03**: Los playbooks se declaran en YAML bajo `config/playbooks/`. Los modos se declaran en YAML bajo `config/modes/`. Las skills curadas viven en `config/skills/curated/`. Convencion sobre configuracion (constitucion, principio de desarrollo).
- **A-04**: En MVP solo se activan 3 modos (default, Vigilancia Tech, CEO) y 3 playbooks (technology-watch, deep-research, general) segun 00b. El resto queda documentado pero no implementado.
- **A-05**: La estructura de carpetas `enterprise/` con sus 13 subcarpetas se crea vacia en F0 (spec 009 FR-003) y se puebla progresivamente por specs posteriores.
- **A-06**: CrewAI se usa para playbooks nuevos que requieren multiples agentes coordinados. El playbook technology-watch NO usa CrewAI; invoca directamente BranchCoordinator.
- **A-07**: El canal MVP es exclusivamente Web/SSE. Telegram y WhatsApp son roadmap post-MVP.
- **A-08**: El ModeContext es un frozen snapshot al inicio de sesion que contiene SOUL overlay, COMPANY subset, Skills allowlist, Playbooks allowed y Tools allowlist (doc 01, diagrama de capas).

---

## User Scenarios & Testing

### Primary User Story

Como **arquitecto del sistema Vigilador 3.0**, quiero que la jerarquia Channel-Mode-Agent-Playbook-Skill-Capability este formalmente definida con reglas de composicion claras y mapeada a la estructura de carpetas, para que cada spec posterior pueda declarar sin ambiguedad donde vive su componente y como se conecta con los demas niveles.

### Acceptance Scenarios

1. **Given** la estructura de carpetas creada por spec 009 (F0), **When** se inspecciona `src/vigilancia_multiagente/enterprise/`, **Then** existen las subcarpetas `orchestration/`, `modes/`, `skills_marketplace/`, `intelligence/`, `triggers/`, `auth/`, `governance/`, `memory/`, `observability/`, `ingestion/`, `tooling/`, `dreaming/`, `mcp/` alineadas con los niveles de la jerarquia.

2. **Given** la jerarquia definida, **When** el playbook `technology-watch` se ejecuta en modo `Vigilancia Tech`, **Then** el flujo es: Channel (Web/SSE) -> ModeResolver resuelve `vigilancia-tech` -> PlaybookRunner carga `config/playbooks/technology-watch.yaml` -> invoca BranchCoordinator del 2.0 -> 6 agentes de rama ejecutan sus skills/capabilities existentes. Cero modificaciones al codigo del 2.0.

3. **Given** un Mode activo con su allowlist de skills y tools, **When** un Agent dentro de un playbook solicita una Skill no permitida por el Mode, **Then** la Skill no se ejecuta y se registra un log estructurado indicando la restriccion.

4. **Given** la configuracion YAML de un playbook, **When** se declara un Agent con un rol y sus skills permitidas, **Then** el PlaybookRunner instancia el Agent con acceso exclusivamente a las Skills declaradas, filtradas adicionalmente por el Mode activo.

5. **Given** la estructura de `config/`, **When** se agrega un nuevo playbook como archivo YAML en `config/playbooks/`, **Then** el sistema lo reconoce sin modificar codigo existente (OCP).

6. **Given** la jerarquia operativa en MVP, **When** se ejecuta `scripts/check-layer-imports.py` sobre el codigo del 3.0, **Then** no hay violaciones de capa entre los niveles de la jerarquia.

### Edge Cases

- **EC-01**: Un Mode referencia un playbook que no existe en `config/playbooks/` -> el sistema falla con error explicito indicando el playbook faltante y el Mode que lo referencia.
- **EC-02**: Un playbook YAML declara un Agent con un skill_id que no existe en el registro -> el PlaybookRunner falla al cargar con error explicito antes de ejecutar.
- **EC-03**: El canal Web/SSE recibe un `/mode X` donde X no esta registrado -> ModeResolver retorna error claro al usuario y no cambia el modo activo.
- **EC-04**: El BranchCoordinator del 2.0 falla durante la ejecucion del playbook technology-watch -> el error se propaga al PlaybookRunner sin ser silenciado (constitucion #4).

---

## Functional Requirements

### Modelo conceptual de la jerarquia (definicion)

- **FR-001**: El sistema MUST implementar una jerarquia de 6 niveles con la siguiente relacion de composicion: Channel contiene Mode, Mode contiene Agent (via Playbook), Playbook contiene Agent(s), Agent invoca Skill(s), Skill invoca Capability(ies), Capability es implementada por Tool. (Traza: doc 01, seccion "Jerarquia conceptual", D1.)

- **FR-002**: Cada nivel de la jerarquia MUST tener una responsabilidad unica definida: Channel adapta interfaz externa; Mode filtra contexto empresarial; Agent ejecuta un rol dentro de un flujo; Playbook declara el flujo de Agents; Skill es receta atomica reutilizable; Capability es verbo ejecutable con schema; Tool es modulo Python que implementa N capabilities. (Traza: doc 01, tabla "Reglas de composicion".)

- **FR-003**: El Mode MUST filtrar que Skills, Playbooks y Tools estan disponibles para los Agents que operan bajo el. Un Agent no MUST acceder a Skills o Tools excluidas por su Mode activo. (Traza: doc 01, "ModeContext frozen snapshot" + ISP en tabla de alineacion.)

- **FR-004**: El Playbook MUST ser declarativo en formato YAML, definiendo que Agents instanciar, su orden o paralelismo, y que Skills tiene permitidas cada Agent. (Traza: doc 01, "PlaybookRunner carga YAML del playbook activo".)

- **FR-005**: El sistema MUST permitir agregar nuevos Playbooks, Modos y Skills mediante archivos YAML sin modificar codigo existente (OCP). (Traza: doc 01, tabla alineacion constitucion, fila OCP.)

### Estructura de carpetas

- **FR-006**: La estructura `src/vigilancia_multiagente/enterprise/` MUST contener subcarpetas separadas por concern alineadas con los niveles de la jerarquia: `orchestration/` (PlaybookRunner), `modes/` (ModeResolver, ModeContext), `skills_marketplace/` (registro de skills), `tooling/` (ToolRegistry, ToolWrapper), `mcp/` (MCPProcessSupervisor). (Traza: doc 01, seccion "Estructura de carpetas".)

- **FR-007**: La configuracion declarativa MUST residir en `config/` con subdirectorios: `modes/` (YAMLs de modos), `playbooks/` (YAMLs de playbooks), `skills/` (matrices de skills con `curated/` y `learned/`), `company/` (contexto empresarial), `mcp/` (MCPs externos). (Traza: doc 01, seccion "Estructura de carpetas".)

- **FR-008**: Cada archivo bajo `enterprise/` MUST respetar la separacion de capas verificable por `scripts/check-layer-imports.py`. Los modulos de orchestration no MUST importar directamente de infra; los modulos de modes no MUST importar de tooling directamente. (Traza: doc 01, criterio de verificacion #5; constitucion #3 Modularidad.)

### Preservacion del flujo technology-watch del 2.0

- **FR-009**: El playbook `technology-watch` MUST invocar el `BranchCoordinator` existente del 2.0 sin modificaciones al codigo de `application/execution/branch_coordinator.py` ni a los 6 agentes de rama. (Traza: doc 01, tabla componentes, fila "Preservar BranchCoordinator".)

- **FR-010**: El playbook `technology-watch` MUST ser declarable como YAML en `config/playbooks/technology-watch.yaml` que referencia al BranchCoordinator como su executor, sin requerir CrewAI. (Traza: doc 01, "CrewAI para combos nuevos + BranchCoordinator preservado".)

- **FR-011**: Los tests existentes del 2.0 MUST seguir pasando al 100% tras la implementacion de la jerarquia. Cero regresiones. (Traza: doc 01, criterio de verificacion #2; constitucion #5.)

### Stack y constraints tecnologicos

- **FR-012**: El lenguaje de implementacion de todos los componentes bajo `enterprise/` MUST ser Python 3.11+ puro. Cero Node en runtime para tools (MCPs externos via STDIO pueden ser Node). (Traza: doc 01, stack, decision #50.)

- **FR-013**: Los playbooks nuevos que requieran multiples agentes coordinados MUST usar CrewAI como framework de agentes. El playbook technology-watch queda exento por usar BranchCoordinator nativo. (Traza: doc 01, stack, decision #6.)

- **FR-014**: Cada archivo nuevo bajo `enterprise/` MUST ser menor o igual a 400 LOC. Excepciones requieren justificacion documentada. (Traza: constitucion #2 Simplicidad; doc 01 referencia C0 #10.)

### Composicion y filtrado entre niveles

- **FR-015**: El ModeContext MUST ser un frozen snapshot creado al inicio de la sesion que contiene: SOUL overlay, COMPANY subset, Skills allowlist, Playbooks allowed, Tools allowlist. No MUST mutar durante la sesion. (Traza: doc 01, diagrama de capas, bloque "ModeContext".)

- **FR-016**: El ModeResolver MUST resolver el modo activo siguiendo la cadena: explicito (`/mode X`) -> autodetect por canal -> autodetect heuristica -> fallback LLM -> default. (Traza: doc 01, diagrama de capas, bloque "ModeResolver".) *Contract-only — implementación diferida a spec 012.*

- **FR-017**: El ToolRegistry.discover(role, intent) MUST filtrar tools por el Mode activo antes de aplicar discovery semantico. Tools excluidas por el Mode no MUST aparecer en resultados. (Traza: doc 01, tabla alineacion ISP: "Mode filtra Skills y Tools antes de exponerlas".)

---

## Key Entities

- **Channel**: interfaz de entrada al sistema. En MVP solo Web/SSE. Adapta payload externo a `InboundMessage` normalizado. Vive en `api/channels/`.
- **Mode**: persona empresarial activa con contexto geografico y filtros. Declarado en `config/modes/<id>.yaml`. Produce un ModeContext frozen al inicio de sesion.
- **ModeContext**: snapshot inmutable que contiene SOUL overlay, COMPANY subset, allowlists de skills/playbooks/tools. Vive en memoria durante la sesion.
- **Agent**: rol dentro de un flujo (BranchAgent, DebateModerator, GoalDecomposer, etc.). Declarado dentro de un playbook YAML o como clase Python en `enterprise/orchestration/` o `application/agents/`.
- **Playbook**: flujo declarativo YAML que define que Agents instanciar y su coordinacion. Vive en `config/playbooks/<id>.yaml`.
- **Skill**: receta atomica reutilizable que invoca una o mas Capabilities en orden definido. Registrada en `config/skills/`.
- **Capability**: verbo ejecutable con schema de entrada/salida (ej: `tavily_search`, `docx_generate`). Unidad minima de ejecucion.
- **Tool**: modulo Python que implementa N capabilities y cumple el protocolo `ToolWrapper`. Vive en `enterprise/tooling/` (Tier 1) o como MCP externo (Tier 2).
- **PlaybookRunner**: orquestador que carga un playbook YAML, instancia Agents y coordina su ejecucion. Vive en `enterprise/orchestration/playbook_runner.py`.
- **ModeResolver**: componente que determina el Mode activo para una sesion. Vive en `enterprise/modes/mode_resolver.py`.

---

## Success Criteria

- **SC-001**: La estructura de carpetas `enterprise/` contiene las 13 subcarpetas documentadas y cada una mapea a exactamente un concern de la jerarquia, verificable por inspeccion de directorio.
- **SC-002**: El playbook `technology-watch` ejecuta el flujo completo del 2.0 (BranchCoordinator + 6 agentes de rama) sin modificaciones al codigo existente, verificable por tests E2E del 2.0 pasando al 100%.
- **SC-003**: Agregar un nuevo playbook YAML en `config/playbooks/` es reconocido por el sistema sin modificar codigo Python, verificable por test de integracion que registra un playbook dummy y lo ejecuta.
- **SC-004**: El filtrado de Mode sobre tools/skills es efectivo: un Agent operando bajo un Mode restrictivo no puede invocar tools excluidas, verificable por test unitario con Mode mock.
- **SC-005**: `scripts/check-layer-imports.py` pasa sin violaciones sobre todo el codigo bajo `enterprise/`, verificable por ejecucion del script en CI.
- **SC-006**: Cero archivos bajo `enterprise/` exceden 400 LOC sin justificacion documentada, verificable por script de conteo.

---

## Delivery Constraints

- **Constitucion v1.2.0 -- Cambios quirurgicos (#5)**: el codigo del 2.0 (`application/`, `api/routes/`, `domain/`, `infra/`) no se modifica. La jerarquia se construye al lado en `enterprise/`.
- **Constitucion v1.2.0 -- Simplicidad obligatoria (#2)**: la jerarquia tiene exactamente 6 niveles porque el plan los define (D1). No se agregan niveles intermedios especulativos.
- **Constitucion v1.2.0 -- Modularidad primero (#3)**: cada nivel de la jerarquia tiene su subcarpeta con responsabilidad unica. Sin mezcla de orquestacion, dominio e infra en un mismo modulo.
- **Constitucion v1.2.0 -- OCP**: nuevos modos, playbooks y skills se agregan por YAML sin tocar runners.
- **Constitucion v1.2.0 -- CQS**: ToolRegistry solo lee; HealthMonitor solo escribe (decision #81).
- **MVP vs Roadmap (00b)**: en MVP se implementan 3 modos, 3 playbooks, 4 dominios activos. El resto de la jerarquia queda documentado como roadmap. La arquitectura MUST soportar la activacion futura sin refactor.

---

## MVP vs Roadmap por nivel de la jerarquia

| Nivel | MVP (segun 00b) | Roadmap post-MVP |
|---|---|---|
| Channel | Web/SSE unicamente | Telegram, WhatsApp, webhooks |
| Mode | default, Vigilancia Tech, CEO (reducido) | CFO, Consultor Legal, Marketing, Vendedor B2B, Operaciones PYME |
| Agent | BranchAgents del 2.0 preservados + agentes basicos de playbooks MVP | GoalDecomposer, CrewAI agents especializados, SubagentRegistry recursivo |
| Playbook | technology-watch, deep-research, general | decision-debate (completo), market-research, compliance-audit, goal-pursuit, app-development, artifact-development, company-optimization |
| Skill | Skills existentes del 2.0 + skills basicas de los 4 dominios MVP | Skills de 13 dominios adicionales, skills learned, marketplace externo |
| Capability/Tool | 20 capacidades (4 Tier 1 nuevas + 16 MCPs) | ~59 capacidades adicionales, sub-tools *_local.py, Tier 3 traducidos |

---

## Dependencies on previous specs

- **spec 009 (MVP Foundation)**: crea la estructura de carpetas `enterprise/` vacia (FR-003 de 009), el ToolRegistry con discovery semantico, y la persistencia base. Este spec 010 define el modelo conceptual que esa estructura materializa.

## Specs descendientes que dependen de este

- **spec 011 (F3a tools)**: las tools implementan el nivel Capability/Tool de esta jerarquia.
- **spec 012 (F4a modos+playbooks)**: implementa ModeResolver, PlaybookRunner, ModeContext y los 3 modos/playbooks MVP definidos conceptualmente aqui.
- **spec 013 (F4a frontend)**: el frontend de chat y seleccion de modo depende de la jerarquia Channel->Mode.
