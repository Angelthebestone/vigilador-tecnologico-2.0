# Implementation Plan: Jerarquia Conceptual Channel-Mode-Agent-Playbook-Skill-Capability

**Feature ID**: 010-jerarquia-agent-mode-skill
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El spec 009 crea la estructura de carpetas `enterprise/` vacia y el ToolRegistry. Sin embargo, no existe todavia una definicion formal implementada de la jerarquia de 6 niveles (Channel, Mode, Agent, Playbook, Skill, Capability/Tool) que el 3.0 necesita como marco de referencia. Los specs posteriores (011 tools, 012 modos+playbooks, 013 frontend) necesitan:

1. Modelos de datos que representen cada nivel de la jerarquia con sus reglas de composicion.
2. Contratos (Protocol classes) que definan como se conectan los niveles entre si.
3. Un loader de YAML que permita agregar playbooks/modos/skills sin tocar codigo (OCP).
4. Validacion de que la estructura de carpetas y las capas respetan la jerarquia.

Hoy no existe nada de esto. El codigo del 2.0 no tiene concepto de Mode, Playbook declarativo ni Skill atomica.

## Approach

Implementar los modelos de dominio y contratos (Protocol classes) que formalizan la jerarquia de 6 niveles, un loader YAML generico para configuracion declarativa, y las validaciones de capa. Todo vive en `enterprise/` y `domain/` sin tocar el 2.0. Se crean los YAMLs placeholder en `config/` que specs posteriores poblaran con contenido real. El playbook `technology-watch` se declara como YAML que referencia BranchCoordinator sin modificarlo.

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje | Python 3.11+ (mismo que 2.0) |
| Modelos de jerarquia | Dataclasses frozen en `domain/` para entidades puras (Mode, Playbook, Skill, Capability) |
| Contratos entre niveles | Protocol classes en `domain/ports/` (ModeResolutionStrategy, PlaybookExecutor, SkillExecutor) |
| Configuracion declarativa | YAML en `config/{modes,playbooks,skills}/` cargado por loader generico |
| Loader YAML | `enterprise/config_loader.py` con validacion Pydantic |
| Filtrado Mode->Tools | ModeContext frozen snapshot con allowlists; ToolRegistry recibe filtro |
| Playbook technology-watch | YAML que declara executor=BranchCoordinator; cero CrewAI |
| Validacion de capas | Extension de `scripts/check-layer-imports.py` para cubrir `enterprise/` |
| Archivos | Todos <= 400 LOC |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Cero breaking changes al 2.0 (constitucion #5) | BranchCoordinator, 6 agentes, API v2 intactos. Tests 2.0 pasan al 100%. |
| Spec 009 debe completarse primero | La estructura `enterprise/` vacia y ToolRegistry ya existen cuando este spec arranca. |
| MVP solo 3 modos + 3 playbooks (00b) | Se crean YAMLs solo para default, vigilancia-tech, CEO y technology-watch, deep-research, general. Resto es roadmap. |
| Constitucion #2 Simplicidad | Cero abstracciones especulativas. Solo se implementa lo que los FR exigen. |
| CrewAI solo para playbooks nuevos multi-agente | technology-watch usa BranchCoordinator nativo. CrewAI bridge se difiere a spec 012. |

---


## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/domain/mode.py` | Dataclass frozen `Mode` con campos: id, name, soul_overlay_path, company_subset, skills_allowlist, playbooks_allowed, tools_allowlist. |
| `src/vigilancia_multiagente/domain/playbook.py` | Dataclass frozen `PlaybookDefinition` con campos: id, name, executor_type, agents (lista de AgentDeclaration), parallel flag. |
| `src/vigilancia_multiagente/domain/skill.py` | Dataclass frozen `SkillDefinition` con campos: id, name, domain, capabilities_required (lista de capability_ids), preconditions. |
| `src/vigilancia_multiagente/domain/capability.py` | Dataclass frozen `CapabilitySchema` con campos: id, verb, input_schema (dict), output_schema (dict), tool_id. |
| `src/vigilancia_multiagente/domain/mode_context.py` | Dataclass frozen `ModeContext` con SOUL overlay, COMPANY subset, allowlists de skills/playbooks/tools. Inmutable durante sesion. |
| `src/vigilancia_multiagente/domain/ports/mode_resolution_strategy.py` | Protocol `ModeResolutionStrategy` con metodo `resolve(channel, message, session) -> Mode`. |
| `src/vigilancia_multiagente/domain/ports/playbook_executor.py` | Protocol `PlaybookExecutor` con metodo `execute(playbook: PlaybookDefinition, context: ModeContext) -> ExecutionResult`. |
| `src/vigilancia_multiagente/domain/ports/skill_executor.py` | Protocol `SkillExecutor` con metodo `execute(skill: SkillDefinition, inputs: dict) -> SkillResult`. |
| `src/vigilancia_multiagente/enterprise/config_loader.py` | Loader generico YAML con validacion Pydantic. Carga modos, playbooks y skills desde `config/`. |
| `src/vigilancia_multiagente/enterprise/modes/__init__.py` | Marker (ya creado por 009, se confirma existencia). |
| `src/vigilancia_multiagente/enterprise/modes/mode_registry.py` | `ModeRegistry`: carga modos desde `config/modes/`, valida referencias a playbooks existentes, expone `get(mode_id) -> Mode`. |
| `src/vigilancia_multiagente/enterprise/orchestration/playbook_registry.py` | `PlaybookRegistry`: carga playbooks desde `config/playbooks/`, valida skills referenciadas, expone `get(playbook_id) -> PlaybookDefinition`. |
| `src/vigilancia_multiagente/enterprise/orchestration/mode_context_factory.py` | Factory que construye `ModeContext` frozen a partir de un `Mode` resuelto + datos de company + registros de skills/tools. |
| `config/modes/default.yaml` | YAML del modo default MVP con allowlists amplias. |
| `config/modes/vigilancia-tech.yaml` | YAML del modo Vigilancia Tech MVP. Allowlist: playbook technology-watch + tools de investigacion. |
| `config/modes/CEO.yaml` | YAML del modo CEO MVP (reducido). Allowlist: playbooks general + deep-research + tools estrategicos. |
| `config/playbooks/technology-watch.yaml` | YAML declarativo: executor=branch_coordinator, agents=6 ramas del 2.0, parallel=true. |
| `config/playbooks/deep-research.yaml` | YAML placeholder MVP: executor=crewai (implementacion en spec 012), agents=[researcher, synthesizer]. |
| `config/playbooks/general.yaml` | YAML placeholder MVP: executor=single_agent, agents=[general_assistant]. |
| `tests/enterprise/domain/test_hierarchy_models.py` | Tests unitarios de los modelos de dominio: inmutabilidad, validacion de campos, composicion. |
| `tests/enterprise/config/test_config_loader.py` | Tests del loader YAML: carga valida, YAML malformado, referencia rota a playbook/skill. |
| `tests/enterprise/modes/test_mode_registry.py` | Tests de ModeRegistry: carga 3 modos MVP, error si playbook referenciado no existe. |
| `tests/enterprise/orchestration/test_playbook_registry.py` | Tests de PlaybookRegistry: carga 3 playbooks, validacion de skills referenciadas. |
| `tests/enterprise/orchestration/test_mode_context_factory.py` | Tests de ModeContextFactory: snapshot frozen, allowlists correctas, filtrado efectivo. |

### Modified Files

| File | Changes |
|------|---------|
| `scripts/check-layer-imports.py` | Agregar reglas para `enterprise/modes/` no importa de `enterprise/tooling/` directamente; `enterprise/orchestration/` no importa de `infra/`. |
| `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` | Agregar parametro opcional `mode_context: ModeContext` a `discover()` y `list_tools_for_role()` para filtrar por allowlist del Mode. Cambio aditivo, no rompe firma existente. |

---


## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: 8 assumptions explicitas (A-01..A-08) en el spec. Fase 1 valida que la estructura de 009 existe antes de escribir modelos.
  - **Simplicidad Obligatoria**: solo se crean los modelos que los FR exigen (6 niveles, 3 protocols, 1 loader, 2 registries). Cero niveles intermedios especulativos. Cero implementacion de ModeResolver ni PlaybookRunner (eso es spec 012).
  - **Modularidad Primero**: cada nivel de la jerarquia tiene su archivo en `domain/`. Cada registry tiene responsabilidad unica. Loader separado de registries.
  - **Cambios Quirurgicos y Trazables**: 1 archivo del 2.0 modificado (`check-layer-imports.py`, aditivo). 1 archivo del spec 009 extendido (`tool_registry.py`, parametro opcional). Cero cambios a BranchCoordinator, agentes, API.
  - **Entrega Verificable**: cada FR mapea a tests concretos. SC-001..SC-006 del spec son verificables por script o test.
- **Diseno de Software**: SRP (un archivo por entidad de dominio), OCP (nuevos YAMLs sin tocar codigo), DIP (Protocol classes como contratos), ISP (protocols minimos por nivel), CQS (registries solo leen), KISS (dataclasses frozen sin logica de negocio), YAGNI (cero CrewAI bridge aqui).

---


## Phases

### Phase 1 — Validacion de prerequisitos (1 dia)

1. Verificar que spec 009 F0 esta completo: estructura `enterprise/` con subcarpetas existe, `config/{modes,playbooks,skills}/` existe con `.gitkeep`.
2. Crear `config/skills/curated/` y `config/skills/learned/` con `.gitkeep` si no existen (FR-007). Verificar que `config/company/` y `config/mcp/` existen (responsabilidad de spec 009; si faltan, crearlos con `.gitkeep`).
3. Verificar que `ToolRegistry` de spec 009 esta operativo (import sin error).
4. Verificar que `scripts/check-layer-imports.py` pasa sobre el estado actual.
5. Documentar resultado en log de fase (no genera archivo persistente).

**Output**: prerequisitos confirmados, listo para implementar modelos.

### Phase 2 — Modelos de dominio de la jerarquia (2 dias)

1. Crear `domain/capability.py`: dataclass frozen `CapabilitySchema` con id, verb, input_schema, output_schema, tool_id.
2. Crear `domain/skill.py`: dataclass frozen `SkillDefinition` con id, name, domain, capabilities_required, preconditions.
3. Crear `domain/playbook.py`: dataclass frozen `PlaybookDefinition` con id, name, executor_type (Literal["branch_coordinator", "crewai", "single_agent"]), agents (list[AgentDeclaration]), parallel.
4. Crear `domain/mode.py`: dataclass frozen `Mode` con id, name, soul_overlay_path, company_subset_paths, skills_allowlist, playbooks_allowed, tools_allowlist.
5. Crear `domain/mode_context.py`: dataclass frozen `ModeContext` con soul_overlay (str), company_context (dict), skills_allowed (frozenset), playbooks_allowed (frozenset), tools_allowed (frozenset).
6. Tests `tests/enterprise/domain/test_hierarchy_models.py`: inmutabilidad (frozen), validacion de tipos, composicion correcta entre niveles.

**Output**: 5 modelos de dominio + tests verdes. Cero logica de negocio, solo estructura de datos.

### Phase 3 — Contracts (Protocol classes) (1 dia)

1. Crear `domain/ports/mode_resolution_strategy.py`: Protocol con `resolve(channel_id: str, message: str, session_id: str) -> Mode`.
2. Crear `domain/ports/playbook_executor.py`: Protocol con `execute(playbook: PlaybookDefinition, context: ModeContext) -> ExecutionResult`.
3. Crear `domain/ports/skill_executor.py`: Protocol con `execute(skill: SkillDefinition, inputs: dict) -> SkillResult`.
4. Definir `ExecutionResult` y `SkillResult` como dataclasses en sus respectivos archivos de port.

**Output**: 3 Protocol classes que definen los contratos entre niveles. Specs 012 los implementara.

### Phase 4 — Config loader y registries (2-3 dias)

1. Crear `enterprise/config_loader.py` (~200 LOC): funcion `load_yaml_config(path: Path, schema: type[T]) -> T` que carga YAML y valida con Pydantic model. Errores explicitos si YAML malformado o campos faltantes.
2. Crear `enterprise/modes/mode_registry.py` (~150 LOC): `ModeRegistry` con `load_all(config_dir: Path)`, `get(mode_id: str) -> Mode`, `list_available() -> list[Mode]`. Valida que playbooks referenciados existan en `config/playbooks/`.
3. Crear `enterprise/orchestration/playbook_registry.py` (~150 LOC): `PlaybookRegistry` con `load_all(config_dir: Path)`, `get(playbook_id: str) -> PlaybookDefinition`. Valida que el YAML cumpla el schema (campos requeridos, tipos); NO valida la existencia de la implementación del executor (así `executor: crewai` carga sin fallar en MVP).
4. Crear `enterprise/orchestration/mode_context_factory.py` (~100 LOC): `ModeContextFactory.build(mode: Mode, company_data: dict, skill_ids: set, tool_ids: set) -> ModeContext`. Intersecta allowlists del Mode con registros disponibles.

> **Nota (A1/A2)**: La validación de `skills_allowlist` contra un SkillRegistry real está diferida — no existe SkillRegistry en este spec. En MVP, PlaybookRegistry valida schema YAML; ModeContextFactory acepta el `skills_allowlist` del Mode tal cual sin verificar existencia de cada skill.
5. Tests:
   - `tests/enterprise/config/test_config_loader.py`: YAML valido, YAML malformado, schema mismatch.
   - `tests/enterprise/modes/test_mode_registry.py`: carga 3 modos, error si playbook no existe (EC-01).
   - `tests/enterprise/orchestration/test_playbook_registry.py`: carga 3 playbooks, error si skill no existe (EC-02).
   - `tests/enterprise/orchestration/test_mode_context_factory.py`: snapshot frozen, allowlists filtradas.

**Output**: loader + 2 registries + factory + tests verdes.

### Phase 5 — YAMLs declarativos MVP (1 dia)

1. Crear `config/modes/default.yaml`: modo default con allowlists amplias (todas las skills/playbooks/tools disponibles).
2. Crear `config/modes/vigilancia-tech.yaml`: allowlist restringida a playbook technology-watch + tools de investigacion (tavily, exa, jina, brave, openalex, etc.).
3. Crear `config/modes/CEO.yaml`: allowlist a playbooks general + deep-research + tools estrategicos.
4. Crear `config/playbooks/technology-watch.yaml`: executor=branch_coordinator, agents=[avances, comercial, riesgo, pi_normativa, competitivo, oportunidades], parallel=true.
5. Crear `config/playbooks/deep-research.yaml`: executor=crewai, agents=[researcher, synthesizer] (placeholder, implementacion en spec 012).
6. Crear `config/playbooks/general.yaml`: executor=single_agent, agents=[general_assistant].
7. Verificar que ModeRegistry y PlaybookRegistry cargan los 3+3 YAMLs sin error. Nota: PlaybookRegistry valida solo el SCHEMA del YAML (campos requeridos, tipos), no la existencia de la implementación del executor. Así `executor: crewai` en `deep-research.yaml` carga sin fallar en MVP.

**Output**: 6 archivos YAML declarativos + registries los cargan correctamente.

### Phase 6 — Integracion con ToolRegistry y validacion de capas (1-2 dias)

1. Extender `enterprise/tooling/tool_registry.py`: agregar parametro opcional `mode_context: ModeContext | None = None` a `discover()` y `list_tools_for_role()`. Si se provee, filtrar resultados por `mode_context.tools_allowed`. Cambio aditivo backward-compatible.
2. Extender `scripts/check-layer-imports.py`: agregar reglas que validen que `enterprise/modes/` no importa directamente de `enterprise/tooling/` ni de `infra/`; que `enterprise/orchestration/` no importa de `infra/`.
3. Correr `scripts/check-layer-imports.py` sobre todo el codigo y verificar cero violaciones.
4. Test de integracion: crear Mode con tools_allowlist restrictiva, verificar que `ToolRegistry.discover()` con ese ModeContext excluye tools no permitidas (SC-004 del spec).

**Output**: filtrado Mode->Tools operativo + validacion de capas verde.

### Phase 7 — Cierre y verificacion (1 dia)

1. Correr `pytest` completo: tests del 2.0 + tests nuevos de este spec. Cero regresiones.
2. Correr `scripts/check-layer-imports.py` sin violaciones (SC-005).
3. Verificar que ningun archivo nuevo excede 400 LOC (SC-006).
4. Verificar SC-001..SC-006 del spec con evidencia:
   - SC-001: listar subcarpetas de `enterprise/` y confirmar 13 con mapeo a concerns.
   - SC-002: tests E2E del 2.0 pasan (BranchCoordinator intacto).
   - SC-003: test de integracion que registra playbook dummy YAML y lo carga sin tocar Python.
   - SC-004: test unitario de filtrado Mode sobre tools.
   - SC-005: script de capas pasa.
   - SC-006: script de conteo LOC confirma <= 400.

**Output**: spec 010 completado. Modelos, contratos, registries y YAMLs listos para que spec 012 implemente ModeResolver y PlaybookRunner.

---


## Rollout Strategy

**Estrategia**: incremental por fase. Cada fase produce artefactos verificables y tests deben pasar antes de avanzar.

- **Backward compatibility**: el 2.0 sigue corriendo sin cambios. Los modelos de dominio nuevos viven en `domain/` sin afectar imports existentes. Los YAMLs en `config/` son archivos nuevos que no interfieren con nada.
- **Feature flags**: cero necesarios. Los registries solo se instancian desde codigo nuevo bajo `enterprise/`.
- **Coexistencia con 2.0**: BranchCoordinator se referencia desde el YAML de `technology-watch` pero no se modifica. El playbook YAML es declarativo; la invocacion real la implementa spec 012.
- **Rollback**: si algo falla, se eliminan los archivos nuevos. Cero migraciones de DB en este spec. El unico archivo modificado del ecosistema existente es `check-layer-imports.py` (cambio aditivo revertible) y `tool_registry.py` (parametro opcional, backward-compatible).

---

## Success Criteria

- **SC-001**: La estructura `enterprise/` contiene las 13 subcarpetas documentadas, cada una mapeando a un concern de la jerarquia. Verificable por inspeccion de directorio.
- **SC-002**: Tests E2E del 2.0 (BranchCoordinator + 6 agentes) pasan al 100% sin modificaciones. Verificable por `pytest tests/` excluyendo suite enterprise.
- **SC-003**: Agregar un playbook YAML nuevo en `config/playbooks/` es reconocido por `PlaybookRegistry` sin modificar codigo Python. Verificable por test de integracion.
- **SC-004**: Filtrado de Mode sobre tools es efectivo: `ToolRegistry.discover()` con ModeContext restrictivo excluye tools no permitidas. Verificable por test unitario.
- **SC-005**: `scripts/check-layer-imports.py` pasa sin violaciones sobre `enterprise/`. Verificable por ejecucion del script.
- **SC-006**: Cero archivos bajo `enterprise/` exceden 400 LOC. Verificable por script de conteo.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Justification**:
  - **Pensar Antes de Codificar**: Phase 1 valida prerequisitos antes de escribir codigo. 8 assumptions del spec documentadas. Modelos de dominio diseñados antes de implementar logica.
  - **Simplicidad Obligatoria**: 5 dataclasses frozen + 3 protocols + 1 loader + 2 registries + 1 factory = 12 archivos funcionales nuevos. Cada uno con razon documentada en FR. Cero abstracciones especulativas (no se implementa ModeResolver, PlaybookRunner ni CrewAI bridge).
  - **Modularidad Primero**: cada entidad de la jerarquia en su propio archivo. Registries separados por concern (modes vs playbooks). Factory aislada de registries.
  - **Cambios Quirurgicos y Trazables**: 2 archivos existentes modificados en modo aditivo (parametro opcional en tool_registry, reglas nuevas en check-layer-imports). Cero borrado, cero renombre, cero cambio al 2.0.
  - **Entrega Verificable**: 6 success criteria con metodo de verificacion explicito. Tests por fase. Cada FR del spec tiene cobertura directa en al menos una fase.
  - **Diseno de Software**: SRP (archivo por entidad), OCP (YAMLs sin tocar runners), DIP (Protocol classes), ISP (protocols minimos), CQS (registries solo leen config), KISS (dataclasses sin logica), YAGNI (cero implementacion de runners).
