# Tasks: Skill Marketplace y Claude Local

**Input**: `specs/015-skill-marketplace-claude-local/spec.md`, `specs/015-skill-marketplace-claude-local/plan.md`
**Feature**: Skill Marketplace MVP — modelo conceptual Skill/Capability/Tool/CommandSkill, SkillRegistry con indice semantico y carga progresiva, SkillLoader multi-fuente, adapter Claude local para `.claude/skills/`, filtrado por Mode, validacion de capabilities, seguridad sandbox.

**User Stories del spec**:
- **US1 (P1)**: Agente del Vigilador 3.0 descubre la skill mas relevante para una tarea sin cargar todo el catalogo al contexto.
  *Unico user story; cubre los 10 acceptance scenarios, 6 edge cases y 26 FRs.*

**Testing strategy**: test-before-implementation por componente. Cada modulo tiene su suite de tests creada antes de la implementacion. SC-001..SC-007 se verifican en Phase 7.

---

## Phase 1: Validacion de prerequisitos y estructura

Cero codigo funcional. Solo validacion de dependencias externas + creacion de estructura de carpetas + documentacion de schema.

- [ ] T001 [PREREQUISITO] Extender `ToolRegistry` con `async def is_capability_available(name: str) -> bool` (cambio aditivo quirurgico en `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`): retorna `True` si `name` existe en `self._tools` y `self._passes_gating(self._tools[name])` es `True`. Validar que el metodo funciona importando `ToolRegistry` y confirmando que expone el nuevo metodo. Persistir resultado en `docs/015-prerequisites.md`. El mapeo `required_capabilities` → `tool.name` es directo (formato plano, e.g. `"template_render"`, NO `domain.tool_name`)
- [ ] T002 [P] Validar que `.claude/skills/` contiene >= 14 subdirectorios con `SKILL.md`: listar directorios y confirmar conteo. Persistir resultado en `docs/015-prerequisites.md`
- [ ] T003 [P] Validar que `GeminiEmbeddingGateway` del 2.0 esta funcional: ejecutar test sintetico contra `src/vigilancia_multiagente/infra/embeddings/gemini_gateway.py` confirmando que genera embeddings. Persistir resultado en `docs/015-prerequisites.md`
- [ ] T004 [P] Crear estructura `config/skills/curated/` con `.gitkeep` en `config/skills/curated/.gitkeep`
- [ ] T005 [P] Crear estructura `config/skills/learned/` con `.gitkeep` en `config/skills/learned/.gitkeep`
- [ ] T006 Actualizar `config/skills/README.md` con documentacion de la estructura `curated/` y `learned/`, referencia a `SCHEMA.md`, y politica de fuentes habilitadas (FR-002)
- [ ] T007 Crear `config/skills/SCHEMA.md` con definiciones autoritativas de Skill vs Capability vs Tool vs CommandSkill (FR-001, FR-002), documentacion del frontmatter obligatorio/opcional (FR-003, FR-004, FR-005), y ejemplos de formato

**Independent Test Criteria for Phase 1**: `docs/015-prerequisites.md` confirma ToolRegistry operativo + `.claude/skills/` con >= 14 skills + GeminiEmbeddingGateway funcional; carpetas `config/skills/curated/` y `config/skills/learned/` existen; `config/skills/SCHEMA.md` documenta taxonomia completa; tests del 2.0 siguen pasando al 100%.

---

## Phase 2: Modelos de datos y validador de schema

Tipos base que todo el subsistema importa. Test-before-implementation.

- [ ] T008 [P] Crear `tests/enterprise/skills_marketplace/__init__.py` (archivo vacio para paquete de tests)
- [ ] T009 Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_models.py` con: enums `SkillSource` (CURATED, LEARNED, EXTERNAL_CLAUDE_LOCAL, EXTERNAL_K_DENSE, EXTERNAL_AGENCY_AGENTS) y `SkillState` (AVAILABLE, UNAVAILABLE, PENDING_REVALIDATION); dataclasses `SkillCard` (id, display_name, description, tags, source, mode_compatible, state, content_hash, requires_sandbox, path), `SkillSummary` (inputs, outputs, required_capabilities, required_company_files, examples, audit_level), `SkillBody` (full_content, procedure_sections, code_blocks), `CommandSkill` (extiende SkillCard con argument_hint, user_invocable) (FR-001, FR-003, FR-004)
- [ ] T010 Test `tests/enterprise/skills_marketplace/test_skill_schema_validator.py`: 5 tests — frontmatter valido con todos los campos pasa; frontmatter con solo campos obligatorios pasa; frontmatter sin `id` ni `name` falla con error descriptivo; frontmatter con YAML invalido falla indicando ruta y linea; campo `name` se normaliza a `id` correctamente (FR-006)
- [ ] T011 Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_schema_validator.py` con: `validate_frontmatter(raw_yaml: dict) -> ValidationResult` que verifica campos obligatorios (id o name, description, source) y tipos; `normalize_id(frontmatter: dict) -> str` que acepta id o name como identificador. Hacer T010 verde (FR-003, FR-006, FR-015)

**Independent Test Criteria for Phase 2**: `pytest tests/enterprise/skills_marketplace/test_skill_schema_validator.py` verde; modelos importables sin error; `basedpyright` sin nuevos errores en archivos creados.

---

## Phase 3: Claude Local Adapter

Adapter que escanea `.claude/skills/*/SKILL.md`, normaliza formato OpenClaw, calcula hash, detecta sandbox. Test-before-implementation.

- [ ] T012 Test `tests/enterprise/skills_marketplace/test_claude_local_adapter.py`: 7 tests — escaneo real de `.claude/skills/` retorna >= 14 skills; normalizacion de campo `name` a `id` funciona con formato OpenClaw real; hash SHA-256 es determinista para mismo contenido; skill que referencia `execute_command`/`subprocess`/`git push` se marca `requires_sandbox: true`; directorio sin `SKILL.md` se ignora con log warning (EC-01); frontmatter YAML invalido se excluye con log error (EC-02); cambio de hash detectado correctamente (FR-019, FR-022)
- [ ] T013 Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py` con: clase `ClaudeLocalAdapter` con constructor que recibe `skills_path: Path`; metodo `scan() -> list[SkillCard]` que itera subdirectorios buscando `SKILL.md`; metodo `normalize_openclaw(frontmatter: dict) -> dict` que mapea name->id, allowed-tools->required_capabilities; metodo `compute_hash(content: str) -> str` con SHA-256; metodo `detect_sandbox_required(body: str) -> bool` con keywords en contexto de comandos/codigo (`execute_command`, `subprocess`, `os.system`, `os.popen`, `Popen`, `shell=True`, `bash -c`, `git push`, `git reset`, `git clean`, `rm -rf`, `shutil.rmtree`); NO usa palabras genericas como 'write'/'create'/'delete'. Cada skill con `source: EXTERNAL_CLAUDE_LOCAL`. Hacer T012 verde (FR-017, FR-018, FR-019, FR-020, FR-021)
- [ ] T014 Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/hash_tracker.py` con: clase `HashTracker` que almacena hashes en `~/.vigilador/skills/hash_registry.json`; metodos `has_changed(skill_id: str, current_hash: str) -> bool` y `update(skill_id: str, new_hash: str)` (FR-022)

**Independent Test Criteria for Phase 3**: `pytest tests/enterprise/skills_marketplace/test_claude_local_adapter.py` verde; adapter importa >= 14 skills reales de `.claude/skills/`; skills con shell/git marcados `requires_sandbox: true`.

---

## Phase 4: SkillRegistry con indice semantico

Registro central con discover semantico, carga progresiva de tres niveles, deduplicacion y filtrado por Mode. Test-before-implementation.

- [ ] T015 Test `tests/enterprise/skills_marketplace/test_skill_registry.py`: 10 tests — registro de 5 skills exitoso; duplicado por id de misma fuente rechazado con error (EC-06); `discover("generar reporte mensual")` retorna candidatos ordenados por similitud (embeddings mockeados); filtrado por Mode: skill con mode_compatible [CFO] no aparece cuando Mode activo es Vigilancia Tech (AS-9); skill con mode_compatible vacio aparece en todos los Modes (EC-05); skill marcado unavailable no aparece en discover; deduplicacion curated prevalece sobre external con mismo id (AS-2, FR-010); `get_cards()` no carga cuerpos (SC-003); `get_summary(id)` retorna detalle intermedio (AS-5); `get_body(id)` carga archivo completo bajo demanda (AS-6)
- [ ] T016 Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_registry.py` con: clase `SkillRegistry` con constructor que recibe `embedding_gateway: EmbeddingGateway` (PORT abstracto de `domain.ports.embedding_gateway`, NO el concreto `GeminiEmbeddingGateway` — DIP) y `tool_registry: ToolRegistry` por inyeccion; metodo `register(card, summary, body_path)` con deduplicacion por prioridad de fuente; metodo `discover(intent, mode, limit=5) -> list[SkillCard]` con busqueda semantica via cosine similarity sobre embeddings de description+tags, filtrado por Mode y disponibilidad; metodos `get_cards(mode)`, `get_summary(skill_id)`, `get_body(skill_id)` para carga progresiva; metodos `mark_unavailable(skill_id, reason)` y `mark_pending_revalidation(skill_id)`. CQS: discover es query pura, register/mark son comandos. Hacer T015 verde (FR-007, FR-008, FR-009, FR-010, FR-011, FR-012)
- [ ] T017 Test de performance `tests/enterprise/skills_marketplace/test_skill_registry_perf.py`: registrar 50 skills sinteticos, medir `discover()` <= 500 ms con embeddings mockeados (SC-002)

**Independent Test Criteria for Phase 4**: `pytest tests/enterprise/skills_marketplace/test_skill_registry.py tests/enterprise/skills_marketplace/test_skill_registry_perf.py` verde; discover responde en <= 500 ms con 50 skills; carga progresiva verificada.

---

## Phase 5: SkillLoader, validacion de capabilities y audit

Orquestador de carga multi-fuente + validacion contra ToolRegistry + audit trail JSONL. Test-before-implementation.

- [ ] T018 Test `tests/enterprise/skills_marketplace/test_skill_loader.py`: 8 tests — carga desde `config/skills/curated/` con 2 skills de prueba; carga desde `.claude/skills/` via adapter retorna >= 14; skill con required_capabilities faltante se marca unavailable (AS-3, FR-011); skill con required_capabilities vacia se considera siempre disponible (EC-03); fuente no habilitada en settings no se carga (FR-025); todas las fuentes vacias arranca vacio sin error (EC-04); deduplicacion curated con mismo id que external prevalece (FR-010); hash change detectado marca pending_revalidation (AS-8, FR-022)
- [ ] T019 Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py` con: clase `SkillLoader` con constructor que recibe registry, tool_registry, settings; metodo `load_all() -> LoadResult` que orquesta carga de fuentes habilitadas; metodos privados `_load_curated(path)`, `_load_learned(path)`, `_load_external_claude_local()`; metodo `_validate_capabilities(card, summary) -> bool` que consulta `ToolRegistry.is_capability_available(name)` para cada capability; metodo `_apply_deduplication(cards) -> list[SkillCard]`; metodo `_detect_hash_changes(cards)` que compara con HashTracker. Solo carga fuentes de `settings.py` field `skills_sources_enabled`. Se ejecuta al arranque. Hacer T018 verde (FR-013, FR-014, FR-015, FR-016, FR-025)
- [ ] T020 [P] Crear `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_audit.py` con: funcion `log_skill_invocation(skill_id, source, mode, capabilities_invoked, result_status)` que escribe JSONL a `~/.vigilador/audit/skills.log`; funcion `log_skill_blocked(skill_id, reason)` para intentos bloqueados por sandbox (FR-023, FR-024)

**Independent Test Criteria for Phase 5**: `pytest tests/enterprise/skills_marketplace/test_skill_loader.py` verde; skills con capabilities faltantes marcados unavailable al 100%; fuentes deshabilitadas no se cargan; audit trail escribe JSONL correctamente.

---

## Phase 6: Integracion, settings y wiring

Conectar todos los componentes al sistema existente. Cero funcionalidad nueva, solo wiring.

- [ ] T021 Extender `src/vigilancia_multiagente/config/settings.py` con campos (SSOT de runtime, env_prefix `VT_`): `skills_sources_enabled: list[str]` (default `["curated", "learned", "external:claude-local"]`, env var `VT_SKILLS_SOURCES_ENABLED` formato lista JSON), `skills_claude_local_path: str` (default `.claude/skills`), `skills_curated_path: str` (default `config/skills/curated`), `skills_learned_path: str` (default `config/skills/learned`), `skills_revalidation_on_hash_change: bool` (default True) (FR-025, FR-026)
- [ ] T022 [P] [DOCUMENTACIÓN] Extender `config/settings.yaml` con bloque `skills:` conteniendo `sources_enabled: [curated, learned, external:claude-local]`, `claude_local_path: .claude/skills`, `curated_path: config/skills/curated`, `learned_path: config/skills/learned`, `revalidation_on_hash_change: true`. NOTA: este archivo es DOC-ONLY (referencia para operadores); NO se carga en runtime. El SSOT es `settings.py` con env vars `VT_*`. No existe loader YAML en el sistema (FR-025)
- [ ] T023 Wirear en `src/vigilancia_multiagente/api/dependencies.py`: `SkillRegistry` como singleton lazy inyectado con `EmbeddingGateway` (PORT abstracto, resuelto a `GeminiEmbeddingGateway` en wiring) y `ToolRegistry`; `SkillLoader` como singleton que se ejecuta al arranque registrando skills antes de que agentes operen (FR-016)
- [ ] T024 Actualizar `src/vigilancia_multiagente/enterprise/skills_marketplace/__init__.py` con exports publicos: `SkillRegistry`, `SkillLoader`, `SkillCard`, `SkillSummary`, `SkillBody`, `ClaudeLocalAdapter`, `SkillSource`, `SkillState`
- [ ] T025 [P] Verificar que `scripts/check-layer-imports.py` pasa sin nuevas violaciones de capas
- [ ] T026 [P] Verificar que tests del 2.0 siguen pasando al 100%: `pytest` sin regresiones

**Independent Test Criteria for Phase 6**: settings cargables sin error; wiring funcional (SkillLoader arranca y registra skills); `scripts/check-layer-imports.py` sin violaciones; tests del 2.0 verdes.

---

## Phase 7: Verificacion end-to-end y cierre

Validacion de todos los SC del spec. Cero codigo nuevo.

- [ ] T027 Test de integracion end-to-end `tests/enterprise/skills_marketplace/test_integration_e2e.py`: arrancar SkillLoader con `.claude/skills/` reales, verificar >= 14 skills registrados en SkillRegistry, ejecutar `discover(intent="plan de implementacion")` y verificar que retorna skills speckit relevantes (SC-001)
- [ ] T028 [P] Verificar SC-001: SkillRegistry carga >= 14 skills desde `.claude/skills/` al arranque sin errores en <= 3 s. Medir tiempo y documentar en `docs/015-sc-validation.md`
- [ ] T029 [P] Verificar SC-002: discover con 50 skills sinteticos responde en <= 500 ms. Documentar en `docs/015-sc-validation.md`
- [ ] T030 [P] Verificar SC-003: `get_cards()` no carga cuerpos; `get_body(id)` carga archivo completo solo bajo demanda. Documentar en `docs/015-sc-validation.md`
- [ ] T031 [P] Verificar SC-004: skills con capabilities faltantes se marcan unavailable al 100% de los casos. Documentar en `docs/015-sc-validation.md`
- [ ] T032 [P] Verificar SC-005: deduplicacion por prioridad de fuente funciona (curated prevalece sobre external). Documentar en `docs/015-sc-validation.md`
- [ ] T033 [P] Verificar SC-006: skills que cumplen la heuristica de sandbox tienen el flag `requires_sandbox: true` correcto (cero falsos negativos en skills con comandos shell/subprocess/git; cero falsos positivos en skills documentales). Documentar en `docs/015-sc-validation.md`
- [ ] T034 [P] Verificar SC-007: cambio de contenido en SKILL.md local se detecta por hash y skill se marca pending_revalidation. Documentar en `docs/015-sc-validation.md`
- [ ] T035 Correr suite completa `pytest` y verificar 0 regresiones (2.0 + spec 015). Documentar en `docs/015-sc-validation.md`
- [ ] T036 [P] Verificar `grep -rE "^\s*(pass|\.\.\.|TODO)\s*$" src/vigilancia_multiagente/enterprise/skills_marketplace/` retorna 0 matches (excepto `__init__.py` vacios)
- [ ] T037 [P] Correr `ruff check src/vigilancia_multiagente/enterprise/skills_marketplace/ tests/enterprise/skills_marketplace/` sin issues

**Independent Test Criteria for Phase 7**: SC-001..SC-007 verificados con evidencia en `docs/015-sc-validation.md`; pytest verde al 100%; cero pass/TODO en codigo de produccion; ruff limpio.

---

## Dependencies

- **Phase 1 (Prerequisitos)** must complete before **Phase 2 (Modelos)**.
- **Phase 2 (Modelos)** must complete before **Phase 3 (Adapter)** y **Phase 4 (Registry)**.
- **Phase 3 (Adapter)** must complete before **Phase 5 (Loader)**.
- **Phase 4 (Registry)** must complete before **Phase 5 (Loader)**.
- **Phase 5 (Loader)** must complete before **Phase 6 (Integracion)**.
- **Phase 6 (Integracion)** must complete before **Phase 7 (Verificacion)**.
- Dentro de **Phase 1**: T001 es bloqueante (valida ToolRegistry); T002, T003, T004, T005 son independientes entre si.
- Dentro de **Phase 2**: T009 (modelos) bloquea T010 y T011 (validador los importa). T008 es independiente.
- Dentro de **Phase 3**: T012 (test) se escribe antes de T013 (implementacion). T014 (hash_tracker) es independiente de T012/T013 pero T013 lo importa.
- Dentro de **Phase 4**: T015 (test) se escribe antes de T016 (implementacion). T017 (perf) requiere T016.
- Dentro de **Phase 5**: T018 (test) se escribe antes de T019 (implementacion). T020 (audit) es independiente.
- Dentro de **Phase 6**: T021 (settings.py) bloquea T022 y T023. T024, T025, T026 son independientes tras T023.
- **Dependencia externa**: spec 009 (ToolRegistry) debe estar operativo antes de Phase 1.
- **Dependencia externa**: spec 012 (Modes) es opcional; se usa Mode placeholder hasta que 012 se implemente.

## Parallel Execution Examples

### Phase 1 Parallel Block

- Run **T002, T003, T004, T005** en paralelo (validaciones y creacion de carpetas independientes).

### Phase 2 Parallel Block

- **T008** puede correr en paralelo con **T009**.
- **T010** y **T011** son secuenciales (test-before-implementation) pero independientes de T008.

### Phase 3 + Phase 4 Parallel Block

Tras Phase 2 verde, Phase 3 y Phase 4 pueden ejecutarse en paralelo por desarrolladores distintos:

- **Dev A — Adapter**: T012 -> T013 -> T014.
- **Dev B — Registry**: T015 -> T016 -> T017.

### Phase 5 Parallel Block

- **T020** (audit) puede correr en paralelo con **T018 -> T019** (loader).

### Phase 6 Parallel Block

- Tras T021 y T023: run **T024, T025, T026** en paralelo.

### Phase 7 Parallel Block

- Run **T028, T029, T030, T031, T032, T033, T034, T036, T037** en paralelo (verificaciones independientes sobre sistema ya integrado).

---

## Implementation Strategy

1. **Cerrar Phase 1 (Prerequisitos) primero**: validar que ToolRegistry, `.claude/skills/` y embeddings estan operativos. Esto da go/no-go al spec 015 completo. Si ToolRegistry no esta listo, este spec se bloquea.
2. **Phase 2 (Modelos) como base**: tipos y validador son importados por todo el subsistema. Deben estar solidos antes de avanzar.
3. **Phase 3 y Phase 4 en paralelo**: el adapter y el registry son independientes entre si. Distribuir entre dos desarrolladores para acelerar.
4. **Phase 5 (Loader) como integracion interna**: une adapter + registry + validacion de capabilities. Requiere ambos anteriores.
5. **Phase 6 (Wiring) como integracion al sistema**: conecta el subsistema al runtime del Vigilador. Cambios quirurgicos en 3 archivos existentes (settings.py, settings.yaml, dependencies.py).
6. **Phase 7 (Verificacion) como gate final**: nada se considera entregado hasta que SC-001..SC-007 esten verificados con evidencia.
7. **Scope MVP estricto**: marketplaces externos (K-Dense, agency-agents) NO se implementan. Solo `external:claude-local`. Skill Learning y Skill Curator son roadmap post-MVP.

---

## Format Validation

Todas las tareas T001..T037 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001..T037).
- Marcador `[P]` solo en tareas paralelizables (diferentes archivos / sin dependencias incompletas).
- Descripcion con accion + path concreto del archivo.
- Traza a FR/SC/AS/EC del spec donde aplica.

**Total task count**: 37 tareas.
**Task count per phase**:
- Phase 1 (Prerequisitos): 7
- Phase 2 (Modelos): 4
- Phase 3 (Adapter): 3
- Phase 4 (Registry): 3
- Phase 5 (Loader): 3
- Phase 6 (Integracion): 6
- Phase 7 (Verificacion): 11

**MVP vs Roadmap**:
- MVP: todo lo listado (fuente `external:claude-local` + curated + learned).
- Roadmap (NO implementar): adapters K-Dense y agency-agents, Skill Learning por demostracion, Skill Curator, CLI admin, override con herencia, tests sinteticos automatizados.
