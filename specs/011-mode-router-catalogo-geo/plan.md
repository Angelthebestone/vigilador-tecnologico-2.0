# Implementation Plan: Mode Router, Catalogo de Modos y company_geo

**Feature ID**: 011-mode-router-catalogo-geo
**Created**: 2026-05-29
**Spec**: [spec.md](spec.md)

## Problem

El Vigilador 3.0 necesita que cada sesion opere bajo un Modo explicito que determine personalidad, skills, playbooks, tools y contexto geografico. Sin esta capa, el sistema no diferencia entre un usuario que necesita vigilancia tecnologica y uno que necesita asistencia ejecutiva. Ademas, la normativa y fuentes oficiales varian segun la ubicacion geografica de la empresa (pais/departamento/municipio). Actualmente el repo tiene:

- Cero schema YAML de Mode ni catalogo de modos.
- Cero componente `ModeResolver` que resuelva modo activo por sesion.
- Cero componente `ModeLoader` que valide y registre modos al arranque.
- Cero integracion entre modo activo y `ToolRegistry` (filtrado por dominios).
- Cero estructura `company_geo` funcional que condicione busquedas normativas.
- La estructura `config/modes/` creada como placeholder en spec 009 (F0) sin contenido funcional.

Este plan describe como construir el ModeLoader, ModeResolver, catalogo MVP (3 modos), integracion con ToolRegistry y company_geo en fases verificables sin tocar el 2.0.

## Approach

Implementar 3 componentes con responsabilidad unica bajo `src/vigilancia_multiagente/enterprise/modes/`: (1) `ModeLoader` que carga y valida archivos YAML de `config/modes/` al arranque, (2) `ModeResolver` que resuelve el modo activo por sesion via comando explicito o fallback a default, (3) `ModeToolFilter` como componente externo que consulta `ToolCard.domains` del `ToolRegistry` existente (spec 009) para filtrar tools por dominios/exclusiones del modo activo, sin modificar el modulo `tooling` (DIP). Crear los 3 archivos YAML de modos MVP (`default`, `vigilancia-tech`, `ceo`) mas los modos roadmap con `status: roadmap`. Persistir `company_geo` como dato frozen consultable desde cualquier modo para condicionar busquedas normativas.

---

## Technical Context

| Area | Decision |
|------|----------|
| Lenguaje | Python 3.11+ (mismo que 2.0 y spec 009) |
| Schema de Mode | Archivos YAML en `config/modes/<id>.yaml` validados contra dataclass/Pydantic model al boot |
| ModeLoader | Componente que lee `config/modes/*.yaml`, valida schema + referencias cruzadas, registra en memoria |
| ModeResolver | Componente con commands (`activate`, `change_mode`) que mutan `_active_modes` y query pura (`get_active`). Commands retornan ModeConfig como excepcion pragmatica documentada |
| Mode registry | Diccionario en memoria de modos validos, consultable por ModeResolver y ToolRegistry |
| Filtrado ToolRegistry | `ModeToolFilter` (componente externo en `enterprise/modes/`) consulta `ToolCard.domains` via la API publica del `ToolRegistry`. El modulo `tooling` NO depende de `modes` (DIP, Bajo Acoplamiento) |
| company_geo | Estructura persistida en `company_profile` (tabla spec 009) y referenciada como dato frozen por cada modo. Nota: `regulatory_sources_policy` es campo del schema YAML del Mode (dentro de `company_geo`), NO columna de la tabla `company_profile` |
| Activacion MVP | Solo explicita (`/mode <id>`) + fallback a `default`. Cero autodeteccion ni heuristica |
| Modos MVP | `default`, `vigilancia-tech`, `ceo` (3 operativos). Los demas con `status: roadmap` |
| Archivos <= 400 LOC | Cada archivo nuevo respeta el limite constitucional |

## External Constraints

| Constraint | Impact |
|------------|--------|
| Cero cambios al 2.0 (constitucion #5) | Los 6 agentes de rama, BranchCoordinator y API v2 no se modifican |
| Dependencia spec 009 | Requiere `ToolRegistry`, `company_profile` table y estructura `config/modes/` existentes |
| Constitucion #2 Simplicidad | ModeResolver es lookup directo por id; cero clasificacion automatica en MVP |
| Constitucion #4 Errores estrictos | Modos invalidos propagan error con contexto (ruta, campo, referencia rota) |
| YAGNI | Cero hot-reload, cero intensidad funcional, cero autodeteccion por LLM en MVP |
| C1 MVP scope (00b) | Solo 3 modos operativos. Los demas documentados pero no activables |
| PlaybookRunner no existe aun | Este spec valida que playbooks referenciados existan como archivo en `config/playbooks/`; la ejecucion es spec 012 |
| CQS (constitucion) | ModeResolver: `get_active()` es query pura; `activate()` y `change_mode()` son commands (mutan `_active_modes`) con retorno pragmatico de ModeConfig |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/enterprise/modes/__init__.py` | Marker del subpaquete modes |
| `src/vigilancia_multiagente/enterprise/modes/mode_schema.py` | Dataclasses/modelos del schema de Mode (ModeConfig, SoulOverlay, CompanyGeo, SkillsConfig, PlaybooksConfig, ToolsConfig, ModeSettings) |
| `src/vigilancia_multiagente/enterprise/modes/mode_loader.py` | ModeLoader: carga YAML, valida schema, valida referencias cruzadas, registra modos validos |
| `src/vigilancia_multiagente/enterprise/modes/mode_resolver.py` | ModeResolver: resuelve modo activo por sesion, expone modo actual, soporta cambio mid-sesion |
| `src/vigilancia_multiagente/enterprise/modes/mode_registry.py` | ModeRegistry: diccionario en memoria de modos validos, interfaz de consulta |
| `src/vigilancia_multiagente/enterprise/modes/mode_tool_filter.py` | Integracion con ToolRegistry: filtra tools por dominios/exclusiones del modo activo |
| `config/modes/default.yaml` | Modo default MVP: dominios search, web, documents; playbook general |
| `config/modes/vigilancia-tech.yaml` | Modo Vigilancia Tech MVP: dominios search, research, web, analytics; playbook technology-watch |
| `config/modes/ceo.yaml` | Modo CEO MVP: dominios search, research, productivity; playbooks decision-debate, deep-research, general |
| `config/modes/cfo.yaml` | Modo CFO roadmap (`status: roadmap`) |
| `config/modes/consultor-legal.yaml` | Modo Consultor Legal roadmap (`status: roadmap`) |
| `config/modes/marketing.yaml` | Modo Marketing roadmap (`status: roadmap`) |
| `config/modes/vendedor-b2b.yaml` | Modo Vendedor B2B roadmap (`status: roadmap`) |
| `config/modes/operaciones-pyme.yaml` | Modo Operaciones PYME roadmap (`status: roadmap`) |
| `config/playbooks/.gitkeep` | Placeholder para que la validacion de referencias cruzadas tenga directorio (si no existe ya) |
| `tests/enterprise/modes/test_mode_schema.py` | Tests de validacion del schema (campos obligatorios, opcionales, company_geo) |
| `tests/enterprise/modes/test_mode_loader.py` | Tests de carga, validacion, rechazo de invalidos, aislamiento de fallos |
| `tests/enterprise/modes/test_mode_resolver.py` | Tests de activacion, fallback, cambio mid-sesion, rechazo de modo inexistente |
| `tests/enterprise/modes/test_mode_tool_filter.py` | Tests de filtrado por dominios, exclusiones, error explicito en tool no permitida |
| `tests/enterprise/modes/test_company_geo.py` | Tests de inyeccion de company_geo en contexto, niveles de especificidad |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/api/dependencies.py` | Wirear ModeLoader (singleton al boot), ModeRegistry, ModeResolver, ModeToolFilter. Sin tocar wirings del 2.0 |
| `src/vigilancia_multiagente/api/app.py` | Invocar ModeLoader.load_all() al startup del app (evento lifespan). Sin tocar routers existentes |

---

## Constitution Check (Pre-Design)

- **Gate result**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`)
- **Alignment**:
  - **Pensar Antes de Codificar**: 8 assumptions explicitas en el spec (A-01..A-08). Fase 1 valida precondiciones antes de implementar. Dependencia de spec 009 declarada.
  - **Simplicidad Obligatoria**: ModeResolver es un lookup por id en diccionario. Cero heuristicas, cero clasificacion LLM, cero hot-reload. Solo lo que el spec pide.
  - **Modularidad Primero**: 5 archivos Python con responsabilidad unica (schema, loader, resolver, registry, tool_filter). Cada uno < 400 LOC.
  - **Cambios Quirurgicos y Trazables**: 2 archivos existentes modificados en modo aditivo (anadir wire a dependencies, anadir invocacion a app startup). Cero borrado, cero renombre, cero cambios al 2.0. El modulo `tooling` no se modifica (DIP).
  - **Entrega Verificable**: 7 success criteria del spec mapeados a fases con tests especificos. Cada fase produce artefacto verificable.
- **Diseno de Software**: SRP (cada archivo un concern), SoC (schema vs carga vs resolucion vs filtrado), DIP (ModeResolver depende de abstraccion ModeRegistry, no de ModeLoader directamente; ModeToolFilter depende de la API publica de ToolRegistry, no al reves), CQS (`get_active` query pura; `activate`/`change_mode` commands con retorno pragmatico), KISS (YAML plano, validacion directa, cero metaprogramacion), OCP (nuevos modos se anaden como archivos YAML sin tocar codigo).

---

## Phases

### Phase 1 -- Validacion de precondiciones (0.5 dias)

1. Verificar que `config/modes/` existe como directorio (creado en spec 009 F0).
2. Verificar que `ToolRegistry` de spec 009 esta implementado y expone mecanismo de filtrado por dominios.
3. Verificar que tabla `company_profile` existe con campos `country`, `department`, `municipality`, `timezone`.
4. Verificar que `config/playbooks/` existe como directorio (para validacion de referencias cruzadas).
5. Documentar cualquier gap encontrado como blocker antes de continuar.

**Output**: precondiciones validadas o gaps documentados. Cero codigo nuevo.

**Traza**: A-01, A-02, A-03 del spec.

### Phase 2 -- Schema de Mode y modelos (1-2 dias)

1. Crear `enterprise/modes/__init__.py` (marker).
2. Crear `enterprise/modes/mode_schema.py` (~200 LOC):
   - Dataclass `CompanyGeo` con campos: `country` (obligatorio), `department` (opcional), `municipality` (opcional), `timezone` (opcional), `regulatory_sources_policy` (opcional).
   - Dataclass `SoulOverlay` con campos: `tone`, `vocabulary_emphasis`, `do_rules`, `dont_rules` (todos opcionales).
   - Dataclass `CompanySubset` con campos: `files`, `sections_filter` (ambos opcionales).
   - Dataclass `SkillsConfig` con campos: `categories`, `individual`, `excluded` (todos opcionales, listas).
   - Dataclass `PlaybooksConfig` con campos: `default` (string), `allowed` (lista strings).
   - Dataclass `ToolsConfig` con campos: `domains` (lista strings obligatoria), `excluded` (lista strings opcional).
   - Dataclass `ModeSettings` con campos: `language_default`, `intensity` (ambos opcionales).
   - Dataclass `ModeConfig` con campos obligatorios (`id`, `display_name`, `description`, `version`) y opcionales (`soul_overlay`, `company_subset`, `company_geo`, `skills`, `playbooks`, `tools`, `mode_settings`, `status`).
   - Funcion `parse_mode_yaml(path: Path) -> ModeConfig` que lee YAML y construye el modelo con validacion de campos obligatorios.
3. Tests `tests/enterprise/modes/test_mode_schema.py`:
   - YAML valido con todos los campos se parsea correctamente.
   - YAML sin `id` falla con error explicito.
   - YAML con `company_geo` sin `country` falla con error explicito (FR-008).
   - YAML con `status: roadmap` se parsea correctamente.
   - Campos opcionales ausentes no causan error.

**Output**: schema de Mode implementado y testeado. FR-001, FR-002, FR-003 cubiertos.

**Traza**: FR-001, FR-002, FR-003, FR-004 -> spec sec. "Schema YAML de Mode"; plan 02-modos sec. "Schema YAML de un Mode".

### Phase 3 -- ModeLoader y validacion (2-3 dias)

1. Crear `enterprise/modes/mode_registry.py` (~80 LOC):
   - Clase `ModeRegistry` con diccionario interno `_modes: dict[str, ModeConfig]`.
   - Metodos: `register(mode: ModeConfig)`, `get(id: str) -> ModeConfig | None`, `list_available() -> list[ModeConfig]`, `exists(id: str) -> bool`.
   - `register()` rechaza duplicados con error explicito (FR-006).
2. Crear `enterprise/modes/mode_loader.py` (~250 LOC):
   - Clase `ModeLoader` con constructor que recibe `modes_dir: Path` y `playbooks_dir: Path`.
   - Metodo `load_all() -> ModeRegistry`:
     - Lee todos los `*.yaml` de `modes_dir`.
     - Para cada archivo: parsea con `parse_mode_yaml()`, valida referencias cruzadas, registra si valido.
     - Modos con `status: roadmap` se parsean pero NO se registran en el registry (FR-023).
     - Modos con `id` duplicado: segundo rechazado con log de error (FR-006).
     - Modos con playbook referenciado inexistente en `playbooks_dir`: rechazados con log (FR-007).
     - Modos con `company_geo` sin `country`: rechazados con log (FR-008).
     - Fallo de un modo no afecta carga de los demas (FR-009).
   - Metodo `validate_single(path: Path) -> list[str]` que retorna lista de errores (para CLI futuro).
   - Errores con contexto: ruta del archivo, campo faltante, referencia rota. Sin try/except defensivos.
3. Tests `tests/enterprise/modes/test_mode_loader.py`:
   - 3 modos validos se cargan correctamente.
   - Modo con `status: roadmap` no aparece en registry.
   - Modo con id duplicado: segundo rechazado, primero prevalece.
   - Modo con playbook inexistente: rechazado sin afectar otros.
   - Modo con company_geo sin country: rechazado.
   - Carga de 3 modos MVP en < 2 segundos (SC-001).
   - Directorio vacio retorna registry vacio sin error.

**Output**: ModeLoader + ModeRegistry funcionales y testeados. FR-005 a FR-009, FR-023 cubiertos.

**Traza**: FR-005..FR-009, FR-023 -> spec sec. "ModeLoader"; plan 02-modos sec. "Validacion del schema".

### Phase 4 -- ModeResolver (1-2 dias)

1. Crear `enterprise/modes/mode_resolver.py` (~150 LOC):
   - Clase `ModeResolver` con constructor que recibe `registry: ModeRegistry`.
   - Metodo `activate(session_id: str, mode_id: str) -> ModeConfig`:
     - Si `mode_id` no existe en registry: levanta error con lista de modos disponibles (FR-012).
     - Si existe: almacena como modo activo para la sesion (FR-010).
     - Retorna el ModeConfig activado.
   - Metodo `get_active(session_id: str) -> ModeConfig`:
     - Si no hay modo activo para la sesion: activa `default` automaticamente (FR-011).
     - Retorna el modo activo actual (FR-014).
   - Metodo `change_mode(session_id: str, new_mode_id: str) -> ModeConfig`:
     - Descarta contexto del modo anterior (FR-013).
     - Activa el nuevo modo.
     - Retorna el nuevo ModeConfig.
   - Almacenamiento interno: `_active_modes: dict[str, ModeConfig]` (en memoria, por sesion).
   - CQS: `activate()` y `change_mode()` son COMMANDS (mutan `_active_modes`); `get_active()` es QUERY pura (solo lee). Excepcion pragmatica: `activate()` y `change_mode()` retornan el `ModeConfig` activado para evitar una segunda llamada inmediata; esto es un command que retorna resultado por conveniencia, no una query.
2. Tests `tests/enterprise/modes/test_mode_resolver.py`:
   - Activacion explicita de modo existente funciona.
   - Activacion de modo inexistente falla con lista de disponibles.
   - Sesion sin modo explicito recibe `default` automaticamente.
   - Cambio mid-sesion descarta modo anterior y activa nuevo.
   - `get_active()` retorna el modo correcto tras activacion.
   - Resolucion en < 500 ms (SC-002).

**Output**: ModeResolver funcional y testeado. FR-010 a FR-014 cubiertos.

**Traza**: FR-010..FR-014 -> spec sec. "ModeResolver/Router"; plan 02-modos sec. "Activacion > Por canal explicito".

### Phase 5 -- Filtrado por Mode en ToolRegistry (1-2 dias)

1. Crear `enterprise/modes/mode_tool_filter.py` (~120 LOC):
   - Clase `ModeToolFilter` con constructor que recibe `tool_registry: ToolRegistry`.
   - Metodo `filter_tools(mode: ModeConfig) -> list[ToolCard]`:
     - Obtiene todas las tools del registry.
     - Filtra a aquellas cuyos dominios esten en `mode.tools.domains` (FR-015).
     - Excluye tools listadas en `mode.tools.excluded` (FR-016).
     - Retorna lista filtrada.
   - Metodo `check_tool_allowed(mode: ModeConfig, tool_name: str) -> bool`:
     - Retorna True si la tool esta permitida por el modo.
     - Si no permitida: levanta error explicito con nombre del modo y tool (FR-017).
2. El `ToolRegistry` NO se modifica. El filtrado por modo se realiza externamente via `ModeToolFilter` que consulta `ToolCard.domains` (composicion en el wiring). Esto respeta DIP y Bajo Acoplamiento: el modulo `tooling` no depende de `modes`.
3. Tests `tests/enterprise/modes/test_mode_tool_filter.py`:
   - Modo con dominios `[search, web]` filtra correctamente (solo tools de esos dominios).
   - Tool en `excluded` no aparece aunque su dominio este permitido.
   - Solicitud de tool excluida retorna error explicito con nombre de modo.
   - Modo sin campo `tools` retorna todas las tools (sin filtro).
   - 100% de escenarios de prueba filtran correctamente (SC-003).

**Output**: filtrado por Mode integrado con ToolRegistry. FR-015 a FR-017 cubiertos.

**Limitacion conocida MVP**: los dominios `analytics` y `productivity` referenciados por los modos `vigilancia-tech` y `ceo` pueden no tener tools registradas en el ToolRegistry durante el MVP. El filtrado retornara un subconjunto vacio para esos dominios; esto es comportamiento esperado, no un error.

**Traza**: FR-015..FR-017 -> spec sec. "Filtrado por Mode en ToolRegistry"; plan 02-modos sec. "Reglas de composicion #2".

### Phase 6 -- Catalogo YAML de modos MVP y roadmap (1 dia)

1. Crear `config/modes/default.yaml`:
   - `id: default`, `display_name: "Asistente General"`, `version: "1.0.0"`.
   - `tools.domains: [search, web, documents]`.
   - `playbooks.default: general`, `playbooks.allowed: [general]`.
   - Sin `company_geo` (hereda del perfil de empresa).
   - Sin `soul_overlay` (usa SOUL base).
2. Crear `config/modes/vigilancia-tech.yaml`:
   - `id: vigilancia-tech`, `display_name: "Vigilancia Tecnologica"`, `version: "1.0.0"`.
   - `tools.domains: [search, research, web, analytics]`.
   - `playbooks.default: technology-watch`, `playbooks.allowed: [technology-watch]`.
   - `soul_overlay.tone: "analitico, tecnico, orientado a tendencias"`.
   - Nota en description: preserva compatibilidad total con 2.0 (FR-022).
3. Crear `config/modes/ceo.yaml`:
   - `id: ceo`, `display_name: "Director Ejecutivo"`, `version: "1.0.0"`.
   - `tools.domains: [search, research, productivity]`.
   - `playbooks.default: general`, `playbooks.allowed: [decision-debate, deep-research, general]`.
   - `soul_overlay.tone: "estrategico, decisivo, prioriza ROI"`.
4. Crear archivos YAML roadmap (`cfo.yaml`, `consultor-legal.yaml`, `marketing.yaml`, `vendedor-b2b.yaml`, `operaciones-pyme.yaml`):
   - Cada uno con `status: roadmap` y schema completo documentado.
   - El ModeLoader los parsea pero no los registra (FR-023).
5. Crear archivos placeholder de playbooks referenciados si no existen:
   - `config/playbooks/general.yaml` (placeholder minimo para que la validacion de referencias pase).
   - `config/playbooks/technology-watch.yaml` (placeholder minimo).
   - `config/playbooks/decision-debate.yaml` (placeholder minimo).
   - `config/playbooks/deep-research.yaml` (placeholder minimo).
   - Nota: estos son placeholders de schema; la implementacion funcional de playbooks es spec 012.

**Output**: 8 archivos YAML de modos + 4 placeholders de playbooks. FR-021, FR-022, FR-023 cubiertos.

**Traza**: FR-021..FR-023 -> spec sec. "Catalogo MVP"; plan 02-modos sec. "Catalogo inicial de Modos".

### Phase 7 -- company_geo e inyeccion en contexto (1 dia)

1. Verificar que `company_profile` (spec 009) persiste `country`, `department`, `municipality`, `timezone`.
2. Implementar en `mode_resolver.py` o componente dedicado la logica de inyeccion de `company_geo`:
   - El `company_geo` del perfil de empresa se inyecta SIEMPRE en el contexto del modo activo (KISS/YAGNI). No se aplica heuristica para detectar si la consulta involucra normativa (FR-019).
   - Si `company_geo` no tiene `department` ni `municipality`: busquedas limitadas a nivel nacional (FR-020).
   - Orden de especificidad: municipio > departamento > pais (FR-019).
3. Crear funcion `build_geo_context(company_geo: CompanyGeo) -> str` en `mode_schema.py` o archivo dedicado que genera el fragmento de contexto inyectable en el prompt.
4. Tests `tests/enterprise/modes/test_company_geo.py`:
   - company_geo con 3 niveles genera contexto con municipio/departamento/pais.
   - company_geo solo con country genera contexto limitado a nivel nacional.
   - company_geo sin department ni municipality no asume subdivision (EC-05).
   - Contexto generado es verificable en el prompt (SC-006).

**Output**: company_geo funcional e inyectable. FR-018, FR-019, FR-020 cubiertos.

**Traza**: FR-018..FR-020 -> spec sec. "company_geo"; plan 02-modos sec. "company_geo" + "Reglas de composicion #6".

### Phase 8 -- Integracion y wiring (0.5 dias)

1. Modificar `api/dependencies.py`:
   - Wirear `ModeLoader` como singleton que se ejecuta al boot.
   - Wirear `ModeRegistry` como resultado de `ModeLoader.load_all()`.
   - Wirear `ModeResolver` con el registry.
   - Wirear `ModeToolFilter` con el `ToolRegistry` existente (composicion externa; tooling no importa modes).
   - Sin tocar wirings del 2.0.
2. Modificar `api/app.py`:
   - En el evento lifespan (startup), invocar `ModeLoader.load_all()` y almacenar el registry.
   - Sin tocar routers existentes.
3. Verificar que el arranque del sistema carga los 3 modos MVP sin error en < 2 s (SC-001).

**Output**: sistema arranca con modos cargados y resolver disponible.

**Traza**: SC-001, A-07 del spec.

### Phase 9 -- Verificacion integral (0.5 dias)

1. Correr toda la bateria `pytest` y verificar 0 regresiones en el 2.0.
2. Verificar SC-001: 3 modos MVP cargan sin error en < 2 s.
3. Verificar SC-002: cambio de modo via activate/change_mode en < 500 ms.
4. Verificar SC-003: filtrado de tools por modo al 100% de escenarios.
5. Verificar SC-004: modo invalido rechazado sin afectar otros.
6. Verificar SC-005: modo `vigilancia-tech` referencia playbook `technology-watch` correctamente (ejecucion funcional es spec 012).
7. Verificar SC-006: company_geo inyectado correctamente en contexto.
8. Verificar SC-007: modos `status: roadmap` no aparecen en listado disponible.
9. Verificar `scripts/check-layer-imports.py` sin nuevas violaciones.

**Output**: spec 011 completado, listo para spec 012 (playbooks + orquestacion).

**Traza**: SC-001..SC-007 del spec.

---

## Rollout Strategy

- **Incremental por fase**: cada fase produce artefacto verificable. Tests deben pasar antes de avanzar.
- **Backward compatibility**: cero cambios al 2.0. Los 6 agentes de rama, BranchCoordinator y API v2 no se tocan.
- **Coexistencia**: el ModeLoader carga modos al boot sin afectar el flujo existente del 2.0. El ModeResolver solo se invoca desde codigo nuevo bajo `enterprise/`.
- **Feature flags**: cero necesarios. La existencia de los componentes de modes no afecta al 2.0.
- **Modos roadmap**: presentes como YAML documentado pero no registrados ni activables. Cuando se implementen (F4c), solo se remueve `status: roadmap` del YAML.
- **Playbooks placeholder**: archivos minimos que permiten validacion de referencias. La implementacion funcional llega en spec 012.
- **Rollback**: si algo falla, los archivos YAML se eliminan y los componentes Python se remueven sin impacto al 2.0.

---

## Success Criteria

- **SC-001**: Los 3 modos MVP (`default`, `vigilancia-tech`, `ceo`) se cargan y validan sin error al arranque en menos de 2 segundos.
- **SC-002**: El cambio de modo via `ModeResolver.activate()` se resuelve en menos de 500 ms.
- **SC-003**: El ToolRegistry filtra correctamente al 100% de los escenarios de prueba: tools de dominios no permitidos por el modo activo no aparecen en el listado.
- **SC-004**: Un modo con referencia invalida (playbook inexistente, company_geo sin country) es rechazado al boot sin afectar la carga de los demas modos.
- **SC-005**: El modo `vigilancia-tech` referencia el playbook `technology-watch` correctamente y su configuracion preserva compatibilidad con el 2.0.
- **SC-006**: `company_geo` con los 3 niveles (pais/departamento/municipio) se inyecta correctamente en el contexto del agente, verificable en el string de contexto generado.
- **SC-007**: Los modos marcados `status: roadmap` no aparecen en el listado de modos disponibles para el usuario.

## Constitution Check (Post-Design)

- **Status**: PASS
- **Constitucion evaluada**: v1.2.0 (`.specify/memory/constitution.md`)
- **Justification**:
  - **Pensar Antes de Codificar**: Phase 1 entera dedicada a validar precondiciones. 8 assumptions del spec declaradas. Dependencia de spec 009 explicita.
  - **Simplicidad Obligatoria**: ModeResolver es un dict lookup. Cero heuristicas, cero LLM classification, cero hot-reload, cero intensidad funcional. 5 archivos Python, cada uno con una responsabilidad clara y < 400 LOC.
  - **Modularidad Primero**: schema (modelos), loader (carga+validacion), registry (almacen), resolver (query), tool_filter (integracion) son 5 componentes separados con interfaces claras. SRP estricto.
  - **Cambios Quirurgicos y Trazables**: 2 archivos existentes modificados en modo aditivo (anadir wire a dependencies, anadir invocacion a app startup). Cero borrado, cero renombre, cero cambios al 2.0. El modulo `tooling` no se modifica (DIP).
  - **Entrega Verificable**: 7 SC del spec mapeados a fases con tests especificos. Phase 9 verifica todos los SC explicitamente.
  - **Diseno de Software**: SRP (5 archivos, 5 responsabilidades), SoC (schema vs carga vs resolucion vs filtrado vs almacen), DIP (ModeResolver depende de ModeRegistry abstraccion, no de ModeLoader; ModeToolFilter depende de API publica de ToolRegistry, no al reves), CQS (`get_active` query pura; `activate`/`change_mode` commands con retorno pragmatico documentado), OCP (nuevos modos = nuevos YAML sin tocar codigo), KISS (YAML plano, validacion directa), DRY (company_geo reutiliza company_profile de spec 009), LoD (ModeToolFilter no accede a internals del ToolRegistry, usa su API publica).
