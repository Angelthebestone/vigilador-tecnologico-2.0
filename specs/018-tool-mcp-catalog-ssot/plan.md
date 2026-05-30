# Implementation Plan: Catalogo SSOT de Tools/MCPs con Discovery Semantico

**Feature ID**: 018-tool-mcp-catalog-ssot
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El Vigilador 3.0 opera con 79 capacidades distribuidas en 4 tiers (Python interno, MCPs externos STDIO/HTTP, TS traducidos, sub-tools locales). No existe un catalogo unico y autoritativo (SSOT) que clasifique cada tool/MCP por estrategia de extraccion, ni un mecanismo de discovery semantico que permita al agente encontrar la tool correcta sin recibir el catalogo completo en prompt. Las fuentes externas (Hermes Agent, OpenClaw) estan clonadas en `documentation/` pero no se ha medido formalmente el LOC por unidad para aplicar la regla de importacion (<5000 LOC Python -> importar refactorizado; otros lenguajes o >=5000 LOC -> MCP externo). Sin este inventario validado, no se puede proceder a la extraccion ni al registro uniforme en el `ToolRegistry`.

## Approach

Ejecutar un inventario formal de LOC sobre las fuentes en `documentation/hermes agent/hermes-agent/tools/` y `documentation/hermes agent/hermes-agent/optional-mcps/`, medir cada unidad individualmente (archivo .py o subcarpeta autocontenida), registrar los resultados en `config/tools/catalog.yaml` con campos normalizados. Aplicar la regla de importacion por unidad para asignar `strategy` y `runtime`. Importar refactorizado (<=400 LOC por modulo, header de atribucion) las tools MVP que califiquen como `python_internal` a `src/vigilancia_multiagente/enterprise/tooling/builtin/<dominio>/`. Registrar todas las 79 entradas en el `ToolRegistry` con discovery semantico. Solo las 20 tools MVP se activan operacionalmente; las 59 restantes quedan documentadas con `mvp: false`.

---

## Technical Context

| Area | Decision |
|------|----------|
| Catalogo SSOT | Archivo YAML plano en `config/tools/catalog.yaml`. Sin DB adicional (constitucion #2 simplicidad). |
| Regla de importacion | Por unidad individual: archivo .py o subcarpeta autocontenida. <5000 LOC Python -> `python_internal`; otros lenguajes o >=5000 -> `process_stdio`/`process_http`. |
| Conteo LOC | Suma de lineas de archivos `.py` excluyendo `test*/`, `docs*/`, `*_test.py`, `conftest.py`. Herramienta: script PowerShell o Python en `scripts/`. |
| Destino import | `src/vigilancia_multiagente/enterprise/tooling/builtin/<dominio>/` segun campo `domain` del catalogo. |
| Modularizacion | SRP, SoC, DIP. Modulos <=400 LOC. Header de atribucion obligatorio para archivos de Hermes. |
| ToolWrapper | Protocolo definido en spec 009 (`enterprise/tooling/tool_wrapper.py`). Esta spec lo usa, no lo redefine. Cita de contrato: `execute() -> dict[str, object]`, `healthcheck() -> HealthcheckResult`. |
| ToolRegistry | Definido en spec 009 (`enterprise/tooling/tool_registry.py`). Esta spec extiende con clasificacion por estrategia y carga desde `catalog.yaml`. Firma real de discovery: `discover(self, role: str, intent: str, tenant_id: UUID)`. |
| Discovery semantico | Reusa `GeminiEmbeddingGateway` existente del 2.0. Tres niveles: ToolCard, ToolSummary, ToolDocs. |
| Fuentes reales | `documentation/hermes agent/hermes-agent/tools/` (~80 archivos .py, subcarpetas `environments/`, `computer_use/`). `documentation/hermes agent/hermes-agent/optional-mcps/` (2 subcarpetas: `n8n/`, `linear/`). `documentation/openclaw/openclaw/` (TypeScript, solo referencia conceptual). |
| MVP scope | 20 capacidades activas (4 Tier 1 + 16 Tier 2). 59 restantes documentadas con `mvp: false`. |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Constitucion v1.2.0 #5 Cambios Quirurgicos | Cero modificaciones al 2.0. `infra/mcp/mcp-providers.json` intacto. Los 15 MCPs del 2.0 (14 providers + serper_patents como alias de capacidad del MCP `serper`) se referencian en el catalogo pero no se alteran. |
| Constitucion v1.2.0 #2 Simplicidad | Catalogo es YAML plano. Cero ORM, cero DB adicional para persistirlo. |
| Constitucion v1.2.0 #3 Modularidad | Tools importadas se refactorizan en modulos <=400 LOC con responsabilidad unica. |
| YAGNI | Las 59 tools roadmap se documentan pero NO se implementan. Cero wrappers, cero codigo para ellas. |
| Spec 009 dependencia | `ToolWrapper`, `ToolRegistry`, `ToolCard`, `ToolSummary`, `ToolDocs` ya definidos. Esta spec los consume. |
| OpenClaw es TypeScript | No se importa codigo de OpenClaw. Solo referencia conceptual. Aplica regla: otro lenguaje -> MCP externo. |
| Hermes tools individuales grandes | Archivos como `mcp_tool.py` (156KB), `browser_tool.py` (165KB), `terminal_tool.py` (114KB) superan 5000 LOC individualmente -> clasificados como MCP externo por unidad. |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `config/tools/catalog.yaml` | Catalogo SSOT con las 79 entradas. Campos obligatorios: id, domain, source, strategy, runtime, status, owner, license, capabilities, requires_key, env_var, healthcheck, update_policy, loc_count, loc_validated, language, mvp. Campos opcionales: notes, dedup_group, source_repo, pinned_version, last_audit_date. |
| `config/tools/catalog-schema.json` | JSON Schema para validar `catalog.yaml`. Garantiza campos obligatorios y valores permitidos. |
| `scripts/inventory_loc.py` | Script que recorre fuentes en `documentation/`, mide LOC por unidad (.py excluyendo tests/docs), genera reporte y actualiza `catalog.yaml`. |
| `scripts/validate_catalog.py` | Script que valida `catalog.yaml` contra `catalog-schema.json`. Verifica regla de importacion (LOC vs strategy). |
| `src/vigilancia_multiagente/enterprise/tooling/catalog_loader.py` | Carga `catalog.yaml` al arranque, parsea entradas, alimenta al `ToolRegistry` con metadata de estrategia. |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/__init__.py` | Marker del subpaquete builtin. |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/__init__.py` | Marker dominio documents. |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/file_system.py` | Tool `file_system` importada de Hermes (refactorizada, <=400 LOC, wrapper sobre modulos internos). |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_operations.py` | Modulo interno: operaciones de archivo (read, write, patch). Refactorizado de `file_operations.py` Hermes. |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_state.py` | Modulo interno: tracking de estado de archivos. Refactorizado de `file_state.py` Hermes. |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/_file_safety.py` | Modulo interno: validaciones de seguridad de paths. Refactorizado de `agent/file_safety.py` Hermes. |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/template_render.py` | Tool `template_render` (NUEVO, Jinja2 sobre MD/HTML/DOCX). |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/docx_generate.py` | Tool `docx_generate` (NUEVO, python-docx). |
| `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/pdf_generate.py` | Tool `pdf_generate` (NUEVO, WeasyPrint). |
| `tests/enterprise/tooling/test_catalog_loader.py` | Tests de carga del catalogo, validacion de schema, regla de importacion. |
| `tests/enterprise/tooling/test_catalog_discovery.py` | Tests de discovery semantico sobre entradas del catalogo. |
| `tests/enterprise/tooling/builtin/documents/test_file_system.py` | Tests de la tool file_system importada. |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` | Integrar `CatalogLoader` para cargar metadata de estrategia al arranque. Anadir filtro `mvp_only` al discovery. |
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear `CatalogLoader` como dependencia del `ToolRegistry`. |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Alignment**:
  - **Pensar Antes de Codificar**: Fase 1 entera dedicada a inventario y medicion antes de importar codigo. Supuestos de LOC se validan contra fuentes reales. La regla de importacion se aplica POR UNIDAD, no al repo completo.
  - **Simplicidad Obligatoria**: Catalogo es un archivo YAML plano. Script de inventario es un script utilitario simple. Cero abstracciones especulativas. Las 59 tools roadmap solo se documentan, no se implementan.
  - **Modularidad Primero**: Tools importadas se refactorizan en modulos <=400 LOC. `CatalogLoader` es un modulo separado del `ToolRegistry`. Cada dominio tiene su subcarpeta.
  - **Cambios Quirurgicos y Trazables**: Cero cambios al 2.0. `infra/mcp/mcp-providers.json` intacto. Solo 2 archivos existentes se modifican (ambos en modo aditivo). Header de atribucion en cada archivo importado.
  - **Entrega Verificable**: Cada fase produce artefactos medibles. Script de validacion automatizado. SC-001 a SC-007 verificables por scripts.
- **Diseno de Software**: SRP (cada modulo un concern), SoC (catalogo separado de registry separado de discovery), DIP (CatalogLoader inyectado al ToolRegistry), DRY (catalogo es unica fuente de verdad), KISS (YAML plano, sin ORM), YAGNI (59 tools solo documentadas).

---

## Phases

### Phase 1 -- Inventario de LOC y generacion del catalogo SSOT

1. Crear `scripts/inventory_loc.py` que recorra:
   - `documentation/hermes agent/hermes-agent/tools/*.py` (archivos individuales).
   - `documentation/hermes agent/hermes-agent/tools/environments/*.py` (subcarpeta).
   - `documentation/hermes agent/hermes-agent/tools/computer_use/*.py` (subcarpeta).
   - `documentation/hermes agent/hermes-agent/optional-mcps/*/` (cada subcarpeta como unidad).
   - Para cada unidad: contar lineas de archivos `.py` excluyendo paths que contengan `test`, `docs`, archivos `*_test.py` y `conftest.py`.
   - Registrar: nombre, loc_count, language (python/typescript/yaml), ruta fuente.
2. Ejecutar el script y registrar resultados. Aplicar la regla de importacion:
   - Python Y loc_count < 5000 -> `strategy` segun doc 06 (COPY-HERMES o WRAP-SDK), `runtime: python_internal`.
   - Python Y loc_count >= 5000 -> `strategy: MCP-EXTERNO`, `runtime: process_stdio`.
   - Otro lenguaje -> `strategy: MCP-EXTERNO`, `runtime: process_stdio` o `process_http`.
3. Crear `config/tools/catalog.yaml` con las 79 entradas completas:
   - 20 entradas con `mvp: true` (4 Tier 1 documents + 16 Tier 2 preservados del 2.0).
   - 59 entradas con `mvp: false` (roadmap).
   - Campos obligatorios: id, domain, source, strategy, runtime, status, owner, license, capabilities, requires_key, env_var, healthcheck, update_policy, loc_count, loc_validated, language, mvp.
   - Campos opcionales: notes, dedup_group, source_repo, pinned_version, last_audit_date.
4. Crear `config/tools/catalog-schema.json` con validacion de:
   - Campos obligatorios presentes.
   - `strategy` es uno de: COPY-HERMES, WRAP-SDK, MCP-EXTERNO, TRANSLATE-THIN, NUEVO.
   - `runtime` es uno de: python_internal, process_stdio, process_http.
   - `language` es uno de: python, typescript, go, rust, yaml.
   - `mvp` es boolean.
   - Coherencia: si `language != python` entonces `runtime != python_internal`.
   - Coherencia: si `language == python` Y `loc_count < 5000` Y `loc_validated == true` entonces `runtime == python_internal`.
5. Crear `scripts/validate_catalog.py` que ejecute la validacion de schema + reglas de coherencia.

**Output**: `config/tools/catalog.yaml` con 79 entradas validadas, `catalog-schema.json`, scripts de inventario y validacion. `loc_validated: true` para todas las unidades medidas directamente; `loc_validated: false` para las que no tienen fuente clonada.

**Verificacion**: `python scripts/validate_catalog.py` pasa sin errores. Exactamente 20 entradas con `mvp: true`. Exactamente 79 entradas totales.

---

### Phase 2 -- CatalogLoader y registro en ToolRegistry

1. Crear `src/vigilancia_multiagente/enterprise/tooling/catalog_loader.py` (~200 LOC):
   - Clase `CatalogLoader` con metodo `load(path: Path) -> list[CatalogEntry]`.
   - Parsea `catalog.yaml` usando `pyyaml` (ya disponible en el proyecto).
   - Retorna lista de `CatalogEntry` (dataclass con todos los campos del catalogo).
   - Valida schema basico al cargar (campos obligatorios presentes).
2. Extender `ToolRegistry` (modificacion aditiva):
   - Metodo `load_catalog(entries: list[CatalogEntry])` que registra metadata de cada entrada.
   - Filtro `mvp_only: bool = True` en `discover(role, intent, tenant_id)` que excluye entradas con `mvp: false`.
   - Cada entrada del catalogo se indexa para discovery semantico usando su campo `capabilities` + descripcion.
3. Wirear en `api/dependencies.py`: al arranque, `CatalogLoader` carga `config/tools/catalog.yaml` y alimenta al `ToolRegistry`.
4. Tests `tests/enterprise/tooling/test_catalog_loader.py`:
   - Carga exitosa de catalogo con 79 entradas.
   - Falla si campo obligatorio falta.
   - Falla si `strategy` tiene valor invalido.
   - Filtro `mvp_only` retorna exactamente 20 entradas.

**Output**: `CatalogLoader` funcional, `ToolRegistry` extendido con metadata de catalogo, tests verdes.

**Verificacion**: Tests pasan. `ToolRegistry` cargado con 79 entradas al arranque. Filtro MVP retorna 20.

---

### Phase 3 -- Import refactorizado de tools MVP Tier 1

1. Crear estructura `src/vigilancia_multiagente/enterprise/tooling/builtin/documents/`.
2. Importar `file_system` desde Hermes (`tools/file_tools.py` + `tools/file_operations.py` + `tools/file_state.py` + `agent/file_safety.py`):
   - Refactorizar en modulos <=400 LOC:
     - `file_system.py`: wrapper ToolWrapper, orquesta operaciones (~200 LOC).
     - `_file_operations.py`: read, write, patch, list (~350 LOC).
     - `_file_state.py`: tracking de estado (~200 LOC).
     - `_file_safety.py`: validacion de paths, permisos (~200 LOC).
   - Header de atribucion en cada archivo:
     ```
     # Adapted from Hermes Agent -- original: tools/<filename>.py -- License: MIT
     ```
   - Reemplazar imports de Hermes (`hermes_cli.config`, `hermes_constants`) por config propio.
   - Implementar protocolo `ToolWrapper` (name, domain, is_external_mcp=False, requires_auth=False, healthcheck(), execute()).
3. Crear `template_render.py` (NUEVO, ~300 LOC):
   - Wrapper ToolWrapper sobre Jinja2.
   - Renderiza templates MD/HTML/DOCX desde `config/templates/`.
   - Inputs: `template_name: str`, `variables: dict[str, object]`, `output_format: str` (md|html|docx).
   - Output: `dict[str, object]` con `rendered_content: str` y `output_path: str | None`.
4. Crear `docx_generate.py` (NUEVO, ~250 LOC):
   - Wrapper ToolWrapper sobre python-docx.
   - Genera documentos DOCX desde datos estructurados.
   - Inputs: `title: str`, `sections: list[dict]` (heading + body), `template_path: str | None`, `output_path: str`.
   - Output: `dict[str, object]` con `output_path: str` y `page_count: int`.
5. Crear `pdf_generate.py` (NUEVO, ~250 LOC):
   - Wrapper ToolWrapper sobre WeasyPrint.
   - Genera PDF desde HTML/Markdown renderizado.
   - Inputs: `html_content: str`, `css_path: str | None`, `output_path: str`.
   - Output: `dict[str, object]` con `output_path: str` y `page_count: int`.
6. Registrar las 4 tools en el `ToolRegistry` al arranque.
7. Tests unitarios para cada tool importada/nueva.

**Output**: 4 tools Tier 1 MVP operativas en `builtin/documents/`, registradas en ToolRegistry, tests verdes.

**Verificacion**: Cada archivo <=400 LOC (verificable con `wc -l`). Header de atribucion presente (verificable con grep). `ToolWrapper` implementado correctamente. Tests pasan.

---

### Phase 4 -- Discovery semantico con catalogo completo

1. Indexar las 79 entradas del catalogo para discovery semantico:
   - Generar embeddings de `capabilities` + descripcion de cada entrada del `CatalogEntry` (YAML) usando `GeminiEmbeddingGateway`. Nota: se indexa metadata del catalogo YAML, NO atributos del Protocol `ToolWrapper` (que no expone `tags` ni `capabilities`).
   - Almacenar embeddings en memoria (no persistidos; se regeneran al arranque).
2. Implementar filtros previos al ranking en `discover()`:
   - `status == active` (excluir deprecated, blocked).
   - `mvp == true` (en primera entrega).
   - Credenciales disponibles (tool-gating: si `requires_key == true` y env_var no configurada, excluir).
3. Implementar tres niveles de detalle:
   - `ToolCard`: id + descripcion corta (<=80 chars) + dominio + permisos + costo + estado.
   - `ToolSummary`: schema inputs/outputs + ejemplos cortos (cargado solo para top-k).
   - `ToolDocs`: docs largas (cargado solo para tool seleccionada).
4. Tests `tests/enterprise/tooling/test_catalog_discovery.py`:
   - `discover(role="researcher", intent="buscar papers academicos", tenant_id=<UUID>)` retorna arxiv, openalex, google_scholar en top-5.
   - Filtro MVP excluye tools con `mvp: false`.
   - Gating excluye tools sin credenciales configuradas.
   - Precision@5 >= 0.6 en set de 20 queries representativas.

**Output**: Discovery semantico operativo sobre las 79 entradas, filtrado por MVP/gating/status, tests verdes.

**Verificacion**: Tests de precision pasan. Filtros funcionan correctamente. Tres niveles de detalle retornan datos correctos.

---

### Phase 5 -- Validacion integral y cierre

1. Ejecutar `scripts/validate_catalog.py` -- debe pasar sin errores.
2. Verificar que el catalogo tiene exactamente 79 entradas con todos los campos obligatorios.
3. Verificar coherencia LOC vs strategy:
   - 100% de entradas con `language: python` Y `loc_count < 5000` tienen `runtime: python_internal`.
   - 100% de entradas con `language != python` O `loc_count >= 5000` tienen `runtime: process_stdio` o `process_http`.
4. Verificar que las 20 entradas MVP coinciden con el inventario de `00b-mvp-scope-y-cronograma.md`.
5. Verificar que toda tool importada cumple <=400 LOC por modulo.
6. Verificar header de atribucion en archivos importados de Hermes.
7. Correr `pytest` completo -- cero regresiones en el 2.0.
8. Correr `scripts/check-layer-imports.py` -- sin nuevas violaciones.

**Output**: Spec 018 completado. Catalogo SSOT validado, tools MVP importadas, discovery semantico operativo.

**Verificacion**: SC-001 a SC-007 cumplidos con evidencia.

---

## Rollout Strategy

- **Incremental por fase**: cada fase produce artefactos verificables. No se avanza a la siguiente sin validacion.
- **Backward compatibility**: cero cambios al 2.0. Los 15 MCPs del 2.0 (tavily, exa, jina, brave, firecrawl, serper, google_scholar, arxiv, fetch, sandbox, markitdown, minimax-image, openalex, playwright + serper_patents como alias de capacidad) en `infra/mcp/mcp-providers.json` siguen operando sin modificacion. El catalogo los referencia como entradas con `source: preservado_2.0` y `strategy: MCP-EXTERNO`.
- **Coexistencia**: el catalogo SSOT es aditivo. No reemplaza ni modifica la configuracion existente de MCPs del 2.0.
- **Feature flags**: cero necesarios. La existencia del catalogo no afecta al 2.0.
- **Dependencia de spec 009**: las fases 2-4 requieren que `ToolWrapper` y `ToolRegistry` de spec 009 esten implementados. La fase 1 (inventario + catalogo YAML) puede ejecutarse independientemente.

---

## Success Criteria

- **SC-001**: El catalogo SSOT contiene exactamente 79 entradas con todos los campos obligatorios completos y validados por schema (`scripts/validate_catalog.py` pasa sin errores).
- **SC-002**: El 100% de las entradas con `language: python` y `loc_count < 5000` tienen `runtime: python_internal`; el 100% de las entradas con lenguaje != Python o `loc_count >= 5000` tienen `runtime: process_stdio` o `runtime: process_http`.
- **SC-003**: Las 20 entradas MVP (`mvp: true`) coinciden exactamente con el inventario de 00b-mvp-scope-y-cronograma.md (4 Tier 1 + 16 Tier 2). Los 16 Tier 2 son: tavily, exa, jina, brave, firecrawl, serper, google_scholar, arxiv, fetch, sandbox, markitdown, minimax-image, openalex, playwright, serper_patents + google-workspace-mcp.
- **SC-004**: `ToolRegistry.discover(role, intent, tenant_id)` retorna resultados relevantes (precision@5 >= 0.6 en set de 20 queries de prueba representativas de los 4 dominios MVP).
- **SC-005**: Toda tool importada al repo cumple la regla de <=400 LOC por modulo, verificable por script automatizado.
- **SC-006**: Toda tool importada desde Hermes contiene el header de atribucion requerido (FR-011), verificable por grep automatizado.
- **SC-007**: El catalogo YAML pasa validacion de schema JSON sin errores al ejecutar el validador.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`).
- **Justification**:
  - **Pensar Antes de Codificar**: Fase 1 completa dedicada a inventario y medicion antes de escribir codigo de produccion. Regla de importacion validada contra fuentes reales (archivos en `documentation/hermes agent/hermes-agent/tools/` medidos individualmente). Supuestos explicitos sobre LOC por unidad vs repo completo.
  - **Simplicidad Obligatoria**: Catalogo es YAML plano (cero DB). Scripts de validacion son utilitarios simples. 59 tools roadmap solo documentadas, cero codigo para ellas. Cero abstracciones especulativas.
  - **Modularidad Primero**: `CatalogLoader` separado del `ToolRegistry`. Tools importadas refactorizadas en modulos <=400 LOC con SRP. Cada dominio en su subcarpeta. Discovery semantico como concern separado.
  - **Cambios Quirurgicos y Trazables**: Solo 2 archivos existentes modificados (ambos aditivos). `infra/mcp/mcp-providers.json` intacto. Header de atribucion en cada archivo importado. Traza: spec -> doc 06 -> catalogo -> codigo.
  - **Entrega Verificable**: 7 success criteria medibles. Scripts automatizados para validacion. Cada fase con output y verificacion explicitos.
  - **Diseno de Software**: SRP (modulos con responsabilidad unica), SoC (catalogo/registry/discovery separados), DIP (CatalogLoader inyectado), DRY (catalogo es unica fuente de verdad), KISS (YAML plano), YAGNI (59 tools solo documentadas), OCP (ToolRegistry extendido sin modificar su contrato base).
