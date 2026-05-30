# Feature Specification: Catalogo SSOT de Tools/MCPs con Discovery Semantico y Estrategia de Extraccion

**Feature ID**: 018-tool-mcp-catalog-ssot
**Created**: 2026-05-29
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/06-catalogo-tools-y-extraccion.md](../../plan%20vigilador%203.0/06-catalogo-tools-y-extraccion.md) (SSOT operacional)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md) (scope MVP vs roadmap)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md) (decisiones C0)

---

## Problem Statement

El Vigilador 3.0 opera con 79 capacidades distribuidas en 4 tiers (Python interno, MCPs externos STDIO/HTTP, TS traducidos, sub-tools locales). Sin un catalogo unico y autoritativo (SSOT) que clasifique cada tool/MCP por estrategia de extraccion, el sistema no puede:

1. Decidir automaticamente si una capacidad se ejecuta in-process (Python importado) o como proceso externo (MCP STDIO/HTTP).
2. Aplicar discovery semantico para que el agente encuentre la tool correcta sin recibir el catalogo completo en prompt.
3. Mantener trazabilidad de origen, licencia, estado y politica de actualizacion por cada capacidad.

El usuario requiere ademas una regla operativa clara: **importar al repo** (refactorizado y modularizado) todo MCP escrito en Python con menos de 5000 lineas de codigo fuente; **mantener como MCP externo** los escritos en otros lenguajes o con 5000+ lineas. Esta regla necesita un criterio de medicion formal, un destino en `src/` y un contrato uniforme (`ToolWrapper` + `ToolRegistry`).

---

## Scope Boundaries

### In Scope

- **Catalogo SSOT persistido**: registro unico de las 79 capacidades con campos normalizados (id, domain, source, strategy, runtime, status, owner, license, capabilities, requires_key, env_var, healthcheck, update_policy).
- **Clasificacion por estrategia de extraccion**: cada entrada clasificada como COPY-HERMES, WRAP-SDK, MCP-EXTERNO, TRANSLATE-THIN o NUEVO segun reglas del doc 06.
- **Regla de importacion por lineas**: MCPs Python con <5000 LOC se importan refactorizados al repo; MCPs en otros lenguajes o con >=5000 LOC se mantienen como MCP externo.
- **Contrato `ToolWrapper`**: protocolo comun que toda tool (interna o MCP externo) implementa para registro, healthcheck y ejecucion.
- **Registro en `ToolRegistry`**: cada tool importada o externa se registra con su clasificacion, metadata y estado operacional.
- **Discovery semantico**: busqueda por embeddings sobre descripciones/tags/uso historico para que el agente encuentre candidatos relevantes sin cargar el catalogo completo en contexto.
- **Tres niveles de detalle**: ToolCard (lista minima), ToolSummary (schema + ejemplos), ToolDocs (docs largas).
- **Distincion MVP (20 capacidades) vs roadmap (+59)**: el catalogo documenta las 79 pero solo las 20 MVP se activan operacionalmente en la primera entrega.

### Out of Scope

- **Implementacion de las tools individuales** (wrappers concretos de tavily, exa, file_system, etc.) -- eso corresponde a specs 009 (ToolRegistry base), 011 (tools Tier 1 MVP) y roadmap F3b.
- **MCPProcessSupervisor** (gestion de procesos STDIO de MCPs externos) -- spec 010 o spec dedicado.
- **LocalAppDetector** (deteccion de apps locales para sub-tools `*_local.py`) -- roadmap post-MVP.
- **Sub-tools `*_local.py`** (10 wrappers Win COM) -- roadmap post-MVP.
- **Tier 3 traducidos** (6 tools TS a Python) -- roadmap post-MVP.
- **Marketplaces externos** (K-Dense, agency-agents) -- roadmap post-MVP.
- **Frontend de administracion avanzada de tools/MCPs** (admin de repos clonados, versionado visual) -- roadmap post-MVP.
- **Automantenimiento Dreaming** (upstream-watch, auto-update proposals) -- roadmap F5b.

---

## Assumptions

- **A-01**: Las fuentes de MCPs a evaluar viven en `documentation/` (p.ej. `documentation/openclaw/openclaw` ya clonado con scripts Python pequenos; `documentation/hermes agent/hermes-agent` pendiente de checkout completo). El inventario real de lineas se valida en fase de plan/tasks, no en esta spec.
- **A-02**: El conteo de lineas para la regla de importacion se mide sumando las lineas de todos los archivos `.py` del repositorio del MCP (excluyendo tests, docs y archivos de configuracion). Herramienta: `find . -name "*.py" -not -path "*/test*" -not -path "*/docs*" | xargs wc -l` o equivalente Windows.
- **A-03**: El `ToolRegistry` y `ToolWrapper` definidos en spec 009 (FR-011, FR-012, FR-013) ya existen como contratos base. Esta spec extiende su uso para clasificacion por estrategia y la regla de importacion.
- **A-04**: Los embeddings para discovery semantico usan el provider ya seleccionable del 2.0 (`GeminiEmbeddingGateway`); no se implementan embeddings nuevos en esta spec.
- **A-05**: La refactorizacion de MCPs importados sigue los principios de la constitucion v1.2.0: SRP, SoC, DIP, modulos <=400 LOC, sin abstracciones especulativas.
- **A-06**: El destino de tools importadas en `src/` es `src/vigilancia_multiagente/enterprise/tooling/builtin/<dominio>/` segun la convencion establecida en el doc 06.
- **A-07**: El catalogo SSOT se persiste como archivo YAML en `config/tools/catalog.yaml` (fuente declarativa) y se carga al `ToolRegistry` en memoria al arranque.
- **A-08**: La clasificacion de estrategia es estatica por entrada (no cambia en runtime); se actualiza manualmente o via Dreaming admin (post-MVP).

---

## User Scenarios & Testing

### Primary User Story

Como **ingeniero del Vigilador 3.0** que integra una nueva capacidad, quiero **consultar el catalogo SSOT para saber la estrategia de extraccion asignada** (importar vs MCP externo), el destino en `src/`, y el contrato que debo implementar, **para que la integracion sea consistente y trazable** sin decisiones ad-hoc.

### Secondary User Story

Como **agente autonomo del Vigilador 3.0**, quiero **descubrir semanticamente las tools relevantes para mi intent actual** sin recibir las 79 entradas en prompt, **para mantener el contexto LLM eficiente** y seleccionar solo candidatos pertinentes.

### Acceptance Scenarios

1. **Given** el catalogo SSOT cargado con las 79 entradas, **When** consulto la entrada de un MCP Python con <5000 LOC (p.ej. `excalidraw_architect`), **Then** su campo `strategy` es `WRAP-SDK` o `COPY-HERMES` y su campo `runtime` es `python_internal`, con destino declarado en `src/vigilancia_multiagente/enterprise/tooling/builtin/<dominio>/`.

2. **Given** el catalogo SSOT cargado, **When** consulto la entrada de un MCP en TypeScript (p.ej. `brave-search-mcp-server`), **Then** su campo `strategy` es `MCP-EXTERNO` y su campo `runtime` es `process_stdio` o `process_http`.

3. **Given** el catalogo SSOT cargado, **When** consulto la entrada de un MCP Python con >=5000 LOC, **Then** su campo `strategy` es `MCP-EXTERNO` y su campo `runtime` es `process_stdio` o `process_http`, independientemente de que sea Python.

4. **Given** una tool importada al repo, **When** verifico su estructura en `src/`, **Then** implementa el protocolo `ToolWrapper` (name, domain, is_external_mcp=False, requires_auth, healthcheck(), execute()) y esta registrada en el `ToolRegistry`.

5. **Given** una tool mantenida como MCP externo, **When** verifico su registro, **Then** implementa `ToolWrapper` con `is_external_mcp=True` y su `execute()` delega al cliente MCP (STDIO o HTTP).

6. **Given** el `ToolRegistry` con 79 entradas indexadas, **When** el agente invoca `discover(role="researcher", intent="buscar papers academicos recientes sobre IA", tenant_id=<UUID>)`, **Then** los candidatos retornados incluyen `arxiv`, `openalex`, `google_scholar` en las primeras 5 posiciones (ordenados por similitud semantica).

7. **Given** el catalogo SSOT, **When** filtro por `status=active` y scope MVP, **Then** obtengo exactamente las 20 capacidades definidas en 00b (4 Tier 1 + 16 Tier 2).

8. **Given** una entrada del catalogo con `update_policy: upstream-watch`, **When** consulto su metadata, **Then** incluye campos `source_repo`, `pinned_version` y `last_audit_date` para trazabilidad.

### Edge Cases

- **EC-01**: Un MCP Python tiene exactamente 5000 lineas -- se clasifica como MCP externo (la regla es "menos de 5000", no "menor o igual").
- **EC-02**: Un MCP Python tiene <5000 LOC pero depende de binarios nativos no-Python (p.ej. requiere compilacion C) -- se clasifica como MCP externo con nota explicativa en el campo `notes`.
- **EC-03**: Las fuentes en `documentation/` no estan clonadas al momento de crear el catalogo -- las entradas se marcan con `loc_validated: false` y el conteo real se completa en fase de plan/tasks.
- **EC-04**: Un MCP cambia de lenguaje entre versiones (p.ej. reescrito de TS a Python) -- la clasificacion se re-evalua en el proximo ciclo de auditoria; el catalogo registra la version evaluada.
- **EC-05**: Dos tools del catalogo exponen la misma capability con distinto nombre -- el catalogo las mantiene como entradas separadas con campo `dedup_group` que las agrupa para que el discovery no las presente ambas.

---

## Functional Requirements

### Catalogo SSOT

- **FR-001**: El sistema MUST mantener un catalogo SSOT con una entrada por cada una de las 79 capacidades del plan v3.0, persistido en `config/tools/catalog.yaml`.
  - *Traza*: doc 06 seccion 0 "Contrato SSOT para tools y MCPs".

- **FR-002**: Cada entrada del catalogo MUST incluir los siguientes campos:
  - **Obligatorios**: `id`, `domain`, `source`, `strategy`, `runtime`, `status`, `owner`, `license`, `capabilities` (lista de verbs), `requires_key`, `env_var`, `healthcheck`, `update_policy`, `loc_count`, `loc_validated`, `language`, `mvp` (boolean).
  - **Opcionales**: `notes`, `dedup_group`, `source_repo`, `pinned_version`, `last_audit_date`.
  - *Traza*: doc 06 seccion 0 tabla de campos.

- **FR-003**: El campo `strategy` MUST ser uno de: `COPY-HERMES`, `WRAP-SDK`, `MCP-EXTERNO`, `TRANSLATE-THIN`, `NUEVO`.
  - *Traza*: doc 06 "Convencion de estrategias".

- **FR-004**: El campo `mvp` MUST ser `true` para las 20 capacidades del MVP (4 Tier 1 + 16 Tier 2) y `false` para las 59 restantes del roadmap.
  - *Traza*: doc 00b "Inventario MVP de tools y MCPs".

### Regla de importacion por lineas

- **FR-005**: El sistema MUST clasificar como `runtime: python_internal` (importar al repo) todo MCP cuyo lenguaje principal sea Python Y cuyo conteo de lineas de archivos `.py` (excluyendo directorios `test*/`, `docs*/`, `*_test.py`, `conftest.py`) sea estrictamente menor a 5000.
  - *Traza*: requisito explicito del usuario.

- **FR-006**: El sistema MUST clasificar como `runtime: process_stdio` o `runtime: process_http` (MCP externo) todo MCP cuyo lenguaje principal NO sea Python, O cuyo conteo de lineas `.py` sea >= 5000.
  - *Traza*: requisito explicito del usuario.

- **FR-007**: El conteo de lineas MUST medirse ejecutando la suma de lineas de todos los archivos `.py` del repositorio del MCP, excluyendo: directorios que contengan `test` en su nombre, archivos `*_test.py`, `conftest.py`, y directorios `docs/` o `documentation/`.
  - *Traza*: requisito explicito del usuario, criterio de medicion.

- **FR-008**: Cada entrada con `loc_validated: false` MUST ser revalidada antes de proceder a su importacion; el campo se actualiza a `true` con el conteo real una vez verificado contra el repositorio fuente.
  - *Traza*: EC-03, A-01.

### Destino en src/ y modularizacion

- **FR-009**: Toda tool importada (`runtime: python_internal`) MUST residir en `src/vigilancia_multiagente/enterprise/tooling/builtin/<dominio>/` donde `<dominio>` corresponde al campo `domain` de su entrada en el catalogo.
  - *Traza*: doc 06 seccion 5 "Orden sugerido de extraccion".

- **FR-010**: Toda tool importada MUST ser refactorizada siguiendo SRP, SoC y DIP de la constitucion v1.2.0: modulos <=400 LOC, sin mezclar orquestacion con logica de dominio ni acceso a infraestructura en la misma unidad.
  - *Traza*: constitucion v1.2.0 principios 2, 3; regla C0 del doc 06.

- **FR-011**: Toda tool importada desde Hermes MUST incluir header de atribucion: `# Adapted from Hermes Agent -- original: tools/<filename>.py -- License: <MIT|Apache-2.0>`.
  - *Traza*: doc 06 seccion 7 "Licencias".

### Contrato ToolWrapper y registro

- **FR-012**: Toda tool (interna o externa) MUST implementar el protocolo `ToolWrapper` con: `name: str`, `domain: str`, `is_external_mcp: bool`, `requires_auth: bool`, `healthcheck() -> HealthcheckResult`, `execute(tool_name: str, args: dict[str, object]) -> dict[str, object]`. *(Cita de contrato de spec 009 — no redefine el Protocol; solo lo consume y registra metadata via CatalogEntry.)*
  - *Traza*: doc 06 seccion 8.6 "Observabilidad uniforme"; spec 009 FR-011; `enterprise/tooling/tool_wrapper.py`.

- **FR-013**: Para tools con `is_external_mcp=True`, el metodo `execute()` MUST delegar al cliente MCP (STDIO o HTTP) sin ejecutar logica de dominio in-process. *(Cita de contrato de spec 009 — no redefine el Protocol; solo lo consume y registra metadata via CatalogEntry.)*
  - *Traza*: doc 06 seccion 8.2 "Tier 2 -- MCPs externos via STDIO".

- **FR-014**: Para tools con `is_external_mcp=False`, el metodo `execute()` MUST invocar la logica Python importada directamente, sin levantar proceso externo. *(Cita de contrato de spec 009 — no redefine el Protocol; solo lo consume y registra metadata via CatalogEntry.)*
  - *Traza*: doc 06 seccion 8.1 "Tier 1 -- Python a internalizar".

- **FR-015**: Toda tool MUST registrarse en el `ToolRegistry` al arranque del sistema, con su clasificacion de estrategia y metadata del catalogo SSOT cargada. *(Cita de contrato de spec 009 — no redefine el Protocol; solo lo consume y registra metadata via CatalogEntry.)*
  - *Traza*: spec 009 FR-012, FR-016.

### Discovery semantico

- **FR-016**: El `ToolRegistry.discover(role, intent, tenant_id)` MUST retornar candidatos ordenados por similitud semantica entre el `intent` y las descripciones/capabilities de las entradas del catalogo (`CatalogEntry`) indexadas. La firma real es `discover(self, role: str, intent: str, tenant_id: UUID)` donde `tenant_id` identifica al tenant para resolver estado de salud por tool.
  - *Traza*: doc 06 seccion 8.7 "Descubrimiento semantico de tools"; spec 009 FR-013; `enterprise/tooling/tool_registry.py`.

### Tools nuevas Tier 1 (documents)

- **FR-019**: La tool `template_render` MUST aceptar como inputs: `template_name: str` (nombre del template en `config/templates/`), `variables: dict[str, object]` (datos a interpolar), `output_format: str` (uno de: `md`, `html`, `docx`). MUST retornar `dict[str, object]` con claves `rendered_content: str` (contenido renderizado) y `output_path: str | None` (ruta del archivo generado si aplica).
  - *Traza*: doc 06 Tier 1 documents; plan.md Phase 3.

- **FR-020**: La tool `docx_generate` MUST aceptar como inputs: `title: str`, `sections: list[dict]` (cada dict con `heading: str` y `body: str`), `template_path: str | None` (template DOCX base opcional), `output_path: str` (ruta destino). MUST retornar `dict[str, object]` con claves `output_path: str` (ruta del DOCX generado) y `page_count: int`.
  - *Traza*: doc 06 Tier 1 documents; plan.md Phase 3.

- **FR-021**: La tool `pdf_generate` MUST aceptar como inputs: `html_content: str` (HTML/Markdown renderizado a convertir), `css_path: str | None` (hoja de estilos opcional), `output_path: str` (ruta destino). MUST retornar `dict[str, object]` con claves `output_path: str` (ruta del PDF generado) y `page_count: int`.
  - *Traza*: doc 06 Tier 1 documents; plan.md Phase 3.

- **FR-017**: El discovery MUST operar en tres niveles de detalle: ToolCard (id + descripcion corta + dominio + permisos + costo + estado, <=80 chars por tool), ToolSummary (schema inputs/outputs + ejemplos cortos), ToolDocs (docs largas cargadas solo para candidatos seleccionados). El discovery indexa metadata del `CatalogEntry` (campos `capabilities`, descripcion del YAML), NO atributos del Protocol `ToolWrapper` (que no expone `tags` ni `capabilities`).
  - *Traza*: doc 06 seccion 8.7 tabla de niveles; spec 009 FR-012.

- **FR-018**: El discovery MUST aplicar filtros previos al ranking semantico: status activo, credenciales disponibles (tool-gating), y scope MVP (solo tools con `mvp: true` en la primera entrega).
  - *Traza*: spec 009 FR-015; doc 00b.

---

## Key Entities

- **Catalog entry (`config/tools/catalog.yaml`)**: registro declarativo de una capacidad del sistema. Campos obligatorios: id, domain, source, strategy, runtime, status, owner, license, capabilities, requires_key, env_var, healthcheck, update_policy, loc_count, loc_validated, language, mvp. Campos opcionales: notes, dedup_group, source_repo, pinned_version, last_audit_date. Vive en YAML versionado en el repo.

- **ToolWrapper (protocolo)**: contrato que toda tool implementa para ser operable por el ToolRegistry. Define la interfaz uniforme de healthcheck (`-> HealthcheckResult`) y ejecucion (`execute() -> dict[str, object]`) independientemente de si la tool es interna o externa. NO expone `tags` ni `capabilities` (esos viven en el CatalogEntry). Vive en `enterprise/tooling/tool_wrapper.py`.

- **ToolRegistry**: servicio que carga el catalogo SSOT, indexa embeddings de descripciones/capabilities del `CatalogEntry` (YAML), y expone discovery semantico (`discover(role, intent, tenant_id)`) + filtrado + gating. Vive en `enterprise/tooling/tool_registry.py`.

- **ToolCard / ToolSummary / ToolDocs**: tres niveles de representacion de una tool para el agente. ToolCard es lo minimo para listar; ToolSummary es lo necesario para decidir; ToolDocs es lo completo para ejecutar.

---

## Success Criteria

- **SC-001**: El catalogo SSOT contiene exactamente 79 entradas con todos los campos obligatorios (FR-002) completos y validados por schema.
- **SC-002**: El 100% de las entradas con `language: python` y `loc_count < 5000` tienen `runtime: python_internal`; el 100% de las entradas con lenguaje != Python o `loc_count >= 5000` tienen `runtime: process_stdio` o `runtime: process_http`.
- **SC-003**: Las 20 entradas MVP (`mvp: true`) coinciden exactamente con el inventario de 00b-mvp-scope-y-cronograma.md (4 Tier 1 + 16 Tier 2). Los 16 Tier 2 son: tavily, exa, jina, brave, firecrawl, serper, google_scholar, arxiv, fetch, sandbox, markitdown, minimax-image, openalex, playwright (14 MCPs preservados del 2.0) + serper_patents (alias de capacidad del MCP `serper`, contado como entrada separada en dominio `research`) + google-workspace-mcp (1 nuevo).
- **SC-004**: El `ToolRegistry.discover(role, intent, tenant_id)` retorna resultados relevantes (precision@5 >= 0.6 en un set de 20 queries de prueba representativas de los 4 dominios MVP).
- **SC-005**: Toda tool importada al repo cumple la regla de <=400 LOC por modulo, verificable por script automatizado.
- **SC-006**: Toda tool importada desde Hermes contiene el header de atribucion requerido (FR-011), verificable por grep automatizado.
- **SC-007**: El catalogo YAML pasa validacion de schema JSON sin errores al ejecutar el validador.

---

## Delivery Constraints

- **Constitucion v1.2.0 -- Simplicidad obligatoria (#2)**: el catalogo es un archivo YAML plano; no se introduce base de datos adicional ni ORM para persistirlo.
- **Constitucion v1.2.0 -- Modularidad primero (#3)**: las tools importadas se refactorizan en modulos con responsabilidad unica. Cero monolitos copiados tal cual.
- **Constitucion v1.2.0 -- DRY**: el catalogo es la unica fuente de verdad sobre clasificacion de tools; ningun otro archivo del repo duplica esta informacion.
- **Constitucion v1.2.0 -- Cambios quirurgicos (#5)**: el 2.0 no se toca. Los MCPs preservados del 2.0 (`infra/mcp/mcp-providers.json`) siguen operando sin modificacion; el catalogo SSOT los referencia pero no los altera.
- **Constitucion v1.2.0 -- YAGNI**: no se implementan las 59 tools del roadmap en esta entrega; solo se documentan en el catalogo con `mvp: false`.
- **C0 regla del doc 06**: "COPY-HERMES no significa pegar monolitos. Antes de entrar al core, cada archivo externo se divide en cliente, schemas, normalizadores, politicas, cache y wrapper."
- **Spec 009 dependencia**: esta spec extiende los contratos `ToolWrapper` y `ToolRegistry` definidos en spec 009 (FR-011 a FR-016). No los redefine.

---

## Dependencies

### Depends on

- **spec 009-mvp-foundation**: provee `ToolWrapper` protocolo, `ToolRegistry` con discovery semantico, `HealthMonitor`, tabla `tool_health`. Esta spec extiende su uso con la clasificacion por estrategia y la regla de importacion.

### Depended on by

- **spec 011 (F3a tools)**: usa el catalogo SSOT para saber que tools MVP implementar y con que estrategia.
- **spec 012 (F4a modos+playbooks)**: usa el discovery semantico del ToolRegistry para filtrar tools por modo.
- **Roadmap F3b**: usa el catalogo completo (79 entradas) para planificar la implementacion de las 59 tools restantes.
