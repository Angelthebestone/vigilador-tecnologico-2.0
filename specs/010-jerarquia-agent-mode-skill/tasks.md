# Tasks: Jerarquia Conceptual Channel-Mode-Agent-Playbook-Skill-Capability

**Input**: `specs/010-jerarquia-agent-mode-skill/spec.md`, `specs/010-jerarquia-agent-mode-skill/plan.md`
**Feature**: Modelo conceptual de la jerarquia de 6 niveles (Channel, Mode, Agent, Playbook, Skill, Capability/Tool), modelos de dominio frozen, Protocol classes de contratos entre niveles, config loader YAML generico, registries de modos y playbooks, YAMLs declarativos MVP, integracion de filtrado Mode->Tools en ToolRegistry, y validacion de capas.

**User Stories del spec**:
- **US1 (P1)**: Arquitecto del sistema define formalmente la jerarquia con reglas de composicion claras y mapeada a la estructura de carpetas, para que specs posteriores declaren sin ambiguedad donde vive cada componente.
  *Cubre los 17 FRs, 6 acceptance scenarios, 4 edge cases y 6 success criteria.*

**Testing strategy**: tests intercalados antes de implementacion por componente (test-before-implementation). Cada fase produce artefactos verificables con tests verdes antes de avanzar. SC-002 exige cero regresiones en tests del 2.0; SC-003..SC-006 exigen tests de integracion y scripts de validacion.

---

## Phase 1: Validacion de prerequisitos

Cero codigo de producto. Solo verificacion de que spec 009 dejo la base lista.

- [ ] T001 [P] Validar estructura enterprise existente: confirmar que `src/vigilancia_multiagente/enterprise/` contiene las 13 subcarpetas con `__init__.py` (orchestration, modes, skills_marketplace, intelligence, triggers, auth, governance, memory, observability, ingestion, tooling, dreaming, mcp)
- [ ] T002 [P] Validar estructura config existente: confirmar que `config/modes/`, `config/playbooks/`, `config/skills/` existen con `.gitkeep` o `README.md`
- [ ] T002b [P] Crear directorios `config/skills/curated/` y `config/skills/learned/` con `.gitkeep` si no existen (FR-007). Verificar/declarar que `config/company/` y `config/mcp/` existen (responsabilidad de spec 009; si faltan, crearlos con `.gitkeep`).
- [ ] T003 [P] Validar ToolRegistry operativo: ejecutar `python -c "from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry"` sin error de import
- [ ] T004 [P] Validar layer imports baseline: ejecutar `python scripts/check-layer-imports.py` sin violaciones sobre el estado actual
- [ ] T005 Validar tests del 2.0 pasan: ejecutar `pytest tests/` (excluyendo suite enterprise) al 100%

**Independent Test Criteria for Phase 1**: las 13 subcarpetas de `enterprise/` existen; `config/{modes,playbooks,skills}/` existen; ToolRegistry importable; `check-layer-imports.py` sin violaciones; tests del 2.0 al 100%.

---

## Phase 2: Modelos de dominio de la jerarquia

Dataclasses frozen que representan los 6 niveles. Cero logica de negocio, solo estructura de datos inmutable.

- [ ] T006 [P] [US1] Crear test `tests/enterprise/domain/test_hierarchy_models.py`: tests de inmutabilidad (frozen), validacion de campos requeridos, composicion entre niveles (CapabilitySchema, SkillDefinition, PlaybookDefinition, Mode, ModeContext) en `tests/enterprise/domain/test_hierarchy_models.py`
- [ ] T007 [US1] Crear dataclass frozen `CapabilitySchema` (id, verb, input_schema, output_schema, tool_id) en `src/vigilancia_multiagente/domain/capability.py`
- [ ] T008 [US1] Crear dataclass frozen `SkillDefinition` (id, name, domain, capabilities_required: list[str], preconditions: list[str]) en `src/vigilancia_multiagente/domain/skill.py`
- [ ] T009 [US1] Crear dataclass frozen `PlaybookDefinition` con `AgentDeclaration` (AgentDeclaration campos: id, role, skills_allowed) (PlaybookDefinition campos: id, name, executor_type: Literal["branch_coordinator","crewai","single_agent"], agents: list[AgentDeclaration], parallel: bool) en `src/vigilancia_multiagente/domain/playbook.py`
- [ ] T010 [US1] Crear dataclass frozen `Mode` (id, name, soul_overlay_path, company_subset_paths: list[str], skills_allowlist: frozenset[str], playbooks_allowed: frozenset[str], tools_allowlist: frozenset[str]) en `src/vigilancia_multiagente/domain/mode.py`
- [ ] T011 [US1] Crear dataclass frozen `ModeContext` (soul_overlay: str, company_context: dict, skills_allowed: frozenset[str], playbooks_allowed: frozenset[str], tools_allowed: frozenset[str]) en `src/vigilancia_multiagente/domain/mode_context.py`
- [ ] T012 [US1] Hacer T006 verde: todos los tests de inmutabilidad y composicion pasan

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/domain/test_hierarchy_models.py` verde; todos los modelos son frozen (asignacion post-init lanza FrozenInstanceError); tipos correctos verificados por basedpyright.

---

## Phase 3: Contracts (Protocol classes)

Protocolos que definen contratos entre niveles. Specs posteriores (012) los implementaran.

- [ ] T013 [P] [US1] Crear Protocol `ModeResolutionStrategy` con metodo `resolve(channel_id: str, message: str, session_id: str) -> Mode` en `src/vigilancia_multiagente/domain/ports/mode_resolution_strategy.py`
- [ ] T014 [P] [US1] Crear Protocol `PlaybookExecutor` con metodo `execute(playbook: PlaybookDefinition, context: ModeContext) -> ExecutionResult` y dataclass `ExecutionResult` en `src/vigilancia_multiagente/domain/ports/playbook_executor.py`
- [ ] T015 [P] [US1] Crear Protocol `SkillExecutor` con metodo `execute(skill: SkillDefinition, inputs: dict) -> SkillResult` y dataclass `SkillResult` en `src/vigilancia_multiagente/domain/ports/skill_executor.py`

**Independent Test Criteria for Phase 3**: los 3 Protocol classes importan sin error; basedpyright sin errores nuevos; una clase dummy que implemente cada Protocol compila correctamente.

---

## Phase 4: Config loader y registries

Loader YAML generico + ModeRegistry + PlaybookRegistry + ModeContextFactory. Cada uno con tests previos.

### F4.1 -- Config loader YAML

- [ ] T016 [US1] Crear test `tests/enterprise/config/test_config_loader.py`: tests de carga YAML valido, YAML malformado lanza error explicito, schema mismatch lanza error con campo faltante indicado en `tests/enterprise/config/test_config_loader.py`
- [ ] T017 [US1] Implementar `load_yaml_config(path: Path, schema: type[T]) -> T` con validacion Pydantic (~200 LOC max) en `src/vigilancia_multiagente/enterprise/config_loader.py`
- [ ] T018 [US1] Hacer T016 verde

### F4.2 -- ModeRegistry

- [ ] T019 [US1] Crear test `tests/enterprise/modes/test_mode_registry.py`: tests de carga de 3 modos MVP, error explicito si playbook referenciado no existe (EC-01), `get(mode_id)` retorna Mode correcto, `list_available()` retorna 3 en `tests/enterprise/modes/test_mode_registry.py`
- [ ] T020 [US1] Implementar `ModeRegistry` con `load_all(config_dir)`, `get(mode_id) -> Mode`, `list_available() -> list[Mode]` (~150 LOC max) en `src/vigilancia_multiagente/enterprise/modes/mode_registry.py`
- [ ] T021 [US1] Hacer T019 verde

### F4.3 -- PlaybookRegistry

> **Nota MVP (A1/A2)**: La validación de `skills_allowlist` contra un SkillRegistry está diferida — no existe SkillRegistry en este spec. En MVP, PlaybookRegistry valida únicamente que el YAML del playbook tenga estructura correcta (schema) y que los campos requeridos estén presentes. NO valida la existencia real de skills referenciadas en runtime; esa validación se implementará cuando exista SkillRegistry (spec posterior).

- [ ] T022 [US1] Crear test `tests/enterprise/orchestration/test_playbook_registry.py`: tests de carga de 3 playbooks MVP, error explicito si skill referenciada no existe (EC-02), `get(playbook_id)` retorna PlaybookDefinition correcta en `tests/enterprise/orchestration/test_playbook_registry.py`
- [ ] T023 [US1] Implementar `PlaybookRegistry` con `load_all(config_dir)`, `get(playbook_id) -> PlaybookDefinition` (~150 LOC max) en `src/vigilancia_multiagente/enterprise/orchestration/playbook_registry.py`
- [ ] T024 [US1] Hacer T022 verde

### F4.4 -- ModeContextFactory

- [ ] T025 [US1] Crear test `tests/enterprise/orchestration/test_mode_context_factory.py`: tests de snapshot frozen, allowlists intersectadas correctamente con registros disponibles, ModeContext inmutable post-creacion en `tests/enterprise/orchestration/test_mode_context_factory.py`
- [ ] T026 [US1] Implementar `ModeContextFactory.build(mode, company_data, skill_ids, tool_ids) -> ModeContext` (~100 LOC max) en `src/vigilancia_multiagente/enterprise/orchestration/mode_context_factory.py`
- [ ] T027 [US1] Hacer T025 verde

**Independent Test Criteria for Phase 4**: `pytest tests/enterprise/config/ tests/enterprise/modes/ tests/enterprise/orchestration/` verde; config loader rechaza YAML invalido con mensaje claro; ModeRegistry carga 3 modos; PlaybookRegistry carga 3 playbooks; ModeContextFactory produce snapshot frozen.

---

## Phase 5: YAMLs declarativos MVP

Archivos de configuracion para los 3 modos y 3 playbooks del MVP.

- [ ] T028 [P] [US1] Crear YAML del modo default con allowlists amplias (todas las skills/playbooks/tools) en `config/modes/default.yaml`
- [ ] T029 [P] [US1] Crear YAML del modo vigilancia-tech con allowlist restringida a playbook technology-watch + tools de investigacion en `config/modes/vigilancia-tech.yaml`
- [ ] T030 [P] [US1] Crear YAML del modo CEO con allowlist a playbooks general + deep-research + tools estrategicos en `config/modes/CEO.yaml`
- [ ] T031 [P] [US1] Crear YAML del playbook technology-watch: executor=branch_coordinator, agents=[avances, comercial, riesgo, pi_normativa, competitivo, oportunidades], parallel=true en `config/playbooks/technology-watch.yaml`
- [ ] T032 [P] [US1] Crear YAML del playbook deep-research: executor=crewai, agents=[researcher, synthesizer] (placeholder para spec 012) en `config/playbooks/deep-research.yaml`
- [ ] T033 [P] [US1] Crear YAML del playbook general: executor=single_agent, agents=[general_assistant] en `config/playbooks/general.yaml`
- [ ] T034 [US1] Verificar que ModeRegistry y PlaybookRegistry cargan los 6 YAMLs sin error ejecutando tests de T019 y T022. Nota: PlaybookRegistry valida solo el SCHEMA del YAML (campos requeridos, tipos), no la existencia de la implementación del executor (así `executor: crewai` en deep-research.yaml carga sin fallar en MVP).

**Independent Test Criteria for Phase 5**: los 6 archivos YAML existen con estructura valida; `ModeRegistry.load_all()` carga 3 modos sin error; `PlaybookRegistry.load_all()` carga 3 playbooks sin error; tests de Phase 4 siguen verdes.

---

## Phase 6: Integracion con ToolRegistry y validacion de capas

Filtrado Mode->Tools en ToolRegistry + extension del script de validacion de capas.

- [ ] T035 [US1] Crear test de integracion: Mode con tools_allowlist restrictiva + `ToolRegistry.discover()` con ModeContext excluye tools no permitidas (SC-004) en `tests/enterprise/tooling/test_tool_registry_mode_filter.py`
- [ ] T036 [US1] Extender `discover()` y `list_tools_for_role()` con parametro opcional `mode_context: ModeContext | None = None`; si se provee, filtrar resultados por `mode_context.tools_allowed`. Cambio aditivo backward-compatible en `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`
- [ ] T037 [US1] Hacer T035 verde
- [ ] T038 [US1] Extender reglas de validacion: `enterprise/modes/` no importa de `enterprise/tooling/` ni de `infra/`; `enterprise/orchestration/` no importa de `infra/` en `scripts/check-layer-imports.py`
- [ ] T039 [US1] Ejecutar `python scripts/check-layer-imports.py` sobre todo el codigo y verificar cero violaciones (SC-005)
- [ ] T040 [US1] Crear test de integracion: agregar playbook YAML dummy en `config/playbooks/` y verificar que PlaybookRegistry lo reconoce sin modificar codigo Python (SC-003) en `tests/enterprise/orchestration/test_playbook_ocp.py`

**Independent Test Criteria for Phase 6**: `ToolRegistry.discover()` con ModeContext restrictivo excluye tools no permitidas; `check-layer-imports.py` pasa sin violaciones; playbook YAML nuevo se carga sin tocar Python.

---

## Phase 7: Cierre y verificacion

Validacion final de todos los success criteria. Cero regresiones.

- [ ] T041 [P] Ejecutar `pytest` completo (tests del 2.0 + tests nuevos de este spec) y verificar cero regresiones (SC-002)
- [ ] T042 [P] Ejecutar `python scripts/check-layer-imports.py` final sin violaciones (SC-005)
- [ ] T043 [P] Verificar que ningun archivo nuevo bajo `enterprise/` excede 400 LOC mediante script de conteo (SC-006)
- [ ] T044 [P] Verificar SC-001: listar subcarpetas de `enterprise/` y confirmar 13 con mapeo a concerns de la jerarquia
- [ ] T045 Verificar SC-003: test de integracion T040 pasa (playbook dummy YAML reconocido sin tocar Python)
- [ ] T046 Verificar SC-004: test de integracion T035 pasa (filtrado Mode sobre tools efectivo)
- [ ] T047 Ejecutar `basedpyright` sobre archivos nuevos y verificar cero errores nuevos

**Independent Test Criteria for Phase 7**: todos los SC-001..SC-006 verificados con evidencia; `pytest` completo verde; `check-layer-imports.py` verde; cero archivos > 400 LOC; basedpyright sin errores nuevos.

---

## Dependencies

- **Phase 1 (Prerequisitos)** must complete before **Phase 2 (Modelos de dominio)**.
- **Phase 2 (Modelos de dominio)** must complete before **Phase 3 (Contracts)**.
- **Phase 3 (Contracts)** must complete before **Phase 4 (Config loader y registries)**.
- **Phase 4 (Config loader y registries)** must complete before **Phase 5 (YAMLs)**.
- **Phase 5 (YAMLs)** must complete before **Phase 6 (Integracion)**.
- **Phase 6 (Integracion)** must complete before **Phase 7 (Cierre)**.
- Dentro de **Phase 2**: T006 (test) se escribe primero; T007..T011 son paralelos entre si (archivos distintos); T012 cierra la fase.
- Dentro de **Phase 3**: T013, T014, T015 son independientes (archivos distintos sin dependencia).
- Dentro de **Phase 4**: F4.1 (loader) must complete before F4.2, F4.3, F4.4. F4.2 y F4.3 son independientes entre si. F4.4 depende de F4.2 (necesita Mode).
- Dentro de **Phase 5**: T028..T033 son independientes (archivos distintos). T034 depende de todos los anteriores.
- Dentro de **Phase 6**: T035 (test) antes de T036 (implementacion) antes de T037 (verde). T038 antes de T039. T040 independiente de T035..T039.
- **T017** (config_loader) bloquea T020 (ModeRegistry) y T023 (PlaybookRegistry) porque ambos lo usan.
- **T020** (ModeRegistry) bloquea T034 (verificacion de carga de YAMLs).
- **T023** (PlaybookRegistry) bloquea T034 y T040.
- **T011** (ModeContext) bloquea T026 (ModeContextFactory) y T036 (filtrado en ToolRegistry).

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run **T001, T002, T003, T004** en paralelo (validaciones independientes sobre archivos/scripts distintos).

### Phase 2 Parallel Block

- Run **T007, T008, T009, T010, T011** en paralelo tras escribir T006 (test). Son archivos distintos sin dependencia entre si.

### Phase 3 Parallel Block

- Run **T013, T014, T015** en paralelo (3 Protocol classes en archivos distintos).

### Phase 4 Parallel Block

- Tras T017 (loader) verde, run **T019+T020 (ModeRegistry)** y **T022+T023 (PlaybookRegistry)** en paralelo (registries independientes).

### Phase 5 Parallel Block

- Run **T028, T029, T030, T031, T032, T033** en paralelo (6 archivos YAML independientes).

### Phase 6 Parallel Block

- Run **T035** y **T038** en paralelo (test de filtrado y extension de check-layer-imports son independientes).
- Run **T040** en paralelo con T036+T037 (test OCP no depende del filtrado Mode->Tools).

### Phase 7 Parallel Block

- Run **T041, T042, T043, T044, T047** en paralelo (validaciones independientes sobre distintos aspectos).

---

## Implementation Strategy

1. **Cerrar Phase 1 (Prerequisitos) primero**: confirmar que spec 009 dejo la base lista. Si falta algo, resolver antes de avanzar. Esto es go/no-go.
2. **Phase 2 + Phase 3 (Modelos + Contracts)**: son la base conceptual. Dataclasses frozen + Protocol classes. Rapido de implementar, alto valor de referencia para specs posteriores.
3. **Phase 4 (Loader + Registries)**: el config_loader es el componente central; una vez verde, los registries se implementan en paralelo. Test-before-implementation estricto.
4. **Phase 5 (YAMLs)**: archivos declarativos que validan que el loader y registries funcionan con datos reales MVP. Paralelizable al 100%.
5. **Phase 6 (Integracion)**: unico punto donde se toca un archivo existente del spec 009 (tool_registry.py, cambio aditivo). Validacion de capas cierra la integridad arquitectonica.
6. **Phase 7 (Cierre)**: gate final. Nada se considera entregado hasta que todos los SC pasen y cero regresiones en el 2.0.
7. **Punto de no retorno**: tras Phase 5, los YAMLs son la interfaz publica que spec 012 consumira. Cambios a su schema despues de Phase 5 impactan specs descendientes.
8. **MVP scope estricto**: este spec NO implementa ModeResolver, PlaybookRunner ni CrewAI bridge. Solo define modelos, contratos, loader y registries. La logica de ejecucion vive en spec 012.

---

## Traza FR/SC

| Tarea(s) | FR cubiertos | SC cubiertos |
|-----------|-------------|-------------|
| T007-T011 | FR-001, FR-002, FR-003, FR-015 | -- |
| T013-T015 | FR-016 (contrato, contract-only — implementación diferida a spec 012), FR-004 (contrato) | -- |
| T017 | FR-005 (OCP via YAML) | -- |
| T020 | FR-003, FR-005, FR-006 | SC-001 |
| T023 | FR-004, FR-005, FR-006 | SC-003 |
| T026 | FR-015 | SC-004 |
| T028-T030 | FR-003, FR-007 | SC-001 |
| T031 | FR-009, FR-010, FR-013 | SC-002 |
| T032-T033 | FR-004, FR-007, FR-013 | -- |
| T036 | FR-017 | SC-004 |
| T038-T039 | FR-008 | SC-005 |
| T040 | FR-005 | SC-003 |
| T041 | FR-011 | SC-002 |
| T043 | FR-014 | SC-006 |
| T007-T011 | FR-012 (constraint: Python 3.11+ puro en enterprise/) | -- |

---

## Format Validation

Todas las tareas T001..T047 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001..T047).
- Marcador `[P]` solo en tareas paralelizables (diferentes archivos sin dependencias incompletas).
- Label `[US1]` en tareas de Phase 2..Phase 6 (user story unica); sin label en Phase 1 (prerequisitos) ni Phase 7 (cierre).
- Descripcion con accion + path concreto del archivo.

**Total task count**: 47 tareas.
**Task count per phase**:
- Phase 1 (Prerequisitos): 5
- Phase 2 (Modelos de dominio): 7
- Phase 3 (Contracts): 3
- Phase 4 (Config loader y registries): 12
- Phase 5 (YAMLs declarativos): 7
- Phase 6 (Integracion): 6
- Phase 7 (Cierre): 7

**MVP vs Roadmap**: este spec entero es MVP. Los niveles Channel (Telegram/WhatsApp), Modes adicionales (CFO, Legal, Marketing...), Playbooks adicionales (decision-debate, market-research...) y Skills learned/marketplace son roadmap post-MVP documentado en el spec pero sin tareas aqui.
