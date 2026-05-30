# Tasks: Mode Router, Catalogo de Modos y company_geo

**Input**: `specs/011-mode-router-catalogo-geo/spec.md`, `specs/011-mode-router-catalogo-geo/plan.md`
**Feature**: ModeLoader + ModeResolver + catalogo MVP (3 modos) + integracion ToolRegistry + company_geo. Componentes de modos del Vigilador 3.0 que determinan personalidad, tools, playbooks y contexto geografico por sesion.

**User Stories del spec**:
- **US1 (P1)**: Usuario activa un modo especifico para que el sistema adapte personalidad, tools y contexto geografico a su necesidad actual.
  *Cubre los 7 acceptance scenarios, 5 edge cases y los 23 FRs.*

**Testing strategy**: test-before-implementation por componente. Cada fase de implementacion tiene su bateria de tests que debe pasar antes de avanzar. SC-001..SC-007 verificados explicitamente en Phase 7.

---

## Phase 1: Validacion de precondiciones

Cero codigo de producto. Solo verificacion de dependencias de spec 009.

- [ ] T001 Verificar que `config/modes/` existe como directorio (creado en spec 009 T006) y documentar resultado en `docs/011-preconditions.md`
- [ ] T002 [P] Verificar que `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` existe y expone metodo de listado de tools (dependencia spec 009 T025)
- [ ] T003 [P] Verificar que tabla `company_profile` (migracion spec 009 T013) contiene campos `country`, `department`, `municipality`, `timezone`
- [ ] T004 [P] Verificar que `config/playbooks/` existe como directorio (creado en spec 009 T006) para validacion de referencias cruzadas
- [ ] T005 Documentar gaps encontrados (si los hay) como blockers en `docs/011-preconditions.md` antes de continuar

**Independent Test Criteria for Phase 1**: `docs/011-preconditions.md` confirma las 4 precondiciones satisfechas o documenta blockers explicitos. Cero codigo nuevo producido.

---

## Phase 2: Schema de Mode y modelos

Dataclasses que definen la estructura de un Mode. Base para todo lo demas.

- [ ] T006 Crear `src/vigilancia_multiagente/enterprise/modes/__init__.py` (marker del subpaquete)
- [ ] T007 [US1] Test `tests/enterprise/modes/test_mode_schema.py`: 6 tests (YAML valido con todos los campos se parsea; YAML sin `id` falla con error explicito; YAML con `company_geo` sin `country` falla FR-008; YAML con `status: roadmap` se parsea; campos opcionales ausentes no causan error; `tools.domains` como lista de strings se valida correctamente FR-004)
- [ ] T008 [US1] Implementar `src/vigilancia_multiagente/enterprise/modes/mode_schema.py` (~200 LOC): dataclasses `CompanyGeo`, `SoulOverlay`, `CompanySubset`, `SkillsConfig`, `PlaybooksConfig`, `ToolsConfig`, `ModeSettings`, `ModeConfig` con campos obligatorios/opcionales segun FR-001/FR-002/FR-003. Funcion `parse_mode_yaml(path: Path) -> ModeConfig`. Hacer T007 verde

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/modes/test_mode_schema.py` verde; `basedpyright` sin errores nuevos en `mode_schema.py`. FR-001, FR-002, FR-003, FR-004 cubiertos.

---

## Phase 3: ModeRegistry y ModeLoader

Carga, validacion y registro de modos desde YAML al arranque.

- [ ] T009 [US1] Test `tests/enterprise/modes/test_mode_loader.py`: 8 tests (3 modos validos se cargan; modo `status: roadmap` no aparece en registry FR-023; id duplicado rechaza segundo con log FR-006; playbook inexistente rechaza modo FR-007; company_geo sin country rechaza FR-008; fallo aislado no afecta otros FR-009; carga 3 modos MVP en < 2 s SC-001; directorio vacio retorna registry vacio)
- [ ] T010 [US1] Implementar `src/vigilancia_multiagente/enterprise/modes/mode_registry.py` (~80 LOC): clase `ModeRegistry` con `_modes: dict[str, ModeConfig]`, metodos `register(mode)`, `get(id) -> ModeConfig | None`, `list_available() -> list[ModeConfig]`, `exists(id) -> bool`. Rechaza duplicados con error explicito (FR-006)
- [ ] T011 [US1] Implementar `src/vigilancia_multiagente/enterprise/modes/mode_loader.py` (~250 LOC): clase `ModeLoader` con `load_all() -> ModeRegistry`. Lee `*.yaml` de `config/modes/`, valida schema via `parse_mode_yaml()`, valida referencias cruzadas (playbooks en `config/playbooks/`), registra validos. Modos `status: roadmap` no se registran. Errores con contexto (ruta, campo, referencia). Sin try/except defensivos. Hacer T009 verde

**Independent Test Criteria for Phase 3**: `pytest tests/enterprise/modes/test_mode_loader.py` verde; ModeLoader rechaza invalidos sin afectar validos; SC-001 verificado en test. FR-005..FR-009, FR-023 cubiertos.

---

## Phase 4: ModeResolver

Componente query-pura que resuelve modo activo por sesion.

- [ ] T012 [US1] Test `tests/enterprise/modes/test_mode_resolver.py`: 6 tests (activacion explicita de modo existente funciona FR-010; modo inexistente falla con lista de disponibles FR-012; sesion sin modo recibe `default` FR-011; cambio mid-sesion descarta anterior y activa nuevo FR-013; `get_active()` retorna modo correcto FR-014; resolucion en < 500 ms SC-002)
- [ ] T013 [US1] Implementar `src/vigilancia_multiagente/enterprise/modes/mode_resolver.py` (~150 LOC): clase `ModeResolver` con `activate(session_id, mode_id) -> ModeConfig`, `get_active(session_id) -> ModeConfig`, `change_mode(session_id, new_mode_id) -> ModeConfig`. Almacenamiento en memoria `_active_modes: dict[str, ModeConfig]`. CQS: `activate()` y `change_mode()` son COMMANDS (mutan `_active_modes`) que retornan ModeConfig como excepcion pragmatica; `get_active()` es QUERY pura. La reconstruccion de contexto de sesion es responsabilidad del orquestador (spec 012). Hacer T012 verde

**Independent Test Criteria for Phase 4**: `pytest tests/enterprise/modes/test_mode_resolver.py` verde; SC-002 verificado. FR-010..FR-014 cubiertos.

---

## Phase 5: Filtrado por Mode en ToolRegistry

Integracion entre modo activo y ToolRegistry para restringir tools por dominios/exclusiones.

- [ ] T014 [US1] Test `tests/enterprise/modes/test_mode_tool_filter.py`: 5 tests (modo con dominios `[search, web]` filtra correctamente FR-015; tool en `excluded` no aparece aunque dominio permitido FR-016; solicitud de tool excluida retorna error explicito FR-017; modo sin campo `tools` retorna todas las tools; 100% escenarios filtran correctamente SC-003)
- [ ] T015 [US1] Implementar `src/vigilancia_multiagente/enterprise/modes/mode_tool_filter.py` (~120 LOC): clase `ModeToolFilter` con `filter_tools(mode, tool_registry) -> list[ToolCard]` y `check_tool_allowed(mode, tool_name, tool_registry) -> bool`. Filtra por `mode.tools.domains`, excluye por `mode.tools.excluded`, error explicito si tool no permitida. Hacer T014 verde
- [ ] T016 [US1] Verificar que `ModeToolFilter` filtra correctamente usando la API publica de `ToolRegistry` (metodo `list_tools_for_role`) y `ToolCard.domains`, sin modificar `tool_registry.py`. El modulo `tooling` NO depende de `modes` (DIP, Bajo Acoplamiento). Composicion se realiza en el wiring (`dependencies.py`)

**Independent Test Criteria for Phase 5**: `pytest tests/enterprise/modes/test_mode_tool_filter.py` verde; SC-003 verificado; `tool_registry.py` no modificado (DIP). FR-015..FR-017 cubiertos.

**Limitacion conocida MVP**: los dominios `analytics` y `productivity` pueden no tener tools registradas en MVP; el filtrado retorna subconjunto vacio para esos dominios (comportamiento esperado, no error).

---

## Phase 6: Catalogo YAML de modos MVP y roadmap

Archivos YAML de configuracion: 3 modos MVP operativos + 5 modos roadmap documentados + placeholders de playbooks.

- [ ] T017 [P] [US1] Crear `config/modes/default.yaml`: `id: default`, `display_name: "Asistente General"`, `version: "1.0.0"`, `tools.domains: [search, web, documents]`, `playbooks.default: general`, `playbooks.allowed: [general]` (FR-021)
- [ ] T018 [P] [US1] Crear `config/modes/vigilancia-tech.yaml`: `id: vigilancia-tech`, `display_name: "Vigilancia Tecnologica"`, `version: "1.0.0"`, `tools.domains: [search, research, web, analytics]`, `playbooks.default: technology-watch`, `playbooks.allowed: [technology-watch]`, `soul_overlay.tone` analitico/tecnico. Nota compatibilidad 2.0 en description (FR-021, FR-022)
- [ ] T019 [P] [US1] Crear `config/modes/ceo.yaml`: `id: ceo`, `display_name: "Director Ejecutivo"`, `version: "1.0.0"`, `tools.domains: [search, research, productivity]`, `playbooks.default: general`, `playbooks.allowed: [decision-debate, deep-research, general]`, `soul_overlay.tone` estrategico/decisivo (FR-021)
- [ ] T020 [P] [US1] Crear `config/modes/cfo.yaml` con `status: roadmap` y schema completo documentado (FR-023)
- [ ] T021 [P] [US1] Crear `config/modes/consultor-legal.yaml` con `status: roadmap` (FR-023)
- [ ] T022 [P] [US1] Crear `config/modes/marketing.yaml` con `status: roadmap` (FR-023)
- [ ] T023 [P] [US1] Crear `config/modes/vendedor-b2b.yaml` con `status: roadmap` (FR-023)
- [ ] T024 [P] [US1] Crear `config/modes/operaciones-pyme.yaml` con `status: roadmap` (FR-023)
- [ ] T025 [P] [US1] Crear `config/playbooks/general.yaml` (placeholder minimo para validacion de referencias; implementacion funcional es spec 012)
- [ ] T026 [P] [US1] Crear `config/playbooks/technology-watch.yaml` (placeholder minimo)
- [ ] T027 [P] [US1] Crear `config/playbooks/decision-debate.yaml` (placeholder minimo)
- [ ] T028 [P] [US1] Crear `config/playbooks/deep-research.yaml` (placeholder minimo)
- [ ] T029 [US1] Test de integracion: ejecutar `ModeLoader.load_all()` contra `config/modes/` real y verificar que los 3 modos MVP se registran y los 5 roadmap no aparecen en `list_available()` (SC-001, SC-007). **Depende de T017-T028** (requiere archivos YAML y playbooks creados)

**Independent Test Criteria for Phase 6**: `ModeLoader.load_all()` carga 3 modos MVP sin error; modos roadmap no aparecen en listado; playbooks referenciados existen como archivo. FR-021, FR-022, FR-023 cubiertos.

---

## Phase 7: company_geo e inyeccion en contexto

Logica que inyecta contexto geografico SIEMPRE en el prompt del agente (KISS/YAGNI) segun nivel de especificidad.

- [ ] T030 [US1] Test `tests/enterprise/modes/test_company_geo.py`: 4 tests (company_geo con 3 niveles genera contexto municipio/departamento/pais FR-019; solo country genera contexto nacional FR-020; sin department ni municipality no asume subdivision EC-05; contexto generado es string verificable SC-006)
- [ ] T031 [US1] Implementar funcion `build_geo_context(company_geo: CompanyGeo) -> str` en `src/vigilancia_multiagente/enterprise/modes/mode_schema.py` (o archivo dedicado si supera cohesion): genera fragmento de contexto inyectable con orden municipio > departamento > pais. Se inyecta SIEMPRE en el contexto del modo activo, sin heuristica de deteccion de normativa. Hacer T030 verde

**Independent Test Criteria for Phase 7**: `pytest tests/enterprise/modes/test_company_geo.py` verde; SC-006 verificado. FR-018, FR-019, FR-020 cubiertos.

---

## Phase 8: Integracion y wiring

Conectar componentes al ciclo de vida de la aplicacion.

- [ ] T032 [US1] Modificar `src/vigilancia_multiagente/api/dependencies.py`: wirear `ModeLoader` (singleton), `ModeRegistry` (resultado de `load_all()`), `ModeResolver` (con registry), `ModeToolFilter` (con `ToolRegistry`; composicion externa, tooling no importa modes). Sin tocar wirings del 2.0
- [ ] T033 [US1] Modificar `src/vigilancia_multiagente/api/app.py`: invocar `ModeLoader.load_all()` en evento lifespan startup y almacenar registry. Sin tocar routers existentes
- [ ] T034 [US1] Test de arranque: verificar que el sistema arranca con los 3 modos MVP cargados sin error en < 2 s (SC-001) y que `ModeResolver` esta disponible como dependencia

**Independent Test Criteria for Phase 8**: aplicacion arranca sin error; `ModeResolver` resuelve modo `default` al consultar sin activacion previa; SC-001 verificado end-to-end.

---

## Phase 9: Verificacion integral y quality gates

Cero regresiones, todos los SC verificados, linters limpios.

- [ ] T035 [P] Correr `pytest` completo (2.0 + enterprise) y verificar 0 regresiones
- [ ] T036 [P] Correr `scripts/check-layer-imports.py` y verificar 0 violaciones nuevas
- [ ] T037 [P] Correr `basedpyright` sobre archivos nuevos en `enterprise/modes/` y verificar 0 errores nuevos
- [ ] T038 [P] Correr `ruff check` + `ruff format` sobre archivos nuevos sin issues
- [ ] T039 Verificar SC-001: 3 modos MVP cargan sin error en < 2 s (medicion con timer en test)
- [ ] T040 Verificar SC-002: cambio de modo en < 500 ms (medicion en test)
- [ ] T041 Verificar SC-003: filtrado de tools por modo al 100% de escenarios de prueba
- [ ] T042 Verificar SC-004: modo invalido rechazado sin afectar carga de otros
- [ ] T043 Verificar SC-005: modo `vigilancia-tech` referencia playbook `technology-watch` correctamente (ejecucion funcional es spec 012)
- [ ] T044 Verificar SC-006: company_geo con 3 niveles inyectado correctamente en contexto
- [ ] T045 Verificar SC-007: modos `status: roadmap` no aparecen en listado disponible
- [ ] T046 Verificar que archivos nuevos no superan 400 LOC (regla C0 #10 de constitucion)

**Independent Test Criteria for Phase 9**: todos los SC-001..SC-007 verificados; 0 regresiones en 2.0; linters limpios; spec 011 listo para spec 012.

---

## Dependencies

- **Phase 1 (Precondiciones)** must complete before **Phase 2 (Schema)**.
- **Phase 2 (Schema)** must complete before **Phase 3 (Loader)** y **Phase 4 (Resolver)**.
- **Phase 3 (Loader)** must complete before **Phase 4 (Resolver)** (resolver necesita registry).
- **Phase 4 (Resolver)** must complete before **Phase 5 (Filtrado)** (filtrado necesita modo activo).
- **Phase 5 (Filtrado)** y **Phase 6 (Catalogo YAML)** son independientes entre si.
- **Phase 6 (Catalogo YAML)** must complete before **Phase 8 (Wiring)** (necesita archivos YAML reales).
- **Phase 7 (company_geo)** depende solo de **Phase 2 (Schema)** y puede ejecutarse en paralelo con Phases 3-6.
- **Phase 8 (Wiring)** depende de Phases 3, 4, 5, 6 y 7 completas.
- **Phase 9 (Verificacion)** must run after **Phase 8**.
- **T007** (test schema) must complete before **T008** (implementacion schema).
- **T009** (test loader) must complete before **T010, T011** (implementacion loader).
- **T012** (test resolver) must complete before **T013** (implementacion resolver).
- **T014** (test filter) must complete before **T015, T016** (implementacion filter).
- **T030** (test geo) must complete before **T031** (implementacion geo).
- **T029** (test integracion catalogo) must complete after **T017..T028** (archivos YAML y playbooks creados).
- **Dependencia externa**: spec 009 (ToolRegistry, company_profile, config/modes/) debe estar implementado.

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run **T002, T003, T004** en paralelo (verificaciones independientes de distintos artefactos).

### Phase 6 Parallel Block

- Run **T017, T018, T019, T020, T021, T022, T023, T024** en paralelo (archivos YAML distintos sin dependencia).
- Run **T025, T026, T027, T028** en paralelo (placeholders de playbooks distintos).

### Phases 5 + 7 Parallel Block

Tras Phase 4 completada:
- **Dev A**: T014 -> T015 -> T016 (filtrado por mode).
- **Dev B**: T030 -> T031 (company_geo).

Ambos trabajan en archivos distintos sin dependencia.

### Phase 9 Parallel Block

- Run **T035, T036, T037, T038** en paralelo (linters/tests/typechecks independientes).
- Luego **T039..T046** secuencial (verificaciones de SC que dependen de sistema completo).

---

## Implementation Strategy

1. **Cerrar Phase 1 (Precondiciones) primero**: validar que spec 009 dejo los artefactos necesarios. Cero codigo nuevo. Go/no-go para el spec 011.
2. **Phase 2 (Schema) como fundacion**: los modelos de datos son la base que todo lo demas importa. Implementar y testear antes de avanzar.
3. **Phases 3-4 secuenciales**: ModeRegistry -> ModeLoader -> ModeResolver. Cada uno depende del anterior.
4. **Phases 5 y 7 en paralelo**: filtrado por mode y company_geo son independientes; distribuir entre desarrolladores.
5. **Phase 6 (YAML) en paralelo con Phase 5**: los archivos YAML no dependen del codigo de filtrado; solo necesitan que el schema (Phase 2) este definido para validar estructura.
6. **Phase 8 (Wiring) como punto de integracion**: solo cuando todos los componentes estan testeados individualmente se conectan al ciclo de vida de la app.
7. **Phase 9 como gate final**: nada se considera entregado hasta que todos los SC pasen y 0 regresiones en el 2.0.
8. **MVP scope ESTRICTO**: solo 3 modos operativos. Los 5 modos roadmap se documentan como YAML con `status: roadmap` pero no se activan. Autodeteccion, hot-reload e intensidad funcional son roadmap post-MVP.

---

## Format Validation

Todas las tareas T001..T046 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001..T046).
- Marcador `[P]` solo en tareas paralelizables (diferentes archivos / sin dependencias incompletas).
- Label `[US1]` en tareas que implementan la user story (Phases 2-8); sin label en Precondiciones ni Verificacion.
- Descripcion con accion + path concreto del archivo.
- Traza a FR/SC del spec en cada fase.

**Total task count**: 46 tareas.
**Task count per phase**:
- Phase 1 (Precondiciones): 5
- Phase 2 (Schema): 3
- Phase 3 (Loader): 3
- Phase 4 (Resolver): 2
- Phase 5 (Filtrado): 3
- Phase 6 (Catalogo YAML): 13
- Phase 7 (company_geo): 2
- Phase 8 (Wiring): 3
- Phase 9 (Verificacion): 12
