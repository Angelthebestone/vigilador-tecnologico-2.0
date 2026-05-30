# Feature Specification: Skill Marketplace y Claude Local

**Feature ID**: 015-skill-marketplace-claude-local
**Created**: 2026-05-29
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/04-skills-y-capacidades.md](../../plan%20vigilador%203.0/04-skills-y-capacidades.md)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md)

---

## Problem Statement

El Vigilador 3.0 necesita un modelo conceptual claro que distinga Skill, Capability y Tool, y un mecanismo para cargar, registrar y descubrir skills desde multiples fuentes: skills curados internos, skills aprendidos por demostracion, skills locales del entorno `.claude/skills` (comandos como `speckit-*`) y, en el futuro, marketplaces externos (K-Dense, agency-agents).

Sin esta distincion formal y sin un `SkillRegistry` con descubrimiento semantico y carga progresiva, los agentes no pueden seleccionar la receta correcta para una tarea, el contexto se satura con instrucciones irrelevantes, y no existe un camino para incorporar skills de terceros de forma segura y versionada.

El plan 04 define la jerarquia `Agent compone Skills` (decision D1), el schema unificado `SKILL.md`, tres niveles de carga progresiva (`SkillCard`, `SkillSummary`, `SkillBody`) y la integracion de `.claude/skills` como fuente `external:claude-local`. Este spec formaliza los requisitos MVP de esa capa.

---

## Scope Boundaries

### In Scope (MVP)

- **Modelo conceptual**: definicion autoritativa de Skill vs Capability vs Tool vs CommandSkill con fronteras claras.
- **Schema unificado `SKILL.md`**: frontmatter YAML con campos obligatorios y opcionales, cuerpo Markdown con procedimiento y codigo opcional.
- **`SkillRegistry`** (`enterprise/skills_marketplace/skill_registry.py`): registro central de skills con indice semantico sobre metadata.
- **Descubrimiento semantico con carga progresiva**: tres niveles (`SkillCard`, `SkillSummary`, `SkillBody`) para evitar saturacion de contexto.
- **`SkillLoader`**: carga skills desde `config/skills/{curated|learned}/` y desde `.claude/skills/*/SKILL.md` (fuente `external:claude-local`).
- **Adapter Claude local** (`enterprise/skills_marketplace/claude_local_adapter.py`): escanea `.claude/skills/*/SKILL.md`, normaliza metadata al schema del Vigilador, calcula hash de contenido, modela comandos como `CommandSkill`.
- **Validacion de disponibilidad**: el `SkillLoader` verifica que las `required_capabilities` de cada skill existan en el `ToolRegistry` (spec 009); skills con capabilities faltantes se marcan `unavailable`.
- **Filtrado por Mode**: skills con `mode_compatible` se filtran segun el Mode activo (los Modes se definen en spec 012; aqui se implementa el mecanismo de filtrado).
- **Politica de prioridad de fuentes**: `curated > learned > external` para deduplicacion por `id`.
- **Seguridad de CommandSkills**: skills que ejecutan shell, invocan subprocess o tocan git destructivamente se marcan `requires_sandbox: true`; no se ejecutan sin approval.
- **Versionado por hash**: skills importadas desde `.claude/skills` se versionan por hash de contenido; cambios detectados se marcan para revalidacion.

### Out of Scope (Roadmap post-MVP)

- **Marketplaces externos** (K-Dense-AI/scientific-agent-skills, msitarzewski/agency-agents): adapters, clonado de repos, quarantine, pull semanal. Documentados en plan 04 pero explicitamente diferidos por 00b ("Marketplaces externos quedan documentados pero no se cargan en MVP").
- **Skill Learning por demostracion** (decision #15): flujo de observacion con `computer_use`, parametrizacion automatica, generacion de `SKILL.md` aprendido. Diferido a F5b.
- **Skill curator** (Dreaming Fase 2): revalidacion periodica, deteccion de duplicados, stats de uso, promocion de skills compuestas. Diferido a F5a/F5b.
- **Plugins internos Cowork** (`finance:`, `engineering:`, `design:`, `productivity:`, `frontend-design:`): su carga como namespace requiere los dominios post-MVP.
- **Override con herencia** (`inherits: "external:k-dense/..."` + `overrides:`): mecanismo de herencia explicita entre skills. Diferido a roadmap.
- **Tests sinteticos automatizados** para validacion de skills: diferidos a Dreaming.
- **CLI `vigilador-admin skill *`**: comandos administrativos de gestion de skills. Diferido a roadmap.

---

## Assumptions

- **A-01**: El `ToolRegistry` (spec 009) esta operativo. Actualmente NO expone un metodo `is_capability_available`; se requiere un cambio aditivo quirurgico (PREREQUISITO Phase 1, tarea T001) para anadir `async def is_capability_available(name: str) -> bool` a `tool_registry.py` que retorne `True` si `name` existe en `self._tools` y `self._passes_gating(self._tools[name])` es `True`. El `SkillRegistry` consultara este metodo para validar `required_capabilities`. El mapeo es directo: cada string en `required_capabilities` corresponde al `tool.name` registrado en `ToolRegistry` (formato plano, e.g. `"template_render"`, NO `domain.tool_name`).
- **A-02**: El directorio `.claude/skills/` existe en la raiz del repo con al menos un `SKILL.md` valido (evidencia: 14 skills Spec-Kit ya instalados).
- **A-03**: Los providers de embeddings del 2.0 (`GeminiEmbeddingGateway`) estan funcionales para generar embeddings sobre descripciones/tags de skills (mismo provider usado por `ToolRegistry`).
- **A-04**: Los Modes se definen en `config/modes/*.yaml` (spec 012); este spec solo consume el campo `mode_compatible` del skill y el Mode activo del runtime.
- **A-05**: El formato de frontmatter YAML de `.claude/skills/*/SKILL.md` usa al menos `name` y `description` como campos obligatorios (evidencia: formato OpenClaw observado en `documentation/openclaw/`).
- **A-06**: En MVP, las unicas fuentes habilitadas son `[curated, learned, external:claude-local]`, controladas por el field `skills_sources_enabled: list[str]` en `settings.py` (env var `VT_SKILLS_SOURCES_ENABLED`; formato: lista JSON, e.g. `'["curated","learned","external:claude-local"]'`). `config/settings.yaml` es DOC-ONLY (referencia para operadores, no se carga en runtime); el SSOT de runtime es `settings.py` con `env_prefix="VT_"` y `SettingsConfigDict`. Las fuentes `external:k-dense` y `external:agency-agents` quedan deshabilitadas hasta roadmap.
- **A-07**: El `SkillRegistry` vive en el mismo proceso que el `ToolRegistry`; no requiere comunicacion inter-proceso.

---

## User Scenarios & Testing

### Primary User Story

Como **agente del Vigilador 3.0** (runtime autonomo), quiero **descubrir la skill mas relevante para una tarea solicitada por el usuario** sin cargar todo el catalogo al contexto, **para ejecutar la receta correcta con las capabilities disponibles** y sin saturar la ventana de contexto del LLM.

### Acceptance Scenarios

1. **Given** skills curados en `config/skills/curated/` y skills locales en `.claude/skills/`, **When** el `SkillLoader` arranca, **Then** ambas fuentes se registran en el `SkillRegistry` con sus respectivos `source` (`curated` y `external:claude-local`) y el total de skills registrados es >= 14 (los de `.claude/skills`).

2. **Given** un skill curado y un skill externo con el mismo `id`, **When** el `SkillRegistry` resuelve el conflicto, **Then** el skill curado prevalece y el externo queda oculto (politica `curated > learned > external`).

3. **Given** un skill con `required_capabilities: [documents.template_render, quickbooks.fetch_journal_entries]` y el `ToolRegistry` reporta que `quickbooks.fetch_journal_entries` no existe, **When** el `SkillLoader` valida el skill, **Then** el skill se marca como `unavailable` y no aparece en resultados de busqueda.

4. **Given** el `SkillRegistry` con 50 skills registrados, **When** un agente invoca `discover(intent="generar reporte mensual de cierre")`, **Then** el resultado contiene solo `SkillCard` de los top-k candidatos (no el cuerpo completo) y la respuesta tarda <= 500 ms.

5. **Given** un skill candidato en top-k tras busqueda semantica, **When** el agente solicita mas detalle, **Then** el `SkillRegistry` devuelve `SkillSummary` (inputs/outputs, capabilities requeridas, ejemplos cortos) sin cargar el `SkillBody` completo.

6. **Given** un skill seleccionado para ejecucion, **When** el agente solicita el cuerpo completo, **Then** el `SkillRegistry` devuelve `SkillBody` con procedimiento, codigo opcional y comandos.

7. **Given** un skill de `.claude/skills/speckit-implement/SKILL.md` que ejecuta shell y escribe archivos, **When** el `claude_local_adapter` lo importa, **Then** el skill se registra con `requires_sandbox: true` y `source: external:claude-local`.

8. **Given** un skill local cuyo contenido cambia (hash diferente al registrado), **When** el `SkillLoader` re-escanea en el proximo arranque, **Then** el skill se marca como `pending_revalidation` y no se ofrece a agentes hasta que el operador lo confirme o el sistema lo revalide.

9. **Given** el Mode activo es `Vigilancia Tech` y un skill tiene `mode_compatible: [CFO, CEO]`, **When** un agente busca skills, **Then** ese skill no aparece en los resultados.

10. **Given** el Mode activo es `CEO` y un skill tiene `mode_compatible: [CFO, CEO]`, **When** un agente busca skills, **Then** ese skill aparece en los resultados si sus capabilities estan disponibles.

### Edge Cases

- **EC-01**: `.claude/skills/` contiene un directorio sin `SKILL.md` -> el adapter lo ignora silenciosamente con log de warning.
- **EC-02**: Un `SKILL.md` tiene frontmatter YAML invalido (syntax error) -> el adapter lo excluye del registro con log de error indicando ruta y linea.
- **EC-03**: Un skill declara `required_capabilities` vacia -> se considera siempre disponible (no depende de tools externas).
- **EC-04**: Todas las fuentes habilitadas estan vacias (cero skills) -> el `SkillRegistry` arranca vacio sin error; las busquedas devuelven lista vacia.
- **EC-05**: Un skill tiene `mode_compatible` vacio o ausente -> se considera compatible con todos los Modes (universal).
- **EC-06**: Dos skills de la misma fuente tienen el mismo `id` -> el loader rechaza el segundo con log de error y registra solo el primero encontrado.

---

## Functional Requirements

### Modelo conceptual (definiciones)

- **FR-001**: El sistema MUST distinguir formalmente cuatro conceptos: **Skill** (receta atomica reutilizable, declarativa + opcional Python, vive en `config/skills/` o fuente externa), **Capability** (verbo concreto con schema JSON expuesto por una Tool), **Tool** (modulo Python que implementa N capabilities, registrado en `ToolRegistry`), **CommandSkill** (comando parametrizable modelado como skill, proveniente de `.claude/commands` o `.claude/skills`).
- **FR-002**: El sistema MUST documentar estas definiciones en un archivo de referencia accesible al runtime (`config/skills/README.md` o equivalente) para que agentes y operadores consulten la taxonomia.

### Schema `SKILL.md`

- **FR-003**: El schema unificado `SKILL.md` MUST requerir como campos obligatorios de frontmatter: `id` (o `name`), `description`, `source`.
- **FR-004**: El schema MUST soportar como campos opcionales: `version`, `license`, `author`, `category`, `tags`, `mode_compatible`, `triggers`, `required_capabilities`, `required_company_files`, `inputs`, `outputs`, `audit.level`, `requires_sandbox`.
- **FR-005**: El cuerpo del `SKILL.md` (despues del frontmatter) MUST soportar secciones Markdown de procedimiento y bloques de codigo Python opcionales.
- **FR-006**: El `SkillLoader` MUST aceptar tanto `id` como `name` en el frontmatter como identificador unico del skill (compatibilidad con formato OpenClaw que usa `name`).

### SkillRegistry

- **FR-007**: El sistema MUST proveer un `SkillRegistry` que mantenga un indice en memoria de todos los skills registrados, indexados por `id` y por embeddings de `description` + `tags`.
- **FR-008**: El `SkillRegistry.discover(intent, mode, limit)` MUST devolver candidatos ordenados por similitud semantica entre el `intent` y las descripciones/tags de los skills, filtrados por Mode activo y disponibilidad de capabilities.
- **FR-009**: El `SkillRegistry` MUST exponer tres niveles de detalle: `get_cards()` (lista minima: id, descripcion corta, tags, source, modos, estado), `get_summary(id)` (inputs/outputs, capabilities requeridas, ejemplos), `get_body(id)` (SKILL.md completo).
- **FR-010**: El `SkillRegistry` MUST aplicar deduplicacion por `id` con prioridad `curated > learned > external:claude-local > external:*`.
- **FR-011**: El `SkillRegistry` MUST marcar como `unavailable` todo skill cuyas `required_capabilities` no esten todas presentes y pasando gating en el `ToolRegistry`. El campo `required_capabilities` es una lista de strings donde cada valor corresponde exactamente al `tool.name` registrado en `ToolRegistry` (formato plano, e.g. `["template_render", "fetch_journal_entries"]`, NO `domain.tool_name`). El mapeo es directo: `capability_name == tool.name`. La validacion se realiza via `ToolRegistry.is_capability_available(name)` (prerequisito A-01).
- **FR-012**: El `SkillRegistry` MUST filtrar skills por `mode_compatible` cuando el caller provee un Mode activo; skills sin `mode_compatible` declarado pasan el filtro (universales).

### SkillLoader

- **FR-013**: El `SkillLoader` MUST escanear `config/skills/curated/` y `config/skills/learned/` recursivamente buscando archivos `*.md` con frontmatter YAML valido.
- **FR-014**: El `SkillLoader` MUST invocar los adapters de fuentes externas habilitadas en `settings.py` field `skills_sources_enabled` (SSOT de runtime; `config/settings.yaml` es DOC-ONLY) y registrar sus skills en el `SkillRegistry`.
- **FR-015**: El `SkillLoader` MUST validar el frontmatter YAML de cada skill antes de registrarlo; skills con frontmatter invalido se excluyen con log de error.
- **FR-016**: El `SkillLoader` MUST ejecutarse al arranque del proceso y registrar todos los skills disponibles antes de que los agentes comiencen a operar.

### Adapter Claude local

- **FR-017**: El sistema MUST proveer un `claude_local_adapter` que escanee `.claude/skills/*/SKILL.md` en la raiz del repo.
- **FR-018**: El adapter MUST normalizar el frontmatter OpenClaw (campo `name` -> `id`, campos opcionales `metadata`, `allowed-tools`, `user-invocable`, `disable-model-invocation`) al schema unificado del Vigilador.
- **FR-019**: El adapter MUST calcular un hash SHA-256 del contenido de cada `SKILL.md` y almacenarlo como `content_hash` en el registro.
- **FR-020**: El adapter MUST marcar como `requires_sandbox: true` todo skill cuyo contenido referencia ejecucion de shell, comandos de sistema o operaciones git destructivas. Deteccion por keywords en contexto de comandos/codigo: `execute_command`, `subprocess`, `os.system`, `os.popen`, `Popen`, `shell=True`, `bash -c`, `git push`, `git reset`, `git clean`, `rm -rf`, `shutil.rmtree`. NO se usan palabras genericas como `write`, `create`, `delete` que generarian falsos positivos en skills documentales o de escritura de archivos via API.
- **FR-021**: El adapter MUST registrar cada skill con `source: external:claude-local` y la ruta relativa como metadata adicional.
- **FR-022**: En arranques posteriores, el adapter MUST comparar el hash actual con el registrado; si difiere, marcar el skill como `pending_revalidation`.

### Seguridad y governance

- **FR-023**: El sistema MUST marcar con `requires_sandbox: true` todo skill que cumpla la heuristica de sandbox, exponiendo este flag como CONTRATO para que el caller futuro (agente ejecutor, fuera del scope de este spec) impida la ejecucion autonoma sin approval. Este spec NO ejecuta skills; solo establece el flag.
- **FR-024**: El sistema MUST proveer un hook de audit (`skill_audit.log_skill_invocation`) como CONTRATO para que el caller futuro registre en el audit trail (JSONL) cada invocacion de skill con: `skill_id`, `source`, `mode`, `timestamp`, `capabilities_invoked`, `result_status`. Este spec implementa la funcion de logging pero no la invoca en runtime.

### Configuracion

- **FR-025**: El sistema MUST leer la lista de fuentes habilitadas desde el field `skills_sources_enabled: list[str]` en `settings.py` (env var `VT_SKILLS_SOURCES_ENABLED`, formato lista JSON: `'["curated","learned","external:claude-local"]'`) y solo cargar skills de fuentes listadas. `config/settings.yaml` documenta la configuracion como referencia para operadores (DOC-ONLY, no se carga en runtime; el SSOT es `settings.py` con `env_prefix="VT_"`).
- **FR-026**: El sistema MUST permitir al operador cambiar las fuentes habilitadas via la env var `VT_SKILLS_SOURCES_ENABLED` o editando `.env` sin recompilacion; el cambio se toma al proximo arranque. No se requiere loader YAML en runtime.

---

## Key Entities

- **Skill (`SkillCard`)**: metadata minima de un skill registrado. Atributos: `id`, `display_name`, `description` (corta), `tags`, `source`, `mode_compatible`, `state` (available/unavailable/pending_revalidation), `content_hash`. Vive en memoria del `SkillRegistry`.
- **SkillSummary**: detalle intermedio. Atributos: `inputs`, `outputs`, `required_capabilities`, `required_company_files`, `examples`, `audit_level`. Se carga bajo demanda desde el archivo fuente.
- **SkillBody**: contenido completo del `SKILL.md` incluyendo procedimiento y codigo opcional. Se carga solo al ejecutar.
- **CommandSkill**: subtipo de Skill proveniente de `.claude/skills` o `.claude/commands`. Atributos adicionales: `requires_sandbox`, `argument_hint`, `user_invocable`.
- **SkillRegistry**: registro central en memoria con indice semantico. Constructor recibe el PORT abstracto `EmbeddingGateway` (interfaz en `domain.ports.embedding_gateway`), NO el concreto `GeminiEmbeddingGateway` (DIP). Tambien recibe `ToolRegistry` por inyeccion. Expone `discover()`, `get_cards()`, `get_summary()`, `get_body()`, `register()`, `mark_unavailable()`.
- **SkillLoader**: orquestador de carga que invoca adapters y valida skills antes de registrarlos.
- **claude_local_adapter**: adapter especifico para `.claude/skills/*/SKILL.md`.

---

## Success Criteria

- **SC-001**: El `SkillRegistry` carga y registra >= 14 skills desde `.claude/skills/` al arranque sin errores, en <= 3 s.
- **SC-002**: Una busqueda semantica `discover(intent, mode, limit=5)` sobre un catalogo de 50 skills responde en <= 500 ms.
- **SC-003**: La carga progresiva funciona correctamente: `get_cards()` no carga cuerpos de skills; `get_body(id)` carga el archivo completo solo bajo demanda.
- **SC-004**: Skills con capabilities faltantes se marcan `unavailable` al 100% de los casos de prueba (cero falsos positivos en el listing).
- **SC-005**: La deduplicacion por prioridad de fuente funciona correctamente: un skill curado con mismo `id` que uno externo siempre prevalece.
- **SC-006**: Skills que cumplen la heuristica de sandbox se registran con el flag `requires_sandbox: true` correcto al 100% de los casos de prueba (cero falsos negativos en skills con comandos shell/subprocess/git destructivo; cero falsos positivos en skills documentales).
- **SC-007**: Un cambio de contenido en un `SKILL.md` local se detecta por diferencia de hash en el siguiente arranque y el skill se marca `pending_revalidation`.

---

## Traceability Matrix

| FR | Acceptance scenario | Success criterion | Fuente plan |
|----|---------------------|-------------------|-------------|
| FR-001 | -- | -- | 04 seccion "Concepto: Skill vs Capability vs Tool" |
| FR-002 | -- | -- | 04 seccion "Concepto" |
| FR-003 | AS-1 | SC-001 | 04 seccion "Schema unificado SKILL.md" |
| FR-004 | AS-7 | -- | 04 seccion "Schema unificado SKILL.md" |
| FR-005 | AS-6 | SC-003 | 04 seccion "Schema unificado SKILL.md" |
| FR-006 | AS-1 | SC-001 | 04 + evidencia OpenClaw (campo `name`) |
| FR-007 | AS-4 | SC-002 | 04 seccion "Descubrimiento semantico" |
| FR-008 | AS-4, AS-9, AS-10 | SC-002 | 04 seccion "Descubrimiento semantico" |
| FR-009 | AS-4, AS-5, AS-6 | SC-003 | 04 seccion "Descubrimiento semantico" tabla niveles |
| FR-010 | AS-2 | SC-005 | 04 seccion "Politica de actualizacion" |
| FR-011 | AS-3 | SC-004 | 04 seccion "Reglas del schema" |
| FR-012 | AS-9, AS-10 | -- | 04 seccion "Descubrimiento semantico" ranking |
| FR-013 | AS-1 | SC-001 | 04 seccion "Como anadir un skill nuevo" |
| FR-014 | AS-1 | SC-001 | 04 seccion "Marketplaces externos integrados" |
| FR-015 | EC-02 | -- | 04 seccion "Reglas del schema" |
| FR-016 | AS-1 | SC-001 | 04 seccion "Descubrimiento semantico" |
| FR-017 | AS-7 | SC-001 | 04 seccion "Claude local" |
| FR-018 | AS-7 | SC-001 | 04 seccion "Claude local" + evidencia OpenClaw |
| FR-019 | AS-8 | SC-007 | 04 seccion "Claude local" |
| FR-020 | AS-7 | SC-006 | 04 seccion "Reglas de seguridad" |
| FR-021 | AS-7 | -- | 04 seccion "Claude local" |
| FR-022 | AS-8 | SC-007 | 04 seccion "Claude local" |
| FR-023 | -- | SC-006 | 04 seccion "Reglas de seguridad" |
| FR-024 | -- | -- | 04 seccion "Schema: audit.level" |
| FR-025 | AS-1 | -- | 04 seccion "source" + 00b C1 |
| FR-026 | -- | -- | 04 seccion "source" |

**Cobertura**: 26/26 FR mapeados. FR sin AS directo (FR-001, FR-002, FR-023, FR-024, FR-025, FR-026) se validan via tests unitarios.

---

## Delivery Constraints

- **Constitucion v1.2.0 -- Simplicidad obligatoria (#2)**: el `SkillRegistry` no implementa mecanismos de quarantine, pull semanal ni curator en MVP. Solo carga, valida y registra.
- **Constitucion v1.2.0 -- Modularidad primero (#3)**: `SkillRegistry`, `SkillLoader` y `claude_local_adapter` son modulos separados con responsabilidad unica. Cada archivo <= 400 LOC.
- **Constitucion v1.2.0 -- Manejo de errores estricto (#4)**: frontmatter invalido se reporta con ruta y detalle; no se silencia. Skills invalidos se excluyen sin detener el arranque.
- **Constitucion v1.2.0 -- YAGNI**: no se implementan adapters para K-Dense ni agency-agents hasta que se habiliten en roadmap.
- **00b MVP scope**: "Marketplaces externos quedan documentados pero no se cargan en MVP (post-MVP)". Solo `external:claude-local` entra en MVP.
- **CQS (Constitucion -- Desarrollo y Arquitectura)**: `SkillRegistry.discover()` es query pura; mutaciones de estado (registro, marcado unavailable) son operaciones separadas.
- **Dependencia spec 009**: requiere `ToolRegistry` operativo para validar `required_capabilities`.
- **Dependencia spec 012**: los Modes se definen ahi; este spec implementa el mecanismo de filtrado pero no define los Modes.

---

## Dependencies on previous specs

- **spec 009 (MVP Foundation)**: `ToolRegistry` con metodo `is_capability_available(name)` (prerequisito aditivo, ver A-01/T001). Embeddings provider funcional (`EmbeddingGateway` PORT).
- **spec 012 (Modos y Playbooks)**: define los Modes que alimentan el filtro `mode_compatible`. Este spec puede implementarse antes de 012 usando un Mode placeholder.

## Specs descendientes que dependen de este

- **spec 012 (Modos y Playbooks)**: los playbooks invocan skills via `SkillRegistry.discover()`.
- **Specs F5a+ (Dreaming, Skill Learning)**: el `skill_curator` y el flujo de Skill Learning escriben en `config/skills/learned/` y dependen del `SkillLoader` para registrarlos.
- **Specs roadmap (marketplaces externos)**: los adapters K-Dense y agency-agents se conectan al `SkillLoader` como fuentes adicionales.
