# Feature Specification: Mode Router, Catalogo de Modos y company_geo

**Feature ID**: 011-mode-router-catalogo-geo
**Created**: 2026-05-29
**Status**: Draft (specification phase)
**Related plan documents**:
- [plan vigilador 3.0/02-modos-y-personalidades.md](../../plan%20vigilador%203.0/02-modos-y-personalidades.md)
- [plan vigilador 3.0/00b-mvp-scope-y-cronograma.md](../../plan%20vigilador%203.0/00b-mvp-scope-y-cronograma.md)
- [plan vigilador 3.0/00-canon-operativo-corregido.md](../../plan%20vigilador%203.0/00-canon-operativo-corregido.md)

---

## Problem Statement

El Vigilador 3.0 necesita que cada sesion de usuario opere bajo un **Modo** explicito que determine la personalidad del asistente, las skills permitidas, los playbooks disponibles, las tools accesibles y el contexto geografico empresarial. Sin esta capa, el sistema no puede diferenciar entre un usuario que necesita asistencia financiera (CFO) y uno que necesita vigilancia tecnologica, resultando en respuestas genericas sin contexto empresarial.

Ademas, la normativa, impuestos y fuentes oficiales varian segun la ubicacion geografica de la empresa (pais/departamento/municipio). El sistema necesita un modelo `company_geo` que condicione las busquedas y respuestas a la jurisdiccion correcta.

Este spec define: el schema YAML de un Mode, el catalogo inicial de Modos, el componente `ModeResolver` que resuelve que modo aplicar a cada sesion, y la estructura `company_geo` que contextualiza geograficamente las respuestas.

**Alcance MVP** (segun 00b): solo los modos `default`, `Vigilancia Tech` y `CEO` (reducido) se implementan. Los demas modos (CFO, Consultor Legal, Marketing, Vendedor B2B, Operaciones PYME) quedan documentados como roadmap.

---

## Scope Boundaries

### In Scope

- **Schema YAML de Mode**: definicion formal del formato `config/modes/<id>.yaml` con campos obligatorios y opcionales, reglas de validacion.
- **Catalogo inicial de Modos**: 7 modos preconfigurados documentados; 3 implementados en MVP.
- **ModeResolver/router**: componente que determina el modo activo para una sesion dada, con activacion explicita (`/mode <id>`) y fallback a `default`.
- **ModeLoader**: componente que carga, valida y registra modos desde archivos YAML al arranque del sistema.
- **company_geo**: estructura de datos (pais/departamento/municipio/timezone) que condiciona busquedas normativas, tributarias y de fuentes oficiales locales.
- **Filtrado por Mode en ToolRegistry**: el Mode activo restringe dominios de tools y skills accesibles (integracion con `ToolRegistry` de spec 009).
- **Validacion al boot**: modos con referencias invalidas (skills inexistentes, playbooks inexistentes, rutas invalidas) no se registran.

### Out of Scope

- **Autodeteccion de modo por heuristica o LLM** (ModeResolver avanzado con regex/clasificador) -- roadmap post-MVP. En MVP solo se soporta activacion explicita y fallback a default.
- **Activacion por evento** (triggers proactivos que asignan modo) -- roadmap, requiere Dreaming (spec posterior).
- **Modos custom creados por el operador** -- la arquitectura lo permite pero el flujo CLI `vigilador-admin mode validate/register` es roadmap.
- **Intensidad operacional** (`REACTIVE`/`PROACTIVE`/`AUTONOMOUS`) -- documentada en schema pero no implementada funcionalmente en MVP; requiere Dreaming y goal-pursuit.
- **Modos CFO, Consultor Legal, Marketing, Vendedor B2B, Operaciones PYME** -- roadmap F4c (ver 00b).
- **PlaybookRunner y ComplexityClassifier** -- spec separado (012).
- **SubagentRegistry** -- spec separado (012).
- **Frontend de seleccion de modo** (chat con `/mode`) -- spec 013 (frontend).
- **SOUL overlay completo** (carga de soul.md + merge con mode overlay) -- se define el schema aqui pero la implementacion del merge de prompts es parte de la orquestacion (spec 012).

---

## Assumptions

- **A-01**: El `ToolRegistry` (spec 009) esta implementado y expone un mecanismo de filtrado por dominios y exclusiones que este spec consume.
- **A-02**: Los archivos de configuracion de empresa (`config/company/identity.md`, etc.) existen como resultado del onboarding (spec 009 FR-026).
- **A-03**: El campo `company_geo` se persiste durante el onboarding (spec 009 FR-026) y esta disponible como dato frozen para cualquier modo.
- **A-04**: En MVP, la activacion de modo es exclusivamente explicita (comando `/mode <id>` o default al iniciar sesion). No hay clasificacion automatica.
- **A-05**: Los playbooks referenciados por los modos MVP (`technology-watch`, `deep-research`, `general`) se implementan en spec 012. Este spec define la referencia pero no la ejecucion.
- **A-06**: El modo `Vigilancia Tech` envuelve el comportamiento existente del 2.0 (`BranchCoordinator` + 6 agentes de rama) sin modificaciones funcionales.
- **A-07**: Los archivos YAML de modos se ubican en `config/modes/` y se cargan al arranque del proceso. Cambios requieren reinicio (no hot-reload en MVP).
- **A-08**: `company_geo` requiere al menos `country` como campo obligatorio; `department` y `municipality` son opcionales pero, si presentes, condicionan la granularidad de busquedas normativas.

---

## User Scenarios & Testing

### Primary User Story

Como **usuario del Vigilador 3.0**, quiero **activar un modo especifico** (ej: `Vigilancia Tech`) para que el sistema adapte su personalidad, tools disponibles y contexto geografico a mi necesidad actual, **sin tener que configurar manualmente cada parametro en cada sesion**.

### Acceptance Scenarios

1. **Given** el sistema arrancado con los modos MVP registrados, **When** un usuario envia `/mode Vigilancia Tech`, **Then** el ModeResolver activa ese modo para la sesion, el ToolRegistry filtra tools a los dominios `search, research, web, analytics` y los playbooks disponibles se restringen a `technology-watch`.

2. **Given** un usuario que inicia sesion sin especificar modo, **When** el sistema procesa su primer mensaje, **Then** el ModeResolver asigna el modo `default` automaticamente y el ToolRegistry aplica los dominios `search, web, documents`.

3. **Given** el modo `CEO` activo, **When** el usuario solicita una accion que requiere una tool del dominio `finance` (no incluido en CEO), **Then** el sistema informa que la tool no esta disponible en el modo actual y sugiere cambiar de modo.

4. **Given** una empresa con `company_geo` configurado como Colombia/Santander/Barrancabermeja, **When** el modo activo procesa cualquier consulta, **Then** el contexto geografico se inyecta SIEMPRE en el prompt del agente con fuentes oficiales del municipio/departamento/pais en ese orden de especificidad.

5. **Given** un archivo `config/modes/invalido.yaml` con una referencia a un playbook inexistente, **When** el sistema arranca y ejecuta ModeLoader, **Then** ese modo no se registra, se emite un log de error con la causa especifica y los demas modos validos se cargan normalmente.

6. **Given** el modo `Vigilancia Tech` activo, **When** se ejecuta el playbook `technology-watch`, **Then** los 6 agentes de rama del 2.0 operan sin diferencias funcionales respecto al comportamiento del 2.0.

7. **Given** un usuario con modo `CEO` activo, **When** envia `/mode default`, **Then** el sistema cambia al modo default, reconstruye el contexto de la sesion y aplica los nuevos filtros de tools/skills.

### Edge Cases

- **EC-01**: Usuario solicita `/mode CFO` (modo roadmap no implementado en MVP) -- el sistema responde que el modo no esta disponible y lista los modos activos.
- **EC-02**: Archivo YAML de modo con `company_geo` sin campo `country` -- la validacion rechaza el modo al boot con error explicito.
- **EC-03**: Dos archivos YAML con el mismo `id` en `config/modes/` -- el ModeLoader rechaza el segundo con error de duplicado; el primero cargado (orden alfabetico) prevalece.
- **EC-04**: El usuario cambia de modo mid-sesion con `/mode <otro>` -- el contexto previo se descarta y se reconstruye desde cero con el nuevo modo (no hay merge).
- **EC-05**: `company_geo` tiene `country` pero no `department` ni `municipality` -- las busquedas normativas se limitan al nivel nacional; no se asume subdivision.

---

## Functional Requirements

### Schema YAML de Mode

- **FR-001**: El sistema MUST definir un schema de Mode con los siguientes campos obligatorios: `id` (string unico), `display_name` (string), `description` (string), `version` (semver string).
- **FR-002**: El schema MUST soportar los siguientes campos opcionales: `soul_overlay` (tone, vocabulary_emphasis, do_rules, dont_rules), `company_subset` (files, sections_filter), `company_geo` (country, department, municipality, timezone, regulatory_sources_policy), `skills` (categories, individual, excluded), `playbooks` (default, allowed), `tools` (domains, excluded), `mode_settings` (language_default, intensity).
- **FR-003**: El campo `company_geo` dentro del schema MUST requerir al menos `country` cuando esta presente; `department`, `municipality` y `timezone` son opcionales.
- **FR-004**: El campo `tools.domains` MUST ser una lista de strings que corresponden a dominios registrados en el ToolRegistry; el campo `tools.excluded` MUST ser una lista de strings con formato `<tool_name>` o `<tool_name>.<capability>`.

### ModeLoader

- **FR-005**: El sistema MUST cargar todos los archivos `*.yaml` de `config/modes/` al arranque y validar cada uno contra el schema definido en FR-001/FR-002.
- **FR-006**: El ModeLoader MUST rechazar (no registrar) cualquier modo cuyo `id` ya exista en el registro, emitiendo log de error con la ruta del archivo duplicado.
- **FR-007**: El ModeLoader MUST rechazar cualquier modo que referencie playbooks no existentes en `config/playbooks/` (validacion de referencias cruzadas).
- **FR-008**: El ModeLoader MUST rechazar cualquier modo cuyo `company_geo` incluya el campo pero omita `country`, emitiendo error especifico.
- **FR-009**: Modos que fallan validacion MUST no afectar la carga de los demas modos validos (fallo aislado).

### ModeResolver/Router

- **FR-010**: El sistema MUST proveer un componente `ModeResolver` que, dado un comando explicito `/mode <id>`, active el modo correspondiente para la sesion del usuario.
- **FR-011**: El ModeResolver MUST asignar el modo `default` cuando el usuario inicia sesion sin especificar modo.
- **FR-012**: El ModeResolver MUST rechazar la activacion de un modo no registrado (por fallo de validacion o por no existir) con mensaje informativo que liste los modos disponibles.
- **FR-013**: El ModeResolver MUST soportar cambio de modo mid-sesion via `/mode <id>`, descartando el contexto del modo anterior y reconstruyendo desde cero.
- **FR-014**: El ModeResolver MUST exponer el modo activo actual como dato consultable por cualquier componente del sistema (ToolRegistry, PlaybookRunner, orquestador).

### Filtrado por Mode en ToolRegistry

- **FR-015**: Cuando un modo esta activo, el ToolRegistry MUST filtrar las tools disponibles a aquellas cuyos dominios esten incluidos en `Mode.tools.domains`.
- **FR-016**: El ToolRegistry MUST excluir tools listadas en `Mode.tools.excluded` del modo activo, independientemente de su dominio.
- **FR-017**: Si un agente solicita una tool excluida por el modo activo, el sistema MUST retornar un error explicito indicando que la tool no esta permitida en el modo actual.

### company_geo

- **FR-018**: El sistema MUST persistir `company_geo` (country, department, municipality, timezone) como parte del perfil de empresa durante el onboarding y hacerlo disponible como dato frozen para todos los modos.
- **FR-019**: Cuando un modo esta activo, el sistema MUST inyectar `company_geo` SIEMPRE en el contexto del agente (KISS/YAGNI), proporcionando la informacion geografica al nivel mas especifico disponible (municipio > departamento > pais). No se aplica heuristica para detectar si la consulta involucra normativa.
- **FR-020**: Si `company_geo` no tiene `department` ni `municipality`, las busquedas normativas MUST limitarse al nivel nacional sin asumir subdivision.

### Catalogo MVP

- **FR-021**: El sistema MUST incluir en MVP los siguientes modos preconfigurados y validados: `default` (dominios: search, web, documents; playbook default: general), `vigilancia-tech` (dominios: search, research, web, analytics; playbook default: technology-watch), `ceo` (dominios: search, research, productivity; playbooks: decision-debate, deep-research, general).
- **FR-022**: El modo `vigilancia-tech` MUST preservar compatibilidad total con el 2.0: su playbook `technology-watch` invoca `BranchCoordinator` y los 6 agentes de rama sin modificaciones funcionales.
- **FR-023**: Los modos roadmap (CFO, Consultor Legal, Marketing, Vendedor B2B, Operaciones PYME) MUST estar documentados como archivos YAML en `config/modes/` con un campo `status: roadmap` que impida su registro por el ModeLoader en MVP.

---

## Key Entities

- **Mode** (`config/modes/<id>.yaml`): unidad user-facing que define la personalidad, contexto, skills, playbooks y tools del asistente para una sesion. Atributos principales: `id`, `display_name`, `description`, `version`, `soul_overlay`, `company_subset`, `company_geo`, `skills`, `playbooks`, `tools`, `mode_settings`.
- **ModeResolver**: componente que determina el modo activo para una sesion. Recibe comandos explicitos (`/mode <id>`) y aplica fallback a `default`. Expone el modo activo como dato consultable.
- **ModeLoader**: componente que al arranque lee `config/modes/*.yaml`, valida contra schema, y registra los modos validos en memoria para consulta del ModeResolver.
- **company_geo**: estructura de datos geografica (country, department, municipality, timezone) que condiciona busquedas normativas y tributarias. Vive en el perfil de empresa persistido durante onboarding y se referencia desde cada Mode.
- **Mode registry** (en memoria): diccionario de modos validos cargados al boot, consultable por `ModeResolver` y `ToolRegistry`.

---

## Success Criteria

- **SC-001**: Los 3 modos MVP (`default`, `vigilancia-tech`, `ceo`) se cargan y validan sin error al arranque del sistema en menos de 2 segundos.
- **SC-002**: El cambio de modo via `/mode <id>` se resuelve en menos de 500 ms (sin contar recarga de playbook).
- **SC-003**: El ToolRegistry filtra correctamente al 100% de los escenarios de prueba: tools de dominios no permitidos por el modo activo no aparecen en el listado.
- **SC-004**: Un modo con referencia invalida (playbook inexistente, company_geo sin country) es rechazado al boot sin afectar la carga de los demas modos.
- **SC-005**: El modo `vigilancia-tech` ejecuta el playbook `technology-watch` con los 6 agentes de rama del 2.0 produciendo resultados identicos al comportamiento del 2.0.
- **SC-006**: `company_geo` con los 3 niveles (pais/departamento/municipio) se inyecta correctamente en el contexto del agente, verificable en el prompt enviado al LLM.
- **SC-007**: Los modos marcados `status: roadmap` no aparecen en el listado de modos disponibles para el usuario en MVP.

---

## Traceability Matrix

| FR | Acceptance scenario | Success criterion | Fuente plan |
|----|---------------------|-------------------|-------------|
| FR-001 | AS-5 | SC-001 | 02-modos sec. "Schema YAML de un Mode" |
| FR-002 | AS-4 | SC-006 | 02-modos sec. "Schema YAML de un Mode" |
| FR-003 | EC-02 | SC-004 | 02-modos sec. "company_geo" + C0 correccion |
| FR-004 | AS-3 | SC-003 | 02-modos sec. "Schema YAML" campo tools |
| FR-005 | AS-5 | SC-001 | 02-modos sec. "Validacion del schema" |
| FR-006 | EC-03 | SC-004 | 02-modos sec. "Validacion del schema" |
| FR-007 | AS-5 | SC-004 | 02-modos sec. "Validacion del schema" |
| FR-008 | EC-02 | SC-004 | 02-modos sec. "company_geo" |
| FR-009 | AS-5 | SC-004 | Constitucion #4 (manejo errores estricto) |
| FR-010 | AS-1 | SC-002 | 02-modos sec. "Activacion > Por canal explicito" |
| FR-011 | AS-2 | SC-002 | 02-modos sec. "Activacion > autodeteccion fallback" |
| FR-012 | EC-01 | SC-007 | 02-modos sec. "Activacion" |
| FR-013 | AS-7 | SC-002 | 02-modos sec. "Mode no puede ser modificado mid-sesion salvo /mode" |
| FR-014 | AS-1, AS-3 | SC-003 | 02-modos sec. "Composicion Mode > Playbook" |
| FR-015 | AS-1, AS-3 | SC-003 | 02-modos sec. "Reglas de composicion #2" |
| FR-016 | AS-3 | SC-003 | 02-modos sec. "Schema YAML" tools.excluded |
| FR-017 | AS-3 | SC-003 | 02-modos sec. "Reglas de composicion #2" |
| FR-018 | AS-4 | SC-006 | 02-modos sec. "company_geo" + 00b C1.6 onboarding |
| FR-019 | AS-4 | SC-006 | 02-modos sec. "Reglas de composicion #6" |
| FR-020 | EC-05 | SC-006 | 02-modos sec. "company_geo" validacion |
| FR-021 | AS-1, AS-2 | SC-001, SC-005 | 00b sec. "Modos MVP vs roadmap" |
| FR-022 | AS-6 | SC-005 | 00b sec. "Modos MVP" + 02-modos nota Vigilancia Tech |
| FR-023 | EC-01 | SC-007 | 00b sec. "Modos MVP vs roadmap" (CFO, Legal, etc.) |

**Cobertura**: 23/23 FR mapeados. Todos los FR tienen al menos un AS o EC y al menos un SC asociado.

---

## Delivery Constraints

- **Constitucion v1.2.0 -- Simplicidad obligatoria (#2)**: el ModeResolver en MVP es un lookup directo por `id`; no se implementa clasificacion automatica ni heuristicas hasta que el roadmap lo requiera.
- **Constitucion v1.2.0 -- Modularidad primero (#3)**: ModeLoader, ModeResolver y el filtrado por Mode en ToolRegistry son componentes separados con responsabilidad unica.
- **Constitucion v1.2.0 -- Manejo de errores estricto (#4)**: modos invalidos propagan error con contexto (ruta del archivo, campo faltante, referencia rota) sin try/except defensivos.
- **Constitucion v1.2.0 -- YAGNI**: no se implementa hot-reload de modos, intensidad operacional funcional, ni autodeteccion por heuristica/LLM en MVP.
- **C1 MVP scope (00b)**: solo 3 modos operativos (default, Vigilancia Tech, CEO reducido). Los demas se documentan pero no se activan.
- **CQS (Constitucion -- Desarrollo y Arquitectura)**: `get_active()` es query pura; `activate()` y `change_mode()` son commands que mutan `_active_modes` y retornan ModeConfig como excepcion pragmatica documentada. Las mutaciones de contexto de sesion son responsabilidad del orquestador.
- **Regla C0 #10**: archivos de implementacion no superan 400 LOC.
- **Dependencia spec 009**: el ToolRegistry y company_geo (onboarding) deben estar implementados antes de que este spec sea funcional.
- **Limitacion conocida MVP**: los dominios `analytics` y `productivity` de los modos MVP pueden no tener tools registradas en el ToolRegistry durante el MVP. El filtrado retornara subconjunto vacio para esos dominios; esto es comportamiento esperado, no un error.

---

## Dependencies on previous specs

- **spec 009 (MVP Foundation)**: provee `ToolRegistry` con mecanismo de filtrado por dominios, `company_geo` persistido en onboarding, estructura `config/modes/` creada en F0.

## Specs descendientes que dependen de este

- **spec 012 (MVP F4a modos+playbooks)**: consume ModeResolver para determinar que playbooks ejecutar; consume el catalogo de modos para validar compatibilidad Mode-Playbook.
- **spec 013 (MVP F4a frontend)**: consume ModeResolver para exponer selector de modo en el chat (`/mode <id>`).
