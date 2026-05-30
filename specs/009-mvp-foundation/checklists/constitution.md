# Constitution Alignment Checklist: Vigilador 3.0 MVP Foundation

**Purpose**: Validar la *calidad de los requisitos* expresados en `plan.md` y `tasks.md` de `009-mvp-foundation` frente a la Constitución del Proyecto v1.2.0. Cada ítem evalúa si los documentos están escritos de forma completa, clara, consistente, medible y trazable respecto a cada principio constitucional. NO valida la implementación ni el comportamiento del código.
**Created**: 2026-05-28
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)
**Reference**: `.specify/memory/constitution.md` (v1.2.0)

<!-- "Unit tests for English": cada ítem testea si el requisito está bien escrito, no si el sistema funciona. -->

## Principio 1 — Pensar Antes de Codificar

- [x] CHK001 - ¿El plan declara los supuestos de diseño explícitamente antes de toda tarea de implementación? [Completeness, Constitución §1, Spec §Assumptions A-01..A-10] — **PASA**: spec lista A-01..A-10 (10 assumptions). Plan §Constitution Check Pre-Design las invoca y F0 (T001–T004) valida entorno antes de F1.
- [x] CHK002 - Cuando un requisito admite múltiples interpretaciones (p. ej. ubicación de `company_geo`: `config/company/identity.md` vs tabla `company_profile`), ¿el plan presenta las opciones en vez de elegir una silenciosamente? [Clarity, Spec §Key Entities, Plan §Files to Create] — **PASA**: el spec plantea ambas opciones ("decisión técnica en /speckit-plan"); el plan resolvió a favor de la tabla `company_profile` (Plan L85, L86, L211) descartando `identity.md`. Decisión trazada, no silenciosa.
- [x] CHK003 - ¿Se documenta si existe un enfoque más simple descartado y la razón del descarte (p. ej. crear `subagents`/`pending_approvals` vacías ahora vs diferirlas)? [Gap, Plan §External Constraints, Constitución §1, §2] — **PASA**: Plan §External Constraints y §Constitution Check justifican crear las tablas vacías ("las exige multi-tenancy desde día 1") y diferir `agent_modifications` a F5b.
- [x] CHK004 - ¿Las tareas que dependen de validación de entorno (T001–T004) están formuladas como gate go/no-go antes de escribir código, en lugar de asumir el entorno disponible? [Coverage, Tasks Phase 1] — **PASA**: Tasks §Implementation Strategy #1 declara Phase 1 como "go/no-go al spec 009 completo"; Phase 1 es "cero código de producto".
- [x] CHK005 - ¿El plan nombra explícitamente las confusiones residuales que requieren aclaración (p. ej. si `alembic.ini` ya existe en el repo) en vez de asumir un estado? [Ambiguity, Plan §Files to Create "alembic.ini o ajuste a config existente"] — **PASA** (resuelto 2026-05-28): Plan §Phase 1 paso 1 ahora exige detectar `alembic.ini`/`alembic/versions/` y registrar el estado (presente/ausente/parcial) en `docs/postgres-readiness.md` antes de que T009 decida `alembic init` vs ajuste aditivo. La validación en F0 cierra el hallazgo.

## Principio 2 — Simplicidad Obligatoria

- [x] CHK006 - ¿Cada tarea traza a un problema concreto del spec sin introducir capas, banderas o abstracciones no solicitadas? [Completeness, Constitución §2, Tasks T001–T066] — **PASA**: cada T0NN apunta a un archivo/FR concreto; Tasks §Implementation Strategy #6 declara "MVP scope ESTRICTO". Sin abstracciones especulativas detectadas.
- [x] CHK007 - ¿El plan justifica por qué las tablas `subagents` y `pending_approvals` creadas vacías NO son sobreingeniería sino mínima migración necesaria? [Clarity, Plan §Constitution Check, §External Constraints] — **PASA**: Plan §Constitution Check Pre-Design lo argumenta explícitamente ("no son sobreingeniería, son la mínima migración necesaria" por multi-tenancy schema día 1).
- [~] CHK008 - ¿Las 16 variables de entorno nuevas están justificadas por valor directo, o alguna es "configurabilidad" especulativa no pedida por el spec? [Consistency, Plan §Variables de entorno, Constitución §2] — **PARCIAL / HALLAZGO**: la matriz de 16 vars está documentada con defaults, pero varias no nacen de ningún FR del spec: `VT_OTEL_EXPORTER_ENDPOINT` (FR-031 dice "sin exportador remoto obligatorio"), los 4 parámetros de circuit breaker como vars de entorno, y `VT_PROMETHEUS_METRICS_PATH`. Riesgo de "configurabilidad no pedida" contra §2. Revisar si reducir a defaults en código.
- [x] CHK009 - ¿Se especifica un límite de tamaño por archivo (≤ 400 LOC) y se evita exceder complejidad innecesaria en `tool_registry.py` (~350) y `health_monitor.py` (~300)? [Measurability, Spec §FR-034, Plan §Phases] — **PASA**: FR-034 fija ≤ 400 LOC; Plan §Phases asigna presupuestos (~250/~350/~300/~250 LOC) por archivo. Medible.
- [x] CHK010 - ¿El requisito de tool-gating (FR-015) evita manejar escenarios imposibles, limitándose a los 3 casos reales (sin API key, DOWN, exclusión por caller)? [Coverage, Spec §FR-015, §SC-010] — **PASA**: FR-015 y SC-010 enumeran exactamente 3 casos reales; el placeholder de Mode-filter está acotado a spec 012. Sin escenarios imposibles.

## Principio 3 — Modularidad Primero

- [x] CHK011 - ¿Cada archivo nuevo del listado del plan tiene una responsabilidad única declarada (un concern por archivo)? [Completeness, Plan §Files to Create, Constitución §3] — **PASA**: la tabla §New Files asigna un "Purpose" único por archivo; Plan §Constitution Check Post-Design afirma "cada uno con un concern".
- [x] CHK012 - ¿El plan define interfaces de entrada/salida claras para `ToolWrapper`, `ToolRegistry`, `HealthMonitor` y `OAuthManager`? [Clarity, Spec §FR-011..FR-019, Plan §Technical Context] — **PASA**: FR-011 define la firma de `ToolWrapper`; Plan §Phases lista métodos concretos por clase (register/list/discover/get_*, store/get/refresh_if_needed, start/_tick).
- [x] CHK013 - ¿Los requisitos garantizan que ningún módulo nuevo mezcla orquestación, lógica de dominio y acceso a infraestructura (p. ej. routers vs repositorios vs registry)? [Consistency, Plan §Files to Create, Constitución §3] — **PASA**: routers en `api/routes/`, repos en `infra/persistence/`, registry/monitor en `enterprise/`; FR-033 + T004/T055 lo validan con `check-layer-imports.py`.
- [x] CHK014 - ¿La separación `ToolRegistry` (solo lee) vs `HealthMonitor` (escribe) está especificada como invariante explícita y no como nota incidental? [Clarity, Spec §FR-014, §FR-017, Plan §Technical Context] — **PASA**: FR-014 ("query pura, solo lee"), FR-017 (monitor escribe), reforzado en Plan §Technical Context ("CQS: solo LEE") y T017 ("upsert para uso EXCLUSIVO de HealthMonitor"). Invariante explícita.

## Principio 4 — Manejo de Errores Estricto

- [x] CHK015 - ¿Los requisitos de manejo de errores son explícitos y prohíben try/except defensivos (p. ej. FR-010 para `XiaomimimoClient`)? [Completeness, Spec §FR-010, Plan §External Constraints] — **PASA**: FR-010 ("sin try/except defensivos que oculten causas"); Spec §Delivery Constraints #4 y Plan §External Constraints lo reiteran ("cero try/except defensivos").
- [x] CHK016 - ¿Se especifica que los errores HTTP propagan con código + cuerpo de respuesta sin captura amplia que oculte causas? [Clarity, Spec §FR-010, Tasks T021–T022] — **PASA**: FR-010 ("propagar errores HTTP con su código y cuerpo"); T021 incluye tests de 401/429 que "propaga sin try/except"; T022 ("HTTPError propaga con status + body").
- [x] CHK017 - ¿El plan acota el circuit breaker del `HealthMonitor` como única excepción de boundary, en vez de validación defensiva difusa? [Coverage, Plan §External Constraints "Circuit breakers solo en boundaries", Spec §FR-018] — **PASA**: Spec §Delivery Constraints #4 ("Circuit breakers solo en boundaries (HealthMonitor)") y FR-018 lo acotan a un único boundary.
- [x] CHK018 - ¿Los Edge Cases (EC-01..EC-07) especifican mensajes/estados accionables en lugar de silenciar el fallo? [Measurability, Spec §Edge Cases] — **PASA**: cada EC define estado/mensaje accionable (EC-01 "mensaje claro 401/403 + enlace", EC-02 "falla atómicamente, log indica paso", EC-03 "credentials_unavailable", EC-05 "last_error=timeout"). Ninguno silencia.

## Principio 5 — Cambios Quirúrgicos y Trazables

- [x] CHK019 - ¿Cada archivo modificado del 2.0 está listado con el cambio exacto y justificación de que es aditivo (no destructivo)? [Traceability, Plan §Modified Files, §Código deprecated] — **PASA**: §Modified Files lista 8 archivos con su cambio (todos aditivos: "Registrar routers", "añadir wires/secciones/deps", "Cero cambios a..."); §Constitution Check Post-Design lo cuantifica ("7 archivos del 2.0 modificados, todos aditivos").
- [x] CHK020 - ¿El plan declara explícitamente "cero edits" a los componentes deprecated soft (MiniMaxClient, agentes 2.0, endpoints `/api/v2/research/*`)? [Completeness, Plan §Código deprecated] — **PASA**: la tabla §Código deprecated marca "Cero edits" en cada fila (MiniMaxClient, 6 agentes, BranchCoordinator, endpoints research, gemini_gateway, etc.).
- [x] CHK021 - ¿Los requisitos exigen preservar convenciones existentes del repositorio (patrón Repository, prefix `VT_`, estructura de routers)? [Consistency, Plan §Patrones del 2.0 reusados] — **PASA**: §Patrones del 2.0 reusados mapea cada componente nuevo al patrón existente (Repository async, BaseSettings `VT_`, routers FastAPI, fakes de conftest, stack React).
- [x] CHK022 - ¿Se especifica que solo se elimina código huérfano generado por este cambio y no código muerto previo del 2.0? [Clarity, Constitución §5, Plan §Código deprecated "NO elimina nada"] — **PASA**: §Código deprecated ("Este spec NO elimina nada del 2.0", "NO existe deprecated hard") y la nota anti-borrado para `/speckit-implement`.
- [x] CHK023 - ¿Existe trazabilidad fuente→decisión→resultado que conecte cada decisión C0/C1 del canon con su FR/tarea? [Traceability, Spec §Delivery Constraints, Plan §Technical Context] — **PASA**: Spec §Delivery Constraints cita C0 #4/#6/#10 y C1.1/C1.6 con su impacto; Plan §Technical Context y §Tareas que materializan los bloques los conectan a T-IDs.

## Principio 6 — Entrega Verificable

- [x] CHK024 - ¿Cada FR del spec mapea a uno o más acceptance scenarios y success criteria verificables? [Acceptance Criteria, Spec §FR-001..FR-034, §Acceptance Scenarios, §Success Criteria] — **PASA** (resuelto 2026-05-28): el spec ahora incluye §Traceability Matrix mapeando los 34 FR → acceptance scenario + success criterion + fase del plan (34/34). Los FR sin AS/SC directo (FR-008, FR-019, FR-024, FR-030, FR-031) quedan explícitamente marcados como validados por tests unitarios de su fase.
- [x] CHK025 - ¿Las tareas de test están formuladas test-before-implementation por componente (T021→T022, T024→T025, etc.) y no como "hacer que funcione"? [Measurability, Tasks §Dependencies] — **PASA**: Tasks §Dependencies declara "Tests-before-implementation por componente" con cadenas explícitas (T021→T022→T023, etc.); cada test enumera N casos concretos.
- [x] CHK026 - ¿Los success criteria son cuantificables (≤ 5 min, ≤ 200 ms, ≤ 90 s, 5 reversiones) y no ambiguos ("parece funcionar")? [Clarity, Spec §SC-001..SC-010, Plan §Success Criteria] — **PASA**: todos los SC tienen umbral numérico o condición binaria verificable (≤ 5 min, 100%, 5 reversiones, ≤ 200 ms, ≤ 90 s, ≤ 3 s, 0 stubs, 3 escenarios gating).
- [x] CHK027 - ¿El plan declara verificación por paso/fase (cada fase produce un artefacto verificable antes de avanzar)? [Coverage, Plan §Rollout Strategy, §Phases, Tasks §Implementation Strategy] — **PASA**: §Rollout Strategy ("cada fase produce un artefacto verificable y los tests deben pasar antes de moverse"); cada Phase del plan tiene bloque "Output"; cada Phase de tasks tiene "Independent Test Criteria".
- [x] CHK028 - ¿Hay correspondencia 1:1 entre los SC del spec (SC-001..SC-010) y los del plan (SC-001..SC-011), o el SC-011 extra está justificado? [Consistency, Spec §Success Criteria vs Plan §Success Criteria] — **PASA** (resuelto 2026-05-28): SC-011 (`check-layer-imports.py` sin nuevas violaciones, anclado a FR-033) añadido al spec. Ambos documentos listan ahora SC-001..SC-011 (11 SC). Correspondencia 1:1 restaurada.

## Principios de Diseño — Limpieza y Simplicidad (DRY/KISS/YAGNI/WET/AHA)

- [x] CHK029 - ¿El plan evita duplicar lógica reusando `GeminiEmbeddingGateway` del 2.0 en vez de crear embeddings nuevos (DRY)? [Consistency, Plan §Technical Context, §Constitution Check] — **PASA**: §Technical Context ("Reusar GeminiEmbeddingGateway existente. Sin nuevos providers"); §Constitution Check lista DRY explícitamente; A-03 lo asume.
- [x] CHK030 - ¿Se documenta YAGNI explícitamente al diferir TurboVecIndex, modos, playbooks y Dreaming a specs posteriores? [Completeness, Spec §Out of Scope, Plan §External Constraints] — **PASA**: Spec §Out of Scope difiere ~14 capacidades a specs 010–013/roadmap; Plan §External Constraints C0 #4 ("se documenta pero NO se implementa").
- [x] CHK031 - ¿El plan evita abstracciones prematuras en `ToolWrapper`/`ToolRegistry`, sin "flexibilidad" que el MVP no usa (AHA)? [Clarity, Spec §FR-011..FR-016, Constitución §Diseño] — **PASA**: el filtro por Mode es placeholder acotado (FR-015, diferido a 012); §Constitution Check declara KISS ("cero cosas no listadas en el spec"). Nota: ver CHK008 — las vars de entorno opcionales son el único punto de posible exceso.

## Principios de Diseño — Cohesión y Conexión (LoD/Acoplamiento/Cohesión/SoC)

- [x] CHK032 - ¿Los requisitos persiguen bajo acoplamiento al desacoplar `XiaomimimoClient` del SDK OpenAI concreto (C0 #6)? [Completeness, Spec §Delivery Constraints C0 #6, Plan §Technical Context] — **PASA**: Spec C0 #6 ("el resto del runtime nunca importa openai directamente"); FR-006/T022 ("retorna tipos propios, NO exponer tipos del SDK"); Plan §Technical Context lo reitera.
- [x] CHK033 - ¿La separación de intereses entre capas (API → enterprise → infra) está definida y verificada por `check-layer-imports.py`? [Clarity, Spec §FR-033, Tasks T004, T055] — **PASA**: FR-033 exige respetar capas verificadas por el script; T004 (baseline) + T055 (final, "0 violaciones nuevas") lo verifican; SC-011 del plan lo formaliza.
- [x] CHK034 - ¿Las tareas mantienen alta cohesión agrupando por concern (F1.1 LLM, F1.2 Registry, F1.3 Health, F1.4 Auth) sin mezclar responsabilidades? [Consistency, Tasks §Phase 3 F1.x] — **PASA**: Phase 3 se subdivide en F1.1–F1.7 por concern; §Dependencies declara que F1.1–F1.5 "son independientes entre sí". Alta cohesión por bloque.

## Principios de Diseño — SOLID

- [x] CHK035 - ¿Cada componente nuevo tiene una única razón para cambiar (SRP) declarada en el Constitution Check del plan? [Completeness, Plan §Constitution Check Pre/Post-Design] — **PASA**: §Constitution Check Pre y Post-Design declaran SRP ("cada archivo nuevo un concern") explícitamente.
- [x] CHK036 - ¿El plan especifica extensión sin modificación (OCP) al registrar routers enterprise en `app.py` de forma aditiva? [Clarity, Spec §FR-032, Plan §Modified Files] — **PASA**: §Constitution Check ("OCP: router enterprise extiende app.py sin tocarlo"); §Modified Files ("Registrar nuevos routers... Cero cambios a routers existentes"); FR-032 (cero breaking changes).
- [x] CHK037 - ¿Se aplica DIP vía Repository pattern con ports para `tool_health`, `oauth_credentials`, `company_profile`? [Consistency, Plan §Constitution Check, Tasks T017–T019] — **PASA**: §Constitution Check ("DIP: Repository pattern para las 3 tablas"); T017–T019 crean los 3 repos como port+adapter async.
- [x] CHK038 - ¿Las interfaces (`ToolWrapper`, niveles de detalle `ToolCard`/`ToolSummary`/`ToolDocs`) son específicas y los clientes no dependen de métodos que no usan (ISP)? [Coverage, Spec §FR-011..FR-012, Tasks T015–T016] — **PASA**: FR-012 define 3 niveles de detalle con granularidad creciente; T016 los modela como dataclasses separadas (card→summary→docs), permitiendo a los callers pedir solo el nivel que usan.

## Principios de Diseño — Desarrollo y Arquitectura (CQS/CQRS/POLA/Convención)

- [x] CHK039 - ¿La separación comando/consulta (CQS) entre `ToolRegistry` (query) y `HealthMonitor` (command) está especificada sin ambigüedad? [Clarity, Spec §FR-014, Plan §Technical Context "CQS"] — **PASA**: ya verificado en CHK014; FR-014 + Plan §Technical Context "CQS" + T017 nombran la frontera command/query explícitamente.
- [x] CHK040 - ¿El comportamiento de defaults (Xiaomimimo default, onboarding retomable) sigue el principio de menor sorpresa (POLA) sin resultados inesperados? [Coverage, Spec §FR-029 EC-06, Plan §Reformulación de defaults] — **PASA**: FR-029 + EC-06 definen retomar onboarding parcial (comportamiento esperable); §Reformulación de defaults documenta el cambio MiniMax→Xiaomimimo con motivo, evitando sorpresa.
- [~] CHK041 - ¿El plan prefiere convención sobre configuración con defaults sensatos (16 vars con default, solo `VT_XIAOMIMIMO_API_KEY` requiere acción del usuario)? [Consistency, Plan §Variables de entorno "matriz completa"] — **PARCIAL**: la matriz declara que solo `VT_XIAOMIMIMO_API_KEY` requiere acción y las demás tienen default sensato (cumple convención sobre configuración). Tensión con CHK008: tener defaults no justifica exponer 16 vars si varias no se consumen por ningún FR. Convención OK; cantidad de superficie configurable a revisar.

## Estándares de Ingeniería y Proceso

- [x] CHK042 - ¿Cada dependencia PyPI nueva está justificada por valor directo y auditada por licencia (MIT/Apache/BSD)? [Completeness, Plan §Código copiado/reusado, Spec §FR-002, Tasks T008] — **PASA**: §Librerías PyPI nuevas tabula las 6 deps con versión, licencia, uso concreto y atribución; FR-002 + T008 exigen registrarlas en `audit-licenses.md`; política whitelist MIT/Apache/BSD declarada.
- [x] CHK043 - ¿El requisito de comentarios/atribución (header Hermes) se limita a lo no obvio y obligatorio por licencia, sin obviedades? [Consistency, Spec §Delivery Constraints "Atribución obligatoria", Estándares §6] — **PASA**: el header Hermes es atribución obligatoria por licencia (no comentario decorativo) y se aplica solo a archivos copiados (spec 011, no 009). Consistente con Estándares §6.
- [x] CHK044 - ¿El proceso definido declara alcance y criterios verificables antes de codificar, con cambio mínimo suficiente por fase? [Coverage, Tasks §Implementation Strategy, Plan §Phases] — **PASA**: §Implementation Strategy ordena Setup→Foundational→US1→Polish con gate por fase; cada Phase declara Output/Independent Test Criteria antes de avanzar.
- [x] CHK045 - ¿La regla anti-stubs (cero `pass`/`...`/`TODO` en `enterprise/`) está especificada como criterio verificable con método de verificación (T062)? [Measurability, Spec §SC-009, §A-09, Tasks T062] — **PASA**: SC-009 + A-09 fijan la regla; T062 da el método exacto (`grep -rE "^\s*(pass|\.\.\.|TODO)\s*$"` → 0 matches salvo `__init__.py`). Medible.

## Trazabilidad y Gobernanza

- [x] CHK046 - ¿Existe un esquema de IDs (FR-NNN, SC-NNN, EC-NN, T0NN, US1) que conecta cada tarea con su requisito y criterio de aceptación? [Traceability, Spec §Functional Requirements, Tasks §Format Validation] — **PASA** (resuelto 2026-05-28): el esquema de IDs ya existía; ahora la §Traceability Matrix del spec añade el mapeo explícito FR → AS + SC + fase del plan, cerrando la trazabilidad inversa que faltaba. El vínculo FR→fase permite ubicar las tareas que materializan cada FR.
- [x] CHK047 - ¿El plan incluye el Constitution Check (Pre-Design y Post-Design) como gate explícito del ciclo de planificación? [Gap, Plan §Constitution Check, Gobernanza] — **PASA**: el plan tiene dos secciones Constitution Check (Pre-Design "Gate result: PASS" y Post-Design "Status: PASS") con justificación por principio. Cumple Gobernanza ("revisión de cumplimiento en cada ciclo").
- [x] CHK048 - ¿Los requisitos hacen referencia a la versión correcta de la constitución (v1.2.0) de forma consistente en spec y plan? [Consistency, Spec §Delivery Constraints, Plan §Constitution Check] — **PASA** (resuelto 2026-05-28): ambos Constitution Check del plan (Pre-Design y Post-Design) ahora declaran "Constitución evaluada: v1.2.0 (`.specify/memory/constitution.md`)", alineándose con las 4 citas del spec. Versión anclada en ambos documentos.
- [x] CHK049 - ¿Las dependencias entre specs descendientes (010–013) están documentadas para mantener trazabilidad de alcance MVP? [Coverage, Spec §Specs descendientes, Plan §Approach] — **PASA**: Spec §Specs descendientes mapea qué necesita cada spec 010–013 de este; §Dependencies on previous specs cubre 002–008. Cadena de alcance trazada.

## Notes

- Leyenda: `[x]` PASA · `[~]` PARCIAL/HALLAZGO. Foco: **calidad de los requisitos** en `plan.md` y `tasks.md`, NO la implementación.

### Resultado de la verificación (2026-05-28)

- **Total**: 49 ítems · **Resultado original**: PASA 43 · PARCIAL/HALLAZGO 6 · FALLA 0.
- **Resultado tras arreglos (2026-05-28)**: **PASA 48 · PARCIAL/HALLAZGO 1 · FALLA 0.**
- **Veredicto global**: el plan y las tasks están **alineados con la Constitución v1.2.0**. Los 6 principios fundamentales, los principios de diseño (SOLID, DRY/KISS/YAGNI, cohesión/SoC, CQS/POLA) y los estándares de ingeniería se cumplen.

### Hallazgos resueltos (2026-05-28)

1. **CHK028 / CHK046 / CHK048 — Inconsistencia spec↔plan** → RESUELTO: SC-011 añadido al spec (ambos docs con 11 SC); "Constitución evaluada: v1.2.0" añadida a los dos Constitution Check del plan.
2. **CHK024 / CHK044 — Falta matriz de trazabilidad** → RESUELTO: añadida §Traceability Matrix al spec mapeando los 34 FR → AS + SC + fase del plan (34/34).
3. **CHK005 — Estado de `alembic.ini` no validado en F0** → RESUELTO: Plan §Phase 1 paso 1 valida `alembic.ini`/`alembic/versions/` antes de T009 y lo registra en `docs/postgres-readiness.md`.

### Hallazgo remanente (informativo, no bloqueante)

1. **CHK008 / CHK041 — Superficie de configuración (Constitución §2)**:
   - 16 vars de entorno nuevas; varias no se consumen por ningún FR (`VT_OTEL_EXPORTER_ENDPOINT` vs FR-031 "sin exportador obligatorio", 4 vars de circuit breaker, `VT_PROMETHEUS_METRICS_PATH`).
   - No es violación constitucional: el plan justifica cada var con su matriz tipo/default/validación y todas tienen default sensato (convención sobre configuración). Se deja como observación por si se decide reducir la superficie configurable del MVP a defaults en código.

### Notas positivas

- **CHK002 resuelto**: la decisión de ubicación de `company_geo` (tabla `company_profile`, no `identity.md`) está tomada y trazada en el plan — no es ambigüedad pendiente.
- Manejo de errores (P4), cambios quirúrgicos (P5) y la sección §Código deprecated son ejemplares: cero `try/except` defensivos, "cero edits" explícito al 2.0, nota anti-borrado para `/speckit-implement`.
