# Implementation Plan: Skill Marketplace y Claude Local

**Feature ID**: 015-skill-marketplace-claude-local
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El Vigilador 3.0 carece de un modelo conceptual formal que distinga Skill, Capability, Tool y CommandSkill, y no tiene mecanismo para cargar, registrar y descubrir skills desde multiples fuentes. Hoy:

- Cero `SkillRegistry` con indice semantico ni carga progresiva de tres niveles.
- Cero `SkillLoader` que valide disponibilidad de capabilities contra el `ToolRegistry` (spec 009).
- Cero adapter para importar los 14 skills de `.claude/skills/` como fuente `external:claude-local`.
- Cero schema unificado `SKILL.md` con frontmatter YAML normalizado.
- Cero mecanismo de filtrado por Mode ni deduplicacion por prioridad de fuente.
- La carpeta `config/skills/` existe con un README placeholder y `skill_matrix_default.yaml` pero sin estructura `curated/` ni `learned/`.
- La carpeta `src/vigilancia_multiagente/enterprise/skills_marketplace/` existe con solo `__init__.py`.

Sin esta capa, los agentes no pueden seleccionar la receta correcta para una tarea, el contexto se satura con instrucciones irrelevantes, y no existe camino para incorporar skills de terceros de forma segura y versionada.

## Approach

Implementar el `SkillRegistry` como registro central en memoria con indice semantico (reusando `GeminiEmbeddingGateway` del 2.0), un `SkillLoader` que orquesta la carga desde fuentes habilitadas, y un `claude_local_adapter` que escanea `.claude/skills/*/SKILL.md`, normaliza el frontmatter OpenClaw al schema del Vigilador, calcula hash SHA-256 y marca skills peligrosos con `requires_sandbox: true`. La carga progresiva expone tres niveles (`SkillCard`, `SkillSummary`, `SkillBody`) para evitar saturacion de contexto. El filtrado por Mode y la validacion de capabilities contra `ToolRegistry` garantizan que solo skills ejecutables aparezcan en resultados. Marketplaces externos (K-Dense, agency-agents) quedan como roadmap; solo `external:claude-local` entra en MVP.

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje runtime | Python 3.11+ (mismo que 2.0) |
| Ubicacion modulos | `src/vigilancia_multiagente/enterprise/skills_marketplace/` |
| Config skills | `config/skills/{curated,learned}/` para archivos SKILL.md internos |
| Fuente externa MVP | `.claude/skills/*/SKILL.md` via `claude_local_adapter` |
| Embeddings | Reusar `GeminiEmbeddingGateway` existente del 2.0 (mismo que `ToolRegistry`) |
| Dependencia spec 009 | `ToolRegistry` operativo con metodo para consultar existencia y estado de capabilities |
| Dependencia spec 012 | Modes definidos en `config/modes/*.yaml`; este spec implementa mecanismo de filtrado con Mode placeholder |
| Schema skill | Frontmatter YAML obligatorio (`id`/`name`, `description`, `source`) + cuerpo Markdown |
| Formato OpenClaw | Campo `name` (no `id`), campos opcionales `metadata`, `allowed-tools`, `user-invocable` |
| Deduplicacion | Prioridad `curated > learned > external:claude-local > external:*` |
| Seguridad | Skills con shell/subprocess/git destructivo se marcan `requires_sandbox: true` (contrato para caller futuro) |
| Versionado | Hash SHA-256 del contenido; cambios detectados marcan `pending_revalidation` |
| CQS | `SkillRegistry.discover()` es query pura; mutaciones (registro, marcado) son operaciones separadas |
| File size | Cada archivo <= 400 LOC |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Cero breaking changes al 2.0 (constitucion #5) | No se modifica ningun archivo del 2.0. Tests del 2.0 siguen pasando al 100%. |
| Marketplaces externos son roadmap (00b) | Solo `external:claude-local` habilitado en MVP. Adapters K-Dense y agency-agents no se implementan. |
| Spec 009 debe estar operativo | `ToolRegistry` con `is_capability_available(name)` necesario para validar `required_capabilities`. |
| Spec 012 define Modes | El filtrado por Mode se implementa aqui pero usa Mode placeholder hasta que 012 lo defina. |
| 14 skills en `.claude/skills/` | Evidencia real: `speckit-plan`, `speckit-implement`, `speckit-specify`, etc. Formato OpenClaw con `name` + `description`. |
| Constitucion v1.2.0 modularidad | SRP por archivo, SoC entre registry/loader/adapter, DIP via interfaces. |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_models.py` | Dataclasses `SkillCard`, `SkillSummary`, `SkillBody`, `CommandSkill`, enums `SkillState`, `SkillSource`. |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_registry.py` | `SkillRegistry` con indice semantico, `discover()`, `get_cards()`, `get_summary()`, `get_body()`, `register()`, `mark_unavailable()`. |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_loader.py` | Orquestador de carga: escanea fuentes habilitadas, valida frontmatter, valida capabilities, registra en `SkillRegistry`. |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/claude_local_adapter.py` | Adapter para `.claude/skills/*/SKILL.md`: escaneo, normalizacion OpenClaw, hash SHA-256, deteccion sandbox. |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_schema_validator.py` | Validacion de frontmatter YAML: campos obligatorios, tipos, formato. |
| `src/vigilancia_multiagente/enterprise/skills_marketplace/skill_audit.py` | Escritura de audit trail JSONL para invocaciones de skills. |
| `config/skills/curated/.gitkeep` | Estructura para skills curados (se pobla en specs posteriores). |
| `config/skills/learned/.gitkeep` | Estructura para skills aprendidos (se pobla en F5b). |
| `config/skills/SCHEMA.md` | Documentacion del schema unificado SKILL.md + taxonomia Skill/Capability/Tool/CommandSkill (FR-002). |
| `tests/enterprise/skills_marketplace/test_skill_registry.py` | Tests del registry: discover, carga progresiva, deduplicacion, filtrado Mode. |
| `tests/enterprise/skills_marketplace/test_skill_loader.py` | Tests del loader: carga fuentes, validacion capabilities, exclusion invalidos. |
| `tests/enterprise/skills_marketplace/test_claude_local_adapter.py` | Tests del adapter: escaneo real de `.claude/skills/`, normalizacion, hash, sandbox detection. |
| `tests/enterprise/skills_marketplace/test_skill_schema_validator.py` | Tests de validacion: frontmatter valido/invalido, campos obligatorios. |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/enterprise/skills_marketplace/__init__.py` | Exportar clases publicas: `SkillRegistry`, `SkillLoader`, `SkillCard`, `SkillSummary`, `SkillBody`. |
| `config/skills/README.md` | Reemplazar placeholder con documentacion de la estructura `curated/` y `learned/` + referencia a `SCHEMA.md`. |
| `src/vigilancia_multiagente/config/settings.py` | Anadir seccion `skills.*`: `skills_sources_enabled` (list[str], env var `VT_SKILLS_SOURCES_ENABLED` formato JSON), `skills_claude_local_path`, `skills_revalidation_on_hash_change`. SSOT de runtime. |
| `config/settings.yaml` | Anadir bloque `skills:` DOC-ONLY (referencia para operadores; NO se carga en runtime). |
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear `SkillRegistry` y `SkillLoader` como singletons lazy. |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: 7 assumptions explicitas en el spec (A-01..A-07). Fase 1 valida que `ToolRegistry` y `.claude/skills/` estan operativos antes de escribir codigo.
  - **Simplicidad Obligatoria**: cero adapters para marketplaces externos (YAGNI). Cero skill curator, cero skill learning, cero quarantine. Solo las 3 fuentes MVP.
  - **Modularidad Primero**: 6 archivos nuevos con responsabilidad unica cada uno. `SkillRegistry` (query), `SkillLoader` (orquestacion carga), `claude_local_adapter` (normalizacion fuente externa), `skill_models` (tipos), `skill_schema_validator` (validacion), `skill_audit` (logging).
  - **Cambios Quirurgicos y Trazables**: 5 archivos modificados, todos en modo aditivo. Cero cambios al 2.0. Cero borrado ni renombre.
  - **Entrega Verificable**: 7 success criteria del spec + 10 acceptance scenarios + tests por fase.
- **Diseno de Software**: SRP (cada archivo un concern), SoC (registry/loader/adapter separados), DIP (`SkillRegistry` recibe embedding provider por inyeccion, no importa concreto), CQS (`discover()` query pura, `register()`/`mark_unavailable()` comandos), KISS (cero abstracciones para marketplaces que no existen en MVP), DRY (reusa `GeminiEmbeddingGateway` del 2.0).

---


## Phases

### Phase 1 — Validacion de prerequisitos y estructura (1-2 dias)

1. Verificar que `ToolRegistry` (spec 009) esta operativo. Actualmente NO expone `is_capability_available`; se requiere un cambio aditivo quirurgico (PREREQUISITO bloqueante para Phase 5): anadir `async def is_capability_available(name: str) -> bool` a `tool_registry.py` que retorne `True` si `name` existe en `self._tools` y `self._passes_gating(self._tools[name])` es `True`. Este metodo se anade como tarea T001 de esta fase. El mapeo `required_capabilities` → `tool.name` es directo (formato plano, e.g. `"template_render"`).
2. Verificar que `.claude/skills/` contiene al menos 14 directorios con `SKILL.md` valido (evidencia: 14 skills speckit confirmados).
3. Verificar que `GeminiEmbeddingGateway` del 2.0 esta funcional para generar embeddings.
4. Crear estructura `config/skills/curated/` y `config/skills/learned/` con `.gitkeep`.
5. Actualizar `config/skills/README.md` con documentacion de la estructura y referencia al schema.
6. Crear `config/skills/SCHEMA.md` con definiciones autoritativas de Skill vs Capability vs Tool vs CommandSkill (FR-001, FR-002) y documentacion del frontmatter obligatorio/opcional.

**Output**: estructura de carpetas lista, documentacion de schema creada, prerequisitos validados. Cero codigo funcional todavia.

### Phase 2 — Modelos de datos y validador de schema (2-3 dias)

1. Crear `enterprise/skills_marketplace/skill_models.py` (~200 LOC):
   - Enum `SkillSource`: `CURATED`, `LEARNED`, `EXTERNAL_CLAUDE_LOCAL`, `EXTERNAL_K_DENSE`, `EXTERNAL_AGENCY_AGENTS`.
   - Enum `SkillState`: `AVAILABLE`, `UNAVAILABLE`, `PENDING_REVALIDATION`.
   - Dataclass `SkillCard`: `id`, `display_name`, `description` (corta), `tags`, `source`, `mode_compatible`, `state`, `content_hash`, `requires_sandbox`, `path`.
   - Dataclass `SkillSummary`: `inputs`, `outputs`, `required_capabilities`, `required_company_files`, `examples`, `audit_level`.
   - Dataclass `SkillBody`: `full_content` (SKILL.md completo), `procedure_sections`, `code_blocks`.
   - Dataclass `CommandSkill` (extiende `SkillCard`): `argument_hint`, `user_invocable`.
2. Crear `enterprise/skills_marketplace/skill_schema_validator.py` (~150 LOC):
   - `validate_frontmatter(raw_yaml: dict) -> ValidationResult`: verifica campos obligatorios (`id` o `name`, `description`, `source`), tipos correctos, formato.
   - `normalize_id(frontmatter: dict) -> str`: acepta `id` o `name` como identificador (FR-006).
   - Retorna errores con ruta y detalle del campo invalido.
3. Tests `tests/enterprise/skills_marketplace/test_skill_schema_validator.py`:
   - Frontmatter valido con todos los campos.
   - Frontmatter con solo campos obligatorios.
   - Frontmatter sin `id` ni `name` falla.
   - Frontmatter con YAML invalido (syntax error) falla con detalle.
   - `name` se normaliza a `id` correctamente.

**Output**: modelos de datos tipados + validador con tests verdes.

### Phase 3 — Claude Local Adapter (2-3 dias)

1. Crear `enterprise/skills_marketplace/claude_local_adapter.py` (~200 LOC):
   - `ClaudeLocalAdapter.__init__(skills_path: Path)`: recibe ruta a `.claude/skills/`.
   - `scan() -> list[SkillCard]`: itera subdirectorios, busca `SKILL.md`, parsea frontmatter.
   - `normalize_openclaw(frontmatter: dict) -> dict`: mapea `name` -> `id`, `allowed-tools` -> `required_capabilities`, `user-invocable` -> `user_invocable`, `metadata` -> metadata adicional.
   - `compute_hash(content: str) -> str`: SHA-256 del contenido completo.
   - `detect_sandbox_required(body: str) -> bool`: busca keywords en contexto de comandos/codigo (`execute_command`, `subprocess`, `os.system`, `os.popen`, `Popen`, `shell=True`, `bash -c`, `git push`, `git reset`, `git clean`, `rm -rf`, `shutil.rmtree`) en el cuerpo. NO usa palabras genericas como 'write'/'create'/'delete' que generarian falsos positivos.
   - Cada skill se registra con `source: EXTERNAL_CLAUDE_LOCAL` y ruta relativa.
   - Directorios sin `SKILL.md` se ignoran con log warning (EC-01).
   - Frontmatter invalido se excluye con log error indicando ruta (EC-02).
2. Crear `enterprise/skills_marketplace/hash_tracker.py` (~80 LOC):
   - `HashTracker`: almacena hashes conocidos en `~/.vigilador/skills/hash_registry.json`.
   - `has_changed(skill_id: str, current_hash: str) -> bool`.
   - `update(skill_id: str, new_hash: str)`.
3. Tests `tests/enterprise/skills_marketplace/test_claude_local_adapter.py`:
   - Escaneo real de `.claude/skills/` retorna >= 14 skills.
   - Normalizacion de `name` a `id` funciona con formato OpenClaw real.
   - Hash SHA-256 es determinista para mismo contenido.
   - `speckit-implement` (que ejecuta shell y escribe archivos) se marca `requires_sandbox: true`.
   - Directorio sin `SKILL.md` se ignora sin error.
   - Cambio de hash detectado correctamente (FR-022).

**Output**: adapter funcional que importa los 14 skills de `.claude/skills/` + tests verdes.

### Phase 4 — SkillRegistry con indice semantico (3-4 dias)

1. Crear `enterprise/skills_marketplace/skill_registry.py` (~350 LOC):
   - `SkillRegistry.__init__(embedding_gateway: EmbeddingGateway, tool_registry: ToolRegistry)`: recibe el PORT abstracto `EmbeddingGateway` (interfaz en `domain.ports.embedding_gateway`), NO el concreto `GeminiEmbeddingGateway` (DIP). Tambien recibe `ToolRegistry` por inyeccion.
   - `register(card: SkillCard, summary: SkillSummary, body_path: Path)`: anade skill al indice. Rechaza duplicado por `id` con error (EC-06).
   - `discover(intent: str, mode: str | None, limit: int = 5) -> list[SkillCard]`: busqueda semantica sobre embeddings de `description` + `tags`, filtrado por Mode y disponibilidad.
   - `get_cards(mode: str | None = None) -> list[SkillCard]`: lista minima filtrada por Mode.
   - `get_summary(skill_id: str) -> SkillSummary`: carga bajo demanda.
   - `get_body(skill_id: str) -> SkillBody`: carga completa solo al ejecutar.
   - `mark_unavailable(skill_id: str, reason: str)`: marca skill como no disponible.
   - `mark_pending_revalidation(skill_id: str)`: marca skill con hash cambiado.
   - Deduplicacion por prioridad de fuente al registrar (FR-010).
   - Filtrado por `mode_compatible`: skills sin campo declarado pasan siempre (EC-05).
   - Skills con `state == UNAVAILABLE` o `PENDING_REVALIDATION` no aparecen en `discover()`.
2. Indice semantico:
   - Al registrar, genera embedding de `description + " " + " ".join(tags)` via `GeminiEmbeddingGateway`.
   - `discover()` genera embedding del `intent` y calcula cosine similarity contra el indice.
   - Top-k filtrado por Mode y disponibilidad.
3. Tests `tests/enterprise/skills_marketplace/test_skill_registry.py`:
   - Registro de 5 skills exitoso.
   - Duplicado por `id` rechazado con error.
   - `discover("generar reporte mensual")` retorna candidatos ordenados por similitud (embeddings mockeados).
   - Filtrado por Mode: skill con `mode_compatible: [CFO]` no aparece cuando Mode activo es `Vigilancia Tech`.
   - Skill con `mode_compatible` vacio aparece en todos los Modes.
   - Skill marcado `unavailable` no aparece en `discover()`.
   - Deduplicacion: curated prevalece sobre external con mismo `id`.
   - Performance: 50 skills registrados, `discover()` <= 500 ms (con embeddings mockeados).
   - `get_cards()` no carga cuerpos (SC-003).
   - `get_body()` carga archivo completo bajo demanda.

**Output**: `SkillRegistry` operativo con indice semantico + tests verdes.

### Phase 5 — SkillLoader y validacion de capabilities (2-3 dias)

1. Crear `enterprise/skills_marketplace/skill_loader.py` (~250 LOC):
   - `SkillLoader.__init__(registry, tool_registry, settings)`: recibe dependencias.
   - `load_all() -> LoadResult`: orquesta carga de todas las fuentes habilitadas.
   - `_load_curated(path: Path) -> list[SkillCard]`: escanea `config/skills/curated/` recursivamente buscando `*.md` con frontmatter valido.
   - `_load_learned(path: Path) -> list[SkillCard]`: escanea `config/skills/learned/`.
   - `_load_external_claude_local() -> list[SkillCard]`: invoca `ClaudeLocalAdapter.scan()`.
   - `_validate_capabilities(card: SkillCard, summary: SkillSummary) -> bool`: consulta `ToolRegistry` para cada capability en `required_capabilities`. Si alguna falta o esta DOWN, marca `unavailable` (FR-011).
   - `_apply_deduplication(cards: list[SkillCard]) -> list[SkillCard]`: prioridad `curated > learned > external` (FR-010).
   - `_detect_hash_changes(cards: list[SkillCard]) -> list[SkillCard]`: compara hashes con `HashTracker`, marca `pending_revalidation` si difieren (FR-022).
   - Solo carga fuentes listadas en `settings.py` field `skills_sources_enabled` (FR-025).
   - Se ejecuta al arranque antes de que agentes operen (FR-016).
2. Crear `enterprise/skills_marketplace/skill_audit.py` (~100 LOC):
   - `log_skill_invocation(skill_id, source, mode, capabilities_invoked, result_status)`: escribe a `~/.vigilador/audit/skills.log` (JSONL) (FR-024).
   - `log_skill_blocked(skill_id, reason)`: registra intentos bloqueados por sandbox.
3. Tests `tests/enterprise/skills_marketplace/test_skill_loader.py`:
   - Carga desde `config/skills/curated/` con 2 skills de prueba.
   - Carga desde `.claude/skills/` via adapter retorna >= 14.
   - Skill con `required_capabilities` faltante se marca `unavailable`.
   - Skill con `required_capabilities` vacia se considera siempre disponible (EC-03).
   - Fuente no habilitada en settings no se carga.
   - Todas las fuentes vacias: registry arranca vacio sin error (EC-04).
   - Deduplicacion: curated con mismo `id` que external prevalece.
   - Hash change detectado marca `pending_revalidation`.

**Output**: `SkillLoader` funcional + audit trail + tests verdes.

### Phase 6 — Integracion, settings y wiring (1-2 dias)

1. Extender `config/settings.py` con campos (SSOT de runtime, env_prefix `VT_`):
   - `skills_sources_enabled: list[str] = ["curated", "learned", "external:claude-local"]` (env var `VT_SKILLS_SOURCES_ENABLED`; formato: lista JSON, e.g. `'["curated","learned","external:claude-local"]'`).
   - `skills_claude_local_path: str = ".claude/skills"`.
   - `skills_curated_path: str = "config/skills/curated"`.
   - `skills_learned_path: str = "config/skills/learned"`.
   - `skills_revalidation_on_hash_change: bool = True`.
2. Extender `config/settings.yaml` con bloque `skills:` (DOC-ONLY — referencia para operadores; NO se carga en runtime. El SSOT es `settings.py` con env vars `VT_*`. No existe loader YAML en el sistema).
3. Wirear en `api/dependencies.py`:
   - `SkillLoader` como singleton que se ejecuta al arranque.
   - `SkillRegistry` como singleton inyectado en `SkillLoader` y disponible para agentes.
4. Actualizar `enterprise/skills_marketplace/__init__.py` con exports publicos.
5. Verificar que `scripts/check-layer-imports.py` pasa sin violaciones.
6. Verificar que tests del 2.0 siguen pasando al 100%.

**Output**: sistema integrado, settings configurados, wiring completo.

### Phase 7 — Verificacion end-to-end y cierre (1-2 dias)

1. Test de integracion end-to-end:
   - Arrancar `SkillLoader` con `.claude/skills/` reales.
   - Verificar >= 14 skills registrados en `SkillRegistry`.
   - Ejecutar `discover(intent="plan de implementacion")` y verificar que retorna skills speckit relevantes.
   - Verificar carga progresiva: `get_cards()` no carga cuerpos, `get_body()` carga completo.
   - Verificar que skills con shell/git estan marcados `requires_sandbox: true`.
2. Verificar SC-001..SC-007 del spec uno por uno con evidencia.
3. Verificar que `SkillRegistry` carga en <= 3 s con 14 skills.
4. Verificar que `discover()` responde en <= 500 ms con 50 skills (sinteticos).
5. Correr toda la bateria `pytest` sin regresiones.

**Output**: spec 015 completado, listo para que spec 012 consuma `SkillRegistry.discover()`.

---


## Rollout Strategy

**Estrategia**: incremental por fase. Cada fase produce artefactos verificables y tests deben pasar antes de avanzar.

- **Backward compatibility**: cero cambios al 2.0. El `SkillRegistry` vive enteramente en `enterprise/skills_marketplace/` sin tocar modulos existentes.
- **Feature flags**: cero necesarios. La existencia del subpaquete no afecta al 2.0 ni a otros specs.
- **Coexistencia con ToolRegistry**: el `SkillRegistry` consume `ToolRegistry` como dependencia de lectura (valida capabilities) pero no lo modifica.
- **Mode placeholder**: hasta que spec 012 defina Modes reales, el filtrado por Mode acepta cualquier string y skills sin `mode_compatible` pasan siempre.
- **Marketplaces externos**: adapters K-Dense y agency-agents NO se implementan. Quedan documentados en `SCHEMA.md` como fuentes futuras con interface placeholder en `SkillSource` enum.
- **Deploy**: una vez todas las fases verdes, el `SkillLoader` se activa al arranque. Si falla la carga de una fuente, las demas siguen operando (graceful degradation).

---

## Success Criteria

- **SC-001**: El `SkillRegistry` carga y registra >= 14 skills desde `.claude/skills/` al arranque sin errores, en <= 3 s.
- **SC-002**: Una busqueda semantica `discover(intent, mode, limit=5)` sobre un catalogo de 50 skills responde en <= 500 ms.
- **SC-003**: La carga progresiva funciona correctamente: `get_cards()` no carga cuerpos de skills; `get_body(id)` carga el archivo completo solo bajo demanda.
- **SC-004**: Skills con capabilities faltantes se marcan `unavailable` al 100% de los casos de prueba (cero falsos positivos en el listing).
- **SC-005**: La deduplicacion por prioridad de fuente funciona correctamente: un skill curado con mismo `id` que uno externo siempre prevalece.
- **SC-006**: Skills marcados `requires_sandbox: true` tienen el flag correcto al 100% de los escenarios de prueba (cero falsos negativos en skills con comandos shell/subprocess/git destructivo; cero falsos positivos en skills documentales). Este spec NO ejecuta skills; solo establece el flag como contrato.
- **SC-007**: Un cambio de contenido en un `SKILL.md` local se detecta por diferencia de hash en el siguiente arranque y el skill se marca `pending_revalidation`.
- **SC-008**: `pytest` corre verde al 100% sobre todas las suites: 2.0 (sin regresiones) + nuevas suites de spec 015.
- **SC-009**: `scripts/check-layer-imports.py` pasa sin nuevas violaciones.
- **SC-010**: Cero archivos bajo `enterprise/skills_marketplace/` con `pass`/`...`/`TODO` al cierre.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Justification**:
  - **Pensar Antes de Codificar**: Phase 1 entera dedicada a validar prerequisitos (ToolRegistry operativo, `.claude/skills/` accesible, embeddings funcionales) antes de escribir codigo. 7 assumptions del spec verificadas explicitamente.
  - **Simplicidad Obligatoria**: cero adapters para marketplaces externos (YAGNI estricto). Cero skill curator, cero skill learning, cero quarantine, cero CLI admin. Solo lo que el spec MVP requiere.
  - **Modularidad Primero**: 6 archivos funcionales nuevos, cada uno con responsabilidad unica. `skill_models` (tipos), `skill_schema_validator` (validacion), `claude_local_adapter` (fuente externa), `skill_registry` (indice + queries), `skill_loader` (orquestacion), `skill_audit` (logging). Ningun archivo mezcla concerns.
  - **Cambios Quirurgicos y Trazables**: 5 archivos existentes modificados en modo aditivo (anadir settings, anadir wires, actualizar README). Cero borrado, cero renombre, cero cambios al 2.0.
  - **Entrega Verificable**: 10 success criteria medibles + 10 acceptance scenarios del spec + 4 suites de tests. Cada SC tiene metodo de validacion claro.
  - **Diseno de Software**: SRP (cada archivo un concern), SoC (registry/loader/adapter/validator separados), DIP (`SkillRegistry` recibe `embedding_gateway` y `tool_registry` por inyeccion), CQS (`discover()` query pura, `register()`/`mark_unavailable()` comandos separados), DRY (reusa embeddings del 2.0), KISS (cero abstracciones especulativas), OCP (nuevos adapters se anaden sin modificar `SkillLoader` gracias a interface comun).
