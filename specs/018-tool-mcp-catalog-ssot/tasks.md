# Tasks: Catalogo SSOT de Tools/MCPs con Discovery Semantico

**Input**: `specs/018-tool-mcp-catalog-ssot/spec.md`, `specs/018-tool-mcp-catalog-ssot/plan.md`
**Feature**: Catalogo SSOT con 79 entradas, regla de importacion por LOC, import refactorizado de 4 tools MVP Tier 1, discovery semantico 3 niveles, validacion integral.

**Traza a spec**: FR-001..FR-018, SC-001..SC-007.

**Testing strategy**: test-before-implementation por componente. Cada fase produce artefactos verificables con scripts automatizados. Cero codigo para las 59 tools roadmap (YAGNI). Cero modificaciones al 2.0 (cambios quirurgicos).

---

## Phase 1: Inventario de LOC y generacion del catalogo SSOT

Objetivo: medir LOC por unidad en fuentes clonadas, aplicar regla de importacion, generar catalogo YAML con 79 entradas validadas.

Independent Test Criteria: `python scripts/validate_catalog.py` pasa sin errores; exactamente 79 entradas totales; exactamente 20 con `mvp: true`; coherencia LOC vs strategy al 100%.

- [ ] T001 Crear `scripts/inventory_loc.py` que recorra `documentation/hermes agent/hermes-agent/tools/` (archivos .py individuales + subcarpetas `environments/`, `computer_use/`) y `documentation/hermes agent/hermes-agent/optional-mcps/` (cada subcarpeta como unidad), cuente lineas .py excluyendo paths con `test`, `docs`, archivos `*_test.py` y `conftest.py`, y genere reporte JSON con nombre, loc_count, language, ruta fuente por unidad en `scripts/inventory_loc.py`
- [ ] T002 Crear `config/tools/catalog-schema.json` con JSON Schema que valide: campos obligatorios (id, domain, source, strategy, runtime, status, owner, license, capabilities, requires_key, env_var, healthcheck, update_policy, loc_count, loc_validated, language, mvp), campos opcionales (notes, dedup_group, source_repo, pinned_version, last_audit_date), valores permitidos de `strategy` (COPY-HERMES, WRAP-SDK, MCP-EXTERNO, TRANSLATE-THIN, NUEVO), valores de `runtime` (python_internal, process_stdio, process_http), valores de `language` (python, typescript, go, rust, yaml), `mvp` boolean, reglas de coherencia (language != python implica runtime != python_internal) en `config/tools/catalog-schema.json`
- [ ] T003 [P] Crear `scripts/validate_catalog.py` que cargue `config/tools/catalog.yaml`, valide contra `config/tools/catalog-schema.json`, verifique reglas de coherencia LOC vs strategy (python + loc<5000 -> python_internal; otro lenguaje o loc>=5000 -> process_stdio/process_http), cuente entradas totales (79) y MVP (20), reporte errores con linea y campo en `scripts/validate_catalog.py`
- [ ] T004 Ejecutar `scripts/inventory_loc.py`, registrar resultados, aplicar regla de importacion por unidad y generar `config/tools/catalog.yaml` con 79 entradas completas: 20 con `mvp: true` (4 Tier 1 documents + 16 Tier 2), 59 con `mvp: false`, todos los campos obligatorios poblados (id, domain, source, strategy, runtime, status, owner, license, capabilities, requires_key, env_var, healthcheck, update_policy, loc_count, loc_validated, language, mvp), campos opcionales (notes, dedup_group, source_repo, pinned_version, last_audit_date) donde aplique, `loc_validated: true` para unidades medidas directamente y `loc_validated: false` para las sin fuente clonada en `config/tools/catalog.yaml`
- [ ] T005 Ejecutar `python scripts/validate_catalog.py` y confirmar: 0 errores de schema, 79 entradas totales, 20 MVP, coherencia LOC-strategy al 100%. Corregir catalogo si hay fallos hasta que pase limpio

---

## Phase 2: CatalogLoader y registro en ToolRegistry

Objetivo: cargar catalogo YAML al arranque, parsear entradas, alimentar ToolRegistry con metadata de estrategia y filtro MVP.

Dependencia: Phase 1 completada (catalogo validado). Spec 009 implementada (ToolWrapper, ToolRegistry existentes).

Independent Test Criteria: `pytest tests/enterprise/tooling/test_catalog_loader.py` verde; ToolRegistry cargado con 79 entradas; filtro MVP retorna 20.

- [ ] T006 Crear test `tests/enterprise/tooling/test_catalog_loader.py` con 5 tests: carga exitosa de catalogo con 79 entradas retorna lista de CatalogEntry; falla si campo obligatorio falta; falla si strategy tiene valor invalido; filtro mvp_only retorna exactamente 20 entradas; entradas con loc_validated=false se cargan con warning en `tests/enterprise/tooling/test_catalog_loader.py`
- [ ] T007 Implementar `src/vigilancia_multiagente/enterprise/tooling/catalog_loader.py` (~200 LOC): clase CatalogLoader con metodo `load(path: Path) -> list[CatalogEntry]`, parsea catalog.yaml con pyyaml, retorna lista de dataclass CatalogEntry con todos los campos del catalogo, valida campos obligatorios al cargar. Hacer T006 verde en `src/vigilancia_multiagente/enterprise/tooling/catalog_loader.py`
- [ ] T008 Extender `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` (modificacion aditiva): metodo `load_catalog(entries: list[CatalogEntry])` que registra metadata de cada entrada; filtro `mvp_only: bool = True` en `discover(role, intent, tenant_id)` que excluye entradas con mvp=false; indexar campo capabilities + descripcion del CatalogEntry (YAML) para discovery semantico en `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`
- [ ] T009 Wirear CatalogLoader en `src/vigilancia_multiagente/api/dependencies.py`: al arranque, instanciar CatalogLoader, cargar `config/tools/catalog.yaml`, alimentar ToolRegistry con las entradas. NO tocar wires existentes del 2.0 en `src/vigilancia_multiagente/api/dependencies.py`
- [ ] T010 Ejecutar `pytest tests/enterprise/tooling/test_catalog_loader.py` y confirmar 5 tests verdes. Verificar que ToolRegistry reporta 79 entradas cargadas y filtro MVP retorna 20

---

## Phase 3: Import refactorizado de tools MVP Tier 1

Objetivo: importar file_system de Hermes + crear 3 tools nuevas (template_render, docx_generate, pdf_generate) en builtin/documents/, todas con ToolWrapper, modulos <=400 LOC, header de atribucion.

Dependencia: Phase 2 completada (ToolRegistry con catalogo cargado).

Independent Test Criteria: `pytest tests/enterprise/tooling/builtin/documents/` verde; cada archivo <=400 LOC verificable con script; header de atribucion presente en archivos Hermes; 4 tools registradas en ToolRegistry.

- [ ] T011 [P] Crear estructura de directorios `src/vigilancia_multiagente/enterprise/tooling/builtin/__init__.py` y `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/__init__.py` como markers de subpaquete en `src/vigilancia_multiagente/enterprise/tooling/builtin/`
- [ ] T012 Crear test `tests/enterprise/tooling/builtin/documents/test_file_system.py` con 5 tests: file_system implementa protocolo ToolWrapper (name, domain, is_external_mcp=False, healthcheck, execute); read de archivo existente retorna contenido; write crea archivo en path permitido; path traversal bloqueado por _file_safety; execute con operacion invalida retorna error claro en `tests/enterprise/tooling/builtin/documents/test_file_system.py`
- [ ] T013 Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_safety.py` (~200 LOC): validacion de paths, prevencion de traversal, permisos. Header: `# Adapted from Hermes Agent -- original: agent/file_safety.py -- License: MIT` en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_safety.py`
- [ ] T014 [P] Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_operations.py` (~350 LOC): operaciones read, write, patch, list. Header: `# Adapted from Hermes Agent -- original: tools/file_operations.py -- License: MIT` en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_operations.py`
- [ ] T015 [P] Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_state.py` (~200 LOC): tracking de estado de archivos. Header: `# Adapted from Hermes Agent -- original: tools/file_state.py -- License: MIT` en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_state.py`
- [ ] T016 Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/file_system.py` (~200 LOC): wrapper ToolWrapper que orquesta _file_operations, _file_state, _file_safety. Implementa name="file_system", domain="documents", is_external_mcp=False, healthcheck(), execute(). Header: `# Adapted from Hermes Agent -- original: tools/file_tools.py -- License: MIT`. Hacer T012 verde en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/file_system.py`
- [ ] T017 [P] Crear test `tests/enterprise/tooling/builtin/documents/test_template_render.py` con 3 tests: implementa ToolWrapper; renderiza template Jinja2 MD con variables; template inexistente retorna error claro en `tests/enterprise/tooling/builtin/documents/test_template_render.py`
- [ ] T018 [P] Crear test `tests/enterprise/tooling/builtin/documents/test_docx_generate.py` con 3 tests: implementa ToolWrapper; genera DOCX valido desde datos estructurados; datos vacios retorna error en `tests/enterprise/tooling/builtin/documents/test_docx_generate.py`
- [ ] T019 [P] Crear test `tests/enterprise/tooling/builtin/documents/test_pdf_generate.py` con 3 tests: implementa ToolWrapper; genera PDF valido desde HTML; HTML malformado retorna error en `tests/enterprise/tooling/builtin/documents/test_pdf_generate.py`
- [ ] T020 Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/template_render.py` (~300 LOC): wrapper ToolWrapper sobre Jinja2, renderiza templates MD/HTML/DOCX desde config/templates/. Inputs: template_name (str), variables (dict[str, object]), output_format (md|html|docx). Output: dict[str, object] con rendered_content (str) y output_path (str|None). Hacer T017 verde en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/template_render.py`
- [ ] T021 Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/docx_generate.py` (~250 LOC): wrapper ToolWrapper sobre python-docx, genera DOCX desde datos estructurados. Inputs: title (str), sections (list[dict] con heading+body), template_path (str|None), output_path (str). Output: dict[str, object] con output_path (str) y page_count (int). Hacer T018 verde en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/docx_generate.py`
- [ ] T022 Implementar `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/pdf_generate.py` (~250 LOC): wrapper ToolWrapper sobre WeasyPrint, genera PDF desde HTML/Markdown renderizado. Inputs: html_content (str), css_path (str|None), output_path (str). Output: dict[str, object] con output_path (str) y page_count (int). Hacer T019 verde en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/pdf_generate.py`
- [ ] T023 Registrar las 4 tools (file_system, template_render, docx_generate, pdf_generate) en ToolRegistry al arranque via builtin/documents/__init__.py. Verificar que ToolRegistry las lista con domain="documents" en `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/__init__.py`
- [ ] T024 Ejecutar `pytest tests/enterprise/tooling/builtin/documents/` y confirmar todos los tests verdes. Verificar con script que cada archivo .py en builtin/documents/ tiene <=400 LOC. Verificar con grep que archivos importados de Hermes contienen header de atribucion

---

## Phase 4: Discovery semantico con catalogo completo

Objetivo: indexar 79 entradas para discovery semantico, implementar filtros pre-ranking, 3 niveles de detalle (ToolCard, ToolSummary, ToolDocs).

Dependencia: Phase 2 (ToolRegistry con catalogo) y Phase 3 (tools Tier 1 registradas).

Independent Test Criteria: `pytest tests/enterprise/tooling/test_catalog_discovery.py` verde; precision@5 >= 0.6 en 20 queries; filtros MVP y gating funcionan; 3 niveles retornan datos correctos.

- [ ] T025 Crear test `tests/enterprise/tooling/test_catalog_discovery.py` con 6 tests: discover(role="researcher", intent="buscar papers academicos", tenant_id=<UUID>) retorna arxiv, openalex, google_scholar en top-5; filtro MVP excluye tools con mvp=false; gating excluye tools sin credenciales configuradas (requires_key=true y env_var ausente); ToolCard retorna id + descripcion <=80 chars + dominio; ToolSummary retorna schema inputs/outputs; ToolDocs retorna docs largas solo para tool seleccionada en `tests/enterprise/tooling/test_catalog_discovery.py`
- [ ] T026 Implementar indexacion de embeddings en ToolRegistry: al ejecutar load_catalog, generar embeddings de capabilities + descripcion de cada CatalogEntry (metadata YAML, NO atributos del Protocol ToolWrapper) usando GeminiEmbeddingGateway existente del 2.0, almacenar en memoria (regenerados al arranque) en `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`
- [ ] T027 Implementar filtros pre-ranking en metodo discover(): excluir status != active, excluir mvp=false (en primera entrega), excluir tools con requires_key=true y env_var no configurada (tool-gating) en `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`
- [ ] T028 Implementar 3 niveles de detalle en ToolRegistry: ToolCard (id + descripcion corta <=80 chars + dominio + permisos + costo + estado), ToolSummary (schema inputs/outputs + ejemplos cortos, cargado solo para top-k), ToolDocs (docs largas, cargado solo para tool seleccionada). Hacer T025 verde en `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py`
- [ ] T029 Crear test de precision `tests/enterprise/tooling/test_catalog_discovery_precision.py` con set de 20 queries representativas de los 4 dominios MVP, verificar precision@5 >= 0.6 en `tests/enterprise/tooling/test_catalog_discovery_precision.py`
- [ ] T030 Ejecutar `pytest tests/enterprise/tooling/test_catalog_discovery.py tests/enterprise/tooling/test_catalog_discovery_precision.py` y confirmar todos verdes. Ajustar descripciones/capabilities en catalog.yaml si precision es insuficiente

---

## Phase 5: Validacion integral y cierre

Objetivo: verificar SC-001 a SC-007, cero regresiones en 2.0, coherencia completa del catalogo.

Dependencia: Phases 1-4 completadas.

Independent Test Criteria: todos los SC pasan con evidencia; pytest completo verde; check-layer-imports sin violaciones; catalogo con 79 entradas validadas.

- [ ] T031 Ejecutar `python scripts/validate_catalog.py` y confirmar 0 errores (SC-007)
- [ ] T032 [P] Verificar que catalogo tiene exactamente 79 entradas con todos los campos obligatorios completos (SC-001)
- [ ] T033 [P] Verificar coherencia LOC vs strategy: 100% de entradas python + loc<5000 tienen runtime python_internal; 100% de entradas con otro lenguaje o loc>=5000 tienen runtime process_stdio o process_http (SC-002)
- [ ] T034 [P] Verificar que las 20 entradas MVP coinciden exactamente con inventario de `plan vigilador 3.0/00b-mvp-scope-y-cronograma.md` (SC-003)
- [ ] T035 [P] Verificar que toda tool importada en builtin/documents/ cumple <=400 LOC por modulo con script automatizado (SC-005)
- [ ] T036 [P] Verificar header de atribucion en archivos importados de Hermes con `grep -r "Adapted from Hermes Agent" src/vigilancia_multiagente/enterprise/tooling/builtin/` (SC-006)
- [ ] T037 Ejecutar `pytest` completo (2.0 + 3.0) y confirmar cero regresiones. Los 14 MCP providers del 2.0 + serper_patents (alias de capacidad) en `infra/mcp/mcp-providers.json` intactos
- [ ] T038 [P] Ejecutar `python scripts/check-layer-imports.py` y confirmar 0 violaciones nuevas
- [ ] T039 Verificar SC-004: ejecutar test de precision de discovery semantico y confirmar precision@5 >= 0.6 en set de 20 queries

---

## Dependencies

- **Phase 1** must complete before **Phase 2** (catalogo validado requerido para CatalogLoader).
- **Phase 2** must complete before **Phase 3** (ToolRegistry con catalogo requerido para registrar tools).
- **Phase 2** must complete before **Phase 4** (catalogo cargado requerido para indexar embeddings).
- **Phase 3** must complete before **Phase 4** (tools Tier 1 registradas para discovery completo).
- **Phases 1-4** must complete before **Phase 5** (validacion integral requiere todo implementado).
- **Spec 009** must be implemented before Phases 2-4 (ToolWrapper, ToolRegistry, GeminiEmbeddingGateway).
- Phase 1 (T001-T005) puede ejecutarse independientemente de spec 009.
- Dentro de Phase 3: T011 (estructura) bloquea T013-T016, T020-T023. T012 (test file_system) bloquea T016 (implementacion). T013+T014+T015 bloquean T016 (file_system los importa). T017 bloquea T020; T018 bloquea T021; T019 bloquea T022.
- Dentro de Phase 4: T025 (test discovery) bloquea T026-T028 (implementacion). T026+T027+T028 bloquean T029 (test precision).

---

## Parallel Execution Examples

### Phase 1 Parallel Block

- T001 y T002 son secuenciales (T002 depende del schema para validar).
- T003 es paralelo a T001+T002 (archivo distinto, sin dependencia).
- T004 depende de T001 (necesita resultados del inventario) y T002 (necesita schema).
- T005 depende de T004.

### Phase 2 Parallel Block

- T006 (test) primero, luego T007 (implementacion).
- T008 y T009 dependen de T007.
- T006 puede escribirse en paralelo con Phase 1 si el contrato CatalogEntry esta definido.

### Phase 3 Parallel Block

Tras T011 (estructura):

- **Bloque A (file_system)**: T012 -> T013, T014 [P], T015 [P] -> T016.
- **Bloque B (tools nuevas tests)**: T017 [P], T018 [P], T019 [P] en paralelo (archivos distintos).
- **Bloque C (tools nuevas impl)**: T020, T021, T022 tras sus tests respectivos (pueden ser paralelos entre si).
- T023 y T024 secuenciales al final de Phase 3.

### Phase 5 Parallel Block

- Run T031, T032, T033, T034, T035, T036, T038 en paralelo (verificaciones independientes sobre archivos distintos).
- T037 secuencial (pytest completo).
- T039 secuencial (depende de discovery funcional).

---

## Implementation Strategy

1. **Cerrar Phase 1 primero**: inventario + catalogo + validacion. Esto es independiente de spec 009 y produce el artefacto SSOT que todo lo demas consume. Ejecutable inmediatamente.
2. **Phase 2 tras spec 009**: CatalogLoader y extension de ToolRegistry requieren que los contratos base existan. Si spec 009 no esta lista, Phase 1 se adelanta y Phase 2 espera.
3. **Phase 3 en paralelo por tool**: file_system (import Hermes) y las 3 tools nuevas pueden distribuirse entre desarrolladores tras tener la estructura creada.
4. **Phase 4 cierra el discovery**: requiere catalogo cargado + tools registradas. Es la integracion final del sistema de busqueda semantica.
5. **Phase 5 como gate de calidad**: nada se considera entregado hasta que los 7 SC pasen con evidencia automatizada.
6. **Principio quirurgico**: en ningun momento se modifica `infra/mcp/mcp-providers.json` ni codigo del 2.0. El catalogo referencia los 15 entradas Tier 2 del 2.0 (14 MCP providers + serper_patents como alias de capacidad) con `source: preservado_2.0` pero no los altera.

---

## Format Validation

Todas las tareas T001..T039 siguen el formato requerido:
- Checkbox `- [ ]` al inicio.
- Task ID secuencial (T001..T039).
- Marcador `[P]` solo en tareas paralelizables (archivos distintos sin dependencia).
- Descripcion con accion + path concreto del archivo.
- Traza a FR/SC en Independent Test Criteria por fase.

**Total task count**: 39 tareas.
**Task count per phase**:
- Phase 1 (Inventario + catalogo): 5
- Phase 2 (CatalogLoader + ToolRegistry): 5
- Phase 3 (Import tools Tier 1): 14
- Phase 4 (Discovery semantico): 6
- Phase 5 (Validacion integral): 9

**MVP scope**: las 39 tareas cubren las 20 tools MVP activas. Las 59 tools roadmap solo se documentan en catalog.yaml con `mvp: false` (YAGNI). Cero codigo de produccion para ellas.
