# Feature Specification: Saneamiento Arquitectonico — Correccion de Deuda Tecnica Estructural

## Problem Statement

El analisis arquitectonico del codigo base revela violaciones significativas
de los principios SOLID y Hexagonal concentradas en ~8 archivos "hub", mas
problemas transversales de estado mutable y diseno defensivo. Los problemas
principales son:

- **SRP**: Controladores HTTP que orquestan pipelines completos de
  investigacion (research_approve.py, 421 LOC); metodo `BaseBranchAgent.run()`
  monolitico (~200 LOC) que mezcla sandbox, routing y NER;
  contract_loader.py con 683 LOC y matrices de configuracion embebidas;
  MCPProviderRegistry con 300+ LOC y 15 providers hardcodeados.
- **DIP**: Ciclos de dependencia prohibidos — infra/mcp importa
  `api.dependencies`; application importa `api.dependencies`
  (smart_router, event_log) via lazy imports.
- **ISP**: Solo 6 Protocolos en domain/repositories.py; faltan puertos para
  LLM, MCP, embeddings, vector index, event publisher.
  Application recibe tipos concretos de infra (MiniMaxClient,
  GeminiEmbeddingGateway) en lugar de interfaces.
- **OCP**: Matrices de gobernanza en codigo (contract_loader.py);
  MCPProviderRegistry con proveedores hardcodeados. Nueva rama/herramienta o
  proveedor MCP requiere editar clases monolíticas.
- **Estado mutable oculto**: `_sub_results` en BranchCoordinator acumula
  entre sesiones (memory leak); `_preload_context` en BaseBranchAgent no
  tiene reseteo; `_directive_queue` se crea lazy. Ningun componente es
  thread-safe ni reutilizable entre sesiones sin riesgos de contaminacion
  cruzada.
- **Falta de tipos**: Todas las respuestas MCP son `dict[str, Any]` con
  estructuras inconsistentes (unas con `{"success": True, "data": ...}`,
  otras con `{"error": ...}`).
  ToolSelector traga decisiones de cadena forzada sin logging.

Esto genera: incorporacion lenta de nuevos desarrolladores, conflictos de
merge frecuentes en los archivos hub, imposibilidad de sustituir proveedores
(LLM, MCP, embeddings) sin cambios en capas superiores, duplicacion de
logica (OrchestratorService.execute_research vs BranchCoordinator.execute),
y ruleta rusa al reutilizar componentes entre sesiones de investigacion.

**Hallazgos complementarios post-refactor** (identificados en auditoria
posterior, no cubiertos por Fases 0-3):

- **Duplicacion nominal**: Dos archivos `source_scorer.py` coexisten en
  `application/evaluation/` (clase `SourceScorer`, 89 LOC, scorer de confianza
  basado en reputacion aprendida de dominio) y `application/routing/`
  (clase `SourceScorerService`, 50 LOC, scorer transactiona que persiste
  confirmaciones/contradicciones). Comparten dominio conceptual pero tienen
  interfaces, mecanismos de persistencia y propositos distintos. Riesgo de
  confusion, duplicacion de logica futura, y mantenimiento divergente.
- **"Optional Everything" en OrchestratorService**: 4 de 7 parametros del
  constructor son `None` por defecto (`cross_session_service`, `trend_forecaster`,
  `source_scorer`, `report_generator`). Esto fuerza al llamador a conocer la
  semantica de cada `None` (ej. `preload_for_session()` retorna `{}` si
  `cross_session_service is None` — comportamiento inconsistente vs LSP).
  Ausencia de Null Object Pattern.
- **Modulo `application/evaluation/` infrautilizado**: Contiene `SourceScorer`
  (legacy), `BranchKPIService`, `GoldenCasesRunner`, `PromptRegressionService` —
  pero coexisten sin plan de migracion activo. `SourceScorer` es funcional
  pero no se invoca desde el pipeline principal; `GoldenCasesRunner` y
  `PromptRegressionService` existen pero no estan integrados en el flujo
  de approval/execution.
- **Composition root fragil**: `dependencies.py` cumple su rol de ensamblar
  dependencias (no viola DIP por definicion), pero al no usar contenedor DI ni
  factories, cualquier cambio en la firma de un constructor requiere editar
  este archivo manualmente — fuente comun de errores y conflictos de merge.

## Scope Boundaries

### In Scope

- **Fase 0 — Quick Wins**: Romper ciclos de dependencia (infra→api,
  application→api, infra→application). Inyectar dependencias por constructor.
  Eliminar codigo muerto (execute_research duplicado).
  Agregar logging en ToolSelector para decisiones de cadena forzada.
  Eliminar estado mutable oculto: _sub_results session-scoped,
  _preload_context con reseteo explicito, _directive_queue por sesion.
- **Fase 1 — Delgazar Controladores**: Extraer casos de uso de las rutas
  HTTP hacia Application/. Crear ApproveResearchUseCase,
  AdHocResearchToolsService, DocumentConversionService.
- **Fase 2 — Puertos de Dominio**: Anadir Protocols en domain/ para
  LLMClient, EmbeddingGateway, ToolExecutor, VectorIndex,
  GlobalKnowledgeStore, SourceTrustStore, EventPublisher.
  Externalizar matrices de contract_loader.py a YAML/JSON versionado.
  Mover MCPProviderRegistry a carga basada en manifiesto YAML/JSON.
  Crear dataclasses tipadas para respuestas MCP (adiós a dict[str, Any]).
- **Fase 3 — Pipeline de Agente**: Extraer pasos de BaseBranchAgent.run()
  en pipeline componible (ComposePromptStep, ToolLoopStep,
  AssembleBranchResultStep, SandboxExecutionStep). Extraer herramientas
  de sandbox a modulo separado. Dividir KnowledgeGraphService
  (GraphBuilder vs GraphAnalytics).
- Pruebas de contrato por capa (domain puro, application con fakes de
  puertos, API con TestClient + mocks de use cases).

### Out of Scope

- Nuevas funcionalidades o capacidades de investigacion.
- Cambios en la interfaz de usuario frontend.
- Migracion de base de datos o esquemas.
- Rendimiento o escalado horizontal (no functional).
- REFACTO de codigo que funcione correctamente y no este en los archivos
  identificados como problematicos.
- Sustitucion real de proveedores LLM/MCP (solo habilitar la
  intercambiabilidad via puertos).

## Assumptions

- Todo el comportamiento existente debe preservarse; no hay cambios
  funcionales durante el refactor.
- Los tests existentes en `tests/` con repositorios en memoria
  (conftest.py) son la red de seguridad para verificar regresiones.
- Cada fase produce artefactos deployables independientemente (no se
  requiere completar Fase 3 para liberar Fase 0).
- El proyecto se mantiene en la rama `main` segun la politica de
  CLAUDE.md; no se crean ramas de feature.
- La puntuacion objetivo post-refactor es 7.5-8/10 en la metrica
  utilizada en el analisis (desde 6.2/10 actual).

## User Scenarios & Testing

### Primary User Story

**Como** desarrollador del equipo de vigilancia,
**Quiero** que la arquitectura respete las fronteras de capa hexagonal
**Para** poder anadir una nueva rama de investigacion o intercambiar un
proveedor LLM sin modificar codigo en multiples capas.

### Acceptance Scenarios

1. **Given** un analisis de imports cruzados,
   **When** se ejecuta el script de verificacion de capas,
   **Then** no debe haber imports desde `infra` hacia `api` ni desde
   `application` hacia `api`.

2. **Given** un nuevo proveedor LLM,
   **When** se implementa un adapter que cumpla el Protocol LLMClient,
   **Then** debe poder inyectarse via dependencies.py sin cambiar
   ninguna linea en application/.

3. **Given** la ruta POST /research/approve,
   **When** se inspecciona su implementacion,
   **Then** debe delegar en un ApproveResearchUseCase y no contener
   logica de orquestacion, persistencia ni MCP.

4. **Given** BaseBranchAgent.run(),
   **When** se ejecuta una rama,
   **Then** debe ser un pipeline de pasos independientes y testeables
   por separado, no un metodo monolitico.

5. **Given** una nueva rama de investigacion (BranchType),
   **When** se anade su configuracion de herramientas,
   **Then** debe hacerse via un archivo YAML/JSON externo sin editar
   contract_loader.py.

6. **Given** un `BaseBranchAgent` que se reusa entre sesiones,
   **When** se inicia una nueva sesion de investigacion,
   **Then** no debe haber contaminacion de estado de la sesion anterior
   (_sub_results, _preload_context, _directive_queue deben estar limpios).

7. **Given** una llamada a una herramienta MCP,
   **When** se inspecciona la respuesta,
   **Then** debe tener un tipo dataclass con campos documentados
   en lugar de `dict[str, Any]` con estructura impredecible.

### Edge Cases

- Archivos que actualmente mezclan responsabilidades y son importados
  por multiples consumidores: la extraccion debe hacerse en pasos
  pequenos para no romper el grafo de dependencias durante la transicion.
- Los lazy imports (imports diferidos dentro de funciones) pueden
  ocultar ciclos reales; deben reemplazarse por inyeccion por
  constructor, no simplemente eliminarse.
- Al externalizar matrices a YAML/JSON, los valores por defecto en
  codigo deben mantenerse como fallback para no romper la carga.
- Estado mutable oculto: objetos como BranchCoordinator y BaseBranchAgent
  pueden ser singletons o instancias long-lived. Cualquier estado interno
  mutable (_sub_results, _preload_context, _directive_queue) debe ser
  session-scoped o reseteable explicitamente para evitar memory leaks y
  contaminacion entre sesiones.

## Functional Requirements

### Fase 0 — Quick Wins

- **FR-001**: Inyectar `MCPSmartCache` en `MCPExecutionClient.__init__`
  como parametro de constructor; eliminar import a
  `api.dependencies.mcp_cache` en execution_client.py.
- **FR-002**: Mover `cosine_similarity` a `domain/` o `shared/math_utils.py`;
  eliminar import infra→application en semantic_reranker.py.
- **FR-003**: Eliminar o redirigir `OrchestratorService.execute_research`;
  unificar toda ejecucion productiva en `BranchCoordinator.execute`.
- **FR-004**: Inyectar `SmartToolRouter` y `EventLog` (como interfaces)
  por constructor en `BaseBranchAgent` y `BranchCoordinator`; eliminar
  lazy imports desde `api.dependencies`.
- **FR-005**: Verificar que no existen imports prohibidos entre capas
  mediante script automatizado de validacion.
- **FR-017**: Agregar logging explicito en `ToolSelector` cuando se fuerza
  una cadena de herramientas (forced chain), documentando la decision
  (tool origen, tool destino, motivo).
- **FR-018**: Hacer `_sub_results` en `BranchCoordinator` session-scoped
  (usar dict keyed por session_id en lugar de lista plana). Anadir metodo
  `reset_session_state(session_id)` en `BaseBranchAgent` para limpiar
  `_preload_context` y `_directive_queue` al iniciar una nueva sesion.
  `_directive_queue` debe inicializarse siempre en el constructor, no
  lazy en el primer uso.

### Fase 1 — Controladores Delgados

- **FR-006**: Crear `ApproveResearchUseCase` en `application/orchestration/`
  que encapsule el contenido actual de `approve_plan` en research_approve.py.
- **FR-007**: La ruta `POST /research/approve` debe solo: validar request,
  llamar al use case, mapear DTO de respuesta.
- **FR-008**: Crear `AdHocResearchToolsService` en `application/research/`
  para busquedas MCP actualmente en research_outputs.py; rutas solo
  validan y delegan.
- **FR-009**: Extraer `DocumentConversionService` + puerto para
  Markitdown; upload.py deja de instanciar MarkitdownProvider directamente.

### Fase 2 — Puertos de Dominio

- **FR-010**: Anadir en `domain/` los siguientes Protocols:
  `LLMClient`, `EmbeddingGateway`, `ToolExecutor`, `VectorIndex`,
  `GlobalKnowledgeStore`, `SourceTrustStore`, `EventPublisher`.
- **FR-011**: Los adaptadores en `infra/` deben implementar estos
  Protocols; `dependencies.py` solo ensambla e inyecta.
- **FR-012**: Externalizar matrices de `contract_loader.py`
  (`load_skill_matrix`) a archivos YAML/JSON versionados en
  `config/skills/` o similar; cargar en startup.
- **FR-013**: Ningun constructor en `application/` debe recibir tipos
  concretos de `infra/`; solo Protocols de `domain/`.
- **FR-019**: Crear dataclasses tipadas para cada respuesta de herramienta
  MCP (NavigationResult, ScreenshotResult, SearchResult, etc.) en
  `domain/` o `application/`. Reemplazar todos los retornos `dict[str, Any]`
  en PlaywrightMCP, MCPExecutionClient y providers afines.
- **FR-020**: Migrar `MCPProviderRegistry` de providers hardcodeados a
  carga desde manifiesto YAML/JSON (`config/mcp-providers.yaml`). Mantener
  `ensure_standard_providers` como fallback para proveedores no declarados
  en el manifiesto.

### Fase 3 — Pipeline de Agente

- **FR-014**: Extraer de `BaseBranchAgent.run()` los pasos:
  `ComposePromptStep`, `ToolLoopStep`, `SandboxExecutionStep`,
  `AssembleBranchResultStep` como componentes independientes (patron
  pipeline o chain of responsibility).
- **FR-015**: Dividir `KnowledgeGraphService` en `GraphBuilder` y
  `GraphAnalytics` con responsabilidades separadas.
- **FR-016**: Cada paso del pipeline debe ser testeable de forma
  aislada con fakes de sus dependencias.
- **FR-022**: Extraer todas las funciones de ejecucion de herramientas
  sandbox (`execute_code`, `list_libraries`, `visualize`) de `base.py`
  a un modulo separado `application/agents/sandbox_tools.py` o similar.
  `BaseBranchAgent` debe delegar en el modulo externo en lugar de
  contener la logica directamente.

### Fase 4 — Hallazgos Residuales

- **FR-023**: Unificar los dos `source_scorer.py` en un unico modulo
  coherente. Evaluar si `SourceScorer` (evaluation/) y `SourceScorerService`
  (routing/) deben fusionarse en un solo servicio con dos modos de operacion
  (snapshot sync vs transactional async) o si representan conceptos distintos
  que deben renombrarse para eliminar la ambiguedad. En cualquier caso,
  eliminar la duplicacion nominal.
  - Opcion A: Fusionar en `application/evaluation/source_scorer.py` con
    dos estrategias intercambiables (estrategia snapshot y estrategia
    transaccional). `application/routing/source_scorer.py` queda deprecated
    y se elimina.
  - Opcion B: Renombrar `SourceScorerService` a `SourceConfirmationService`
    y mantener separados si el dominio lo justifica. Ningun archivo se
    depreca, pero ambos deben documentar su proposito y evitar duplicacion
    de logica a futuro.
  - Opcion C: Deprecar `SourceScorerService` (routing/) y migrar su logica
    transaccional al pipeline de evaluacion (spec 007).
    `SourceScorerService` y `routing/source_scorer.py` quedan deprecated
    con comentario `# DEPRECATED: migrar a evaluation/source_scorer.py (spec 007)`.
  **Codigo deprecated post-ejecucion**:
  - Si Opcion A: `src/vigilancia_multiagente/application/routing/source_scorer.py` entero.
  - Si Opcion C: misma ruta + clase `SourceScorerService`.
- **FR-024**: Introducir Null Object Pattern para las 4 dependencias
  opcionales de `OrchestratorService`. Crear `NullCrossSessionService`,
  `NullTrendForecaster`, `NullSourceScorer`, `NullReportGenerator` que
  implementen sus respectivos Protocols con comportamientos neutros
  (retornar valores vacios, no operar). Eliminar los `None` por defecto
  y los condicionales `if x is None` en los metodos.
  - `NullCrossSessionService.preload_session()` retorna `{}` explicitamente
    (sin condicional).
  - `NullTrendForecaster.forecast()` retorna lista vacia.
  - `NullSourceScorer.score()` retorna `None`.
  - `NullReportGenerator.generate()` retorna `None`.
  **Codigo deprecated post-ejecucion**:
  - El patrón de `dependencia_opcional=None` en constructores queda deprecated.
    Nuevos servicios deben usar Null Objects o requerir la dependencia como
    obligatoria. Las firmas viejas (`= None`) se eliminan; no se mantienen
    overloads para compatibilidad hacia atras (el composition root siempre
    provee todas las dependencias).
- **FR-025**: Establecer un plan de migracion para `application/evaluation/`.
  Determinar que componentes son legacy (eliminar), cuales estan activos
  (documentar), y cuales pertenecen al scope de spec 007 (migrar). Como
  minimo:
  - `SourceScorer` (evaluation/): evaluar si es reemplazado por spec 007.
    Si se decide Opcion A en FR-023, absorbe la logica de
    `SourceScorerService`. Caso contrario, queda como legacy.
  - `BranchKPIService` (20 LOC): documentar su rol actual y puntos de
    integracion. Evaluar si debe migrar a spec 007 o permanece.
  - `GoldenCasesRunner` (12 LOC): mover a spec 007 o tests/ si corresponde.
  - `PromptRegressionService` (18 LOC): mover a spec 007 o integrar en
    pipeline CI.
  - `ConfidenceCalibrator` (72 LOC): evaluar si es reemplazado por el
    nuevo sistema de evaluacion de spec 007.
  - `CausalTimeline` (101 LOC): documentar si tiene consumidores activos.
    Si no, marcar como candidate a legacy.
  - `ClaimPolarity` (37 LOC): documentar consumidores. Bajo consumo →
    candidate a legacy.
  - `ContradictionAnalyzer` (67 LOC): verificar si `EvidenceLinker` ya
    cubre esta funcionalidad. Si hay superposicion, deprecar.
  - `FindingImpactScorer` (84 LOC): activo (usado por `report_synthesizer`).
    Documentar y mantener.
  - `HypeDetector` (141 LOC): verificar consumidores. Si no tiene uso
    activo, candidate a legacy.
  - `ObsolescenceDetector` (45 LOC): verificar consumidores. Si no tiene
    uso activo, candidate a legacy.
  - `WeakSignalDetector` (163 LOC): verificar consumidores. Si no tiene
    uso activo, candidate a legacy.
  - `_markdown.py` (12 LOC): helper interno. Mantener si tiene
    consumidores dentro de evaluation/.
  **Codigo deprecated post-ejecucion**: Depende del plan de migracion.
    Cada archivo marcado como legacy recibe comentario
    `# DEPRECATED: [motivo] — migrar a spec 007 o eliminar` en su cabecera.
- **FR-026**: Reducir la fragilidad del composition root introduciendo
  metodos factory o funciones de creacion por dominio en `dependencies.py`.
  Cada dominio (governance, orchestration, agents, execution) debe tener
  su propia funcion `_build_*_services()` que agrupe la creacion de sus
  componentes. Esto no introduce un contenedor DI completo pero acota el
  alcance de los cambios: una modificacion en agentes solo toca
  `_build_agent_services()`.
  **Codigo deprecated post-ejecucion**: El codigo actual de
    `dependencies.py` (funcion unica, ~283 LOC, sin separacion por dominio)
    queda deprecated como "old composition root". Sin embargo, NO se elimina
    inmediatamente — la funcion principal `get_dependencies()` se mantiene
    como wrapper que llama a las factories en orden topologico, y se depreca
    con comentario `# DEPRECATED: refactorizar a factories individuales`
    cuando todas las rutas esten migradas a las nuevas factories.

## Key Entities

- **Capa Domain**: Nucleo inmutable sin dependencias externas; entidades
  de negocio, value objects, Protocols de puertos.
- **Capa Application**: Casos de uso, orquestacion, agentes, fusion,
  gobernanza; depende solo de domain/ via Protocols.
- **Capa Infra**: Adaptadores concretos (Postgres, MCP, LLM,
  embeddings); implementa Protocols definidos en domain/.
- **Capa API**: Adaptadores HTTP (FastAPI routes); delgados, solo
  validan request y delegan en application services.
- **Composition Root** (dependencies.py): Unico punto de ensamblaje de
  dependencias; no debe ser importado por application/ ni infra/.
- **Protocols de Puerto**: Interfaces en domain/ para LLM, MCP, vector,
  embeddings, eventos, almacenamiento.
- **Pipeline de Agente**: Secuencia de pasos componibles que reemplazan
  el metodo run() monolitico.
- **MCP Response Types**: Dataclasses tipadas (NavigationResult,
  ScreenshotResult, SearchResult, etc.) que reemplazan `dict[str, Any]`
  en todas las respuestas de herramientas MCP.

## Success Criteria

- **SC-001**: Zero imports desde `infra/` hacia `api/` o `application/`
  (verificable mediante script de validacion de capas).
- **SC-002**: Zero imports perezosos desde `application/` hacia
  `api.dependencies` (lazy imports reemplazados por inyeccion).
- **SC-003**: Todos los puntos de extension (LLM, MCP, embeddings,
  vector store, event bus) tienen un Protocol en `domain/` y al menos
  un adapter en `infra/` que lo implementa.
- **SC-004**: La ruta `POST /research/approve` tiene <= 50 LOC de
  logica de enrutamiento (sin contar imports y decoradores) y delega
  toda la orquestacion en `ApproveResearchUseCase`.
- **SC-005**: `BaseBranchAgent.run()` se compone de 3-5 pasos
  independientes, cada uno testeable con fakes y con <= 60 LOC.
- **SC-006**: Nueva rama de investigacion requiere: (a) crear
  `*_agent.py` como subclase de BaseBranchAgent, (b) agregar entrada
  YAML/JSON en config de herramientas, (c) registrar en DI — sin tocar
  `contract_loader.py`.
- **SC-007**: La puntuacion arquitectonica global del proyecto alcanza
  7.5/10 o superior segun la metrica establecida en el analisis.
- **SC-008**: Ningun test existente se rompe como consecuencia del
  refactor (verificable via `pytest` antes y despues de cada fase).
- **SC-009**: El tiempo estimado para que un nuevo desarrollador
  comprenda el flujo completo de aprobacion se reduce en al menos un
  40% (medible via revision del codigo: de 4 archivos / 3 capas a
  1 use case + 1 ruta delgada).
- **SC-010**: Cero estado mutable compartido entre sesiones:
  `_sub_results` debe ser session-scoped; `_preload_context` debe tener
  reset explicito via `reset_session_state()`; `_directive_queue` debe
  inicializarse en el constructor (no lazy). Verificable mediante
  inspeccion de codigo y tests de reutilizacion.
- **SC-011**: Todas las respuestas de herramientas MCP tienen un tipo
  dataclass especifico (no `dict[str, Any]`) con campos documentados.
  Verificable mediante analisis de tipos estatico (basedpyright) y
  ausencia de `dict[str, Any]` como retorno en modulos MCP.

### Fase 4 — Success Criteria

- **SC-012**: Solo existe un archivo `source_scorer.py` en el proyecto,
  con nombre y responsabilidad inequivoca. Verificable via `Get-ChildItem`
  o `find` — cero falsos positivos.
- **SC-013**: `OrchestratorService` tiene cero parametros `None` en su
  constructor. Todas las dependencias opcionales tienen Null Object
  implementations. Verificable mediante inspeccion de codigo (buscar
  `= None` en `__init__`).
- **SC-014**: Cada componente de `application/evaluation/` tiene un
  destino documentado: legacy (eliminar), activo (testeado e integrado),
  o migrado a spec 007. Verificable via comentario en cada archivo y
  entrada en el plan de migracion.
- **SC-015**: `dependencies.py` esta organizado en funciones factory
  por dominio (< 50 LOC cada una). Verificable mediante inspeccion de
  codigo.

## Delivery Constraints

- Cada fase debe completarse de forma independiente y verificable antes
  de pasar a la siguiente (Simplicidad Obligatoria, Entrega Verificable).
- No se permite introducir nuevas funcionalidades ni cambiar firmas de
  APIs publicas durante el refactor (Cambios Quirurgicos y Trazables).
- Los cambios deben ser pequenos y frecuentes; cada commit debe trazar
  directamente al objetivo de la fase (Pensar Antes de Codificar).
- Se debe mantener la modularidad existente; la extraccion de
  responsabilidades debe mejorar la cohesion sin aumentar el
  acoplamiento innecesariamente (Modularidad Primero, Principios de
  Diseno de Software).
- Todo nuevo puerto (Protocol) debe seguir ISP: interfaces especificas,
  no interfaces "gordas".
