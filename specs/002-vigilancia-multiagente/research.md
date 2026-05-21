# Phase 0 Research: Vigilancia Tecnologica Multiagente

## Decision 1: Orquestacion central con ramas paralelas especializadas

- **Decision**: Usar un orquestador de sesion que crea un plan por ramas y ejecuta ramas en paralelo con consolidacion al final.
- **Rationale**: El objetivo del producto exige analisis simultaneo (comercial, normativo, innovacion, riesgo, competitivo) y una salida unificada.
- **Alternatives considered**:
  - Ejecucion secuencial por ramas (descartada por latencia y menor cobertura temprana).
  - Orquestacion totalmente automatica sin gate humano (descartada por riesgo de desalineacion con objetivos de negocio).

## Decision 2: MiniMax M2.7 como modelo orquestador unico

- **Decision**: Centralizar clarificacion, planificacion, analisis de rama y sintesis en MiniMax M2.7.
- **Rationale**: Reduce complejidad operativa y favorece consistencia de criterio entre etapas.
- **Alternatives considered**:
  - Multiples modelos por etapa (descartado por mayor complejidad y costo operativo).
  - Modelo no agentico + reglas rigidas (descartado por menor adaptabilidad en investigaciones complejas).

## Decision 3: Tool use con preservacion completa de historial

- **Decision**: En cada iteracion de tool use, conservar respuesta completa del modelo y resultados de herramienta.
- **Rationale**: La continuidad del razonamiento y calidad de decisiones depende del contexto completo de llamadas previas.
- **Alternatives considered**:
  - Persistir solo respuesta textual final (descartado por perdida de contexto de tool-calls).
  - Limpiar historial agresivamente (descartado por degradacion de calidad en tareas largas).

## Decision 4: Embeddings con gemini-embedding-2 a 768 dimensiones

- **Decision**: Usar `gemini-embedding-2` para indexacion semantica de hallazgos, conceptos y fuentes; normalizar a 768 dimensiones.
- **Rationale**: Mantiene calidad semantica con costo y almacenamiento controlados para grafo y retrieval.
- **Alternatives considered**:
  - 3072 dimensiones (descartado por mayor costo/huella sin beneficio proporcional para este caso).
  - Embeddings 001 legacy (descartado por menor alineacion futura multimodal).

## Decision 5: Formato de embeddings por tarea

- **Decision**: Aplicar prefijos de tarea consistentes (query/document) para retrieval asimetrico.
- **Rationale**: Mejora precision de recuperacion al alinear intencion de consulta con indexacion documental.
- **Alternatives considered**:
  - Embedding sin prefijos de tarea (descartado por menor relevancia de ranking).

## Decision 6: Contrato de API y streaming por eventos tipados

- **Decision**: Mantener endpoints de sesion/reporte/grafo y stream de eventos con payload minimo consistente por etapa.
- **Rationale**: Soporta UX observable en tiempo real y simplifica acoplamiento con frontend.
- **Alternatives considered**:
  - Polling de estado sin SSE/eventos (descartado por peor experiencia y mayor latencia percibida).

## Decision 7: Deteccion explicita de contradicciones y cobertura incompleta

- **Decision**: Tratar contradicciones inter-rama y vacios de evidencia como salidas de primer nivel en el reporte.
- **Rationale**: Mejora confiabilidad y evita conclusiones optimistas sin respaldo.
- **Alternatives considered**:
  - Silenciar conflictos en resumen ejecutivo (descartado por riesgo de decisiones incorrectas).

## Decision 8: Human-in-the-loop obligatorio antes de ejecutar

- **Decision**: Exigir aprobacion del plan antes de ejecucion de ramas.
- **Rationale**: Mantiene control estrategico del usuario y alineacion con objetivos de negocio.
- **Alternatives considered**:
  - Auto-run por defecto (descartado por riesgo de costos y trabajo fuera de alcance).

## Decision 9: Compatibilidad MCP basada en protocolo (independiente del lenguaje)

- **Decision**: Tratar cada servidor MCP como integracion por contrato de protocolo y no por stack interno.
- **Rationale**: La compatibilidad depende de transporte y schema MCP, no de si el servidor esta en Python, Node o cualquier otro lenguaje.
- **Alternatives considered**:
  - Estandarizar todos los MCP en un solo lenguaje (descartado por sobrecosto y menor reutilizacion de ecosistema).

## Decision 10: Estrategia de transporte MCP hibrida

- **Decision**: Usar HTTP/Streamable HTTP para proveedores remotos (Tavily, Exa, Jina) y STDIO para servidores locales.
- **Rationale**: Mantiene interoperabilidad de protocolo y reduce friccion operativa en distintos clientes.
- **Alternatives considered**:
  - Solo HTTP remoto (descartado por acoplamiento alto a infraestructura externa).
  - Solo STDIO local (descartado por peor experiencia con proveedores hospedados).

## Decision 11: Politica de seguridad para MCP de web y papers

- **Decision**: Aplicar controles de seguridad para prompt injection y acceso a endpoints internos al usar herramientas de extraccion/fetching.
- **Rationale**: Hay riesgo documentado de prompt injection en contenido externo (papers/web) y riesgo de alcance de red interna en fetchers.
- **Alternatives considered**:
  - Confiar en contenido externo sin validaciones (descartado por riesgo operacional y de seguridad).

## Decision 12: Gestion de secretos y telemetria de proveedor

- **Decision**: Prohibir API keys hardcodeadas, usar solo entorno seguro y registrar telemetria por proveedor (latencia, error-rate, retries).
- **Rationale**: Evita exposicion de credenciales y habilita control operativo basado en señales reales.
- **Alternatives considered**:
  - Mantener llaves en scripts o ejemplos productivos (descartado por incumplir seguridad basica).
  - Sin metricas por proveedor (descartado por baja trazabilidad operativa).

## Decision 13: Anti-bias temporal dinamico

- **Decision**: Calcular automaticamente ventana temporal en cada sesion (anio actual, recencia por dominio y corte configurable).
- **Rationale**: Evita sesgo por periodos hardcodeados y mantiene vigencia de resultados.
- **Alternatives considered**:
  - Rangos fijos por anio (descartado por obsolescencia y drift de contexto).

## Decision 14: Follow-up query loop con limite de profundidad

- **Decision**: Cada rama ejecuta queries iniciales y follow-ups con `depth_limit` y criterio de parada por saturacion de evidencia.
- **Rationale**: Permite investigacion profunda controlando costo/latencia.
- **Alternatives considered**:
  - Una sola query por rama (descartado por cobertura insuficiente).
  - Loop sin limite (descartado por riesgo de runaway execution).

## Decision 15: Relaciones semanticas entre iteraciones

- **Decision**: Generar y persistir relaciones semanticas por iteracion (query→finding, finding→source, finding→finding).
- **Rationale**: Permite medir convergencia, detectar contradicciones y explicar evolucion del conocimiento.
- **Alternatives considered**:
  - Embedding solo final (descartado por perdida de trazabilidad temporal).

## Decision 16: Matriz agente→skill MCP obligatoria

- **Decision**: Definir por rama herramientas MCP permitidas, orden de uso y limites de ejecucion en un contrato unico.
- **Rationale**: Reduce deriva operativa entre agentes y facilita auditoria.
- **Alternatives considered**:
  - Permitir uso libre de tools por agente (descartado por comportamiento inconsistente).

## Decision 17: Prompt contracts versionados por agente

- **Decision**: Usar plantilla fija por agente con objetivo, contexto, salida, calidad, do/don't e incertidumbre.
- **Rationale**: Mejora estabilidad de resultados y facilita regression testing.
- **Alternatives considered**:
  - Prompts ad-hoc por ejecucion (descartado por variabilidad y baja trazabilidad).

## Decision 18: Contrato de artefactos y rutas por sesion

- **Decision**: Estandarizar artefactos en `sessions/{session_id}/...` con naming/version/retencion por tipo.
- **Rationale**: Facilita reproducibilidad y control de costos de almacenamiento.
- **Alternatives considered**:
  - Guardado libre por componente (descartado por dificultad de auditoria).

## Decision 19: Capa de evaluacion operativa

- **Decision**: Establecer KPIs por rama y pruebas de regresion de prompts con golden cases.
- **Rationale**: Garantiza calidad estable tras cambios de prompts, modelos o tools.
- **Alternatives considered**:
  - Validacion manual eventual (descartado por baja confiabilidad en produccion).

## Decision 20: System Base Standardization

- **Decision**: Centralizar reglas globales de agentes en un unico artefacto canonico (`system-base.md`) y componer prompts en runtime via SystemBase + BranchOverlay + UserQuery.
- **Rationale**: Elimina duplicacion de reglas globales entre ramas, reduce complejidad del planner, y permite propagar cambios de comportamiento a todos los agentes sin modificar su codigo.
- **Alternatives considered**:
  - Mantener reglas embebidas en cada PromptContract de rama (descartado por duplicacion y baja mantenibilidad).
  - Reglas globales inline en PlanBuilder (descartado por mezcla de orquestacion y configuracion).

## Clarification Status

- No `NEEDS CLARIFICATION` pendientes para avanzar a Phase 1.

## Storage Decision

- La linea oficial de almacenamiento es `Postgres + pgvector`.
- Supabase no es una dependencia operativa separada en esta implementacion; cualquier referencia antigua se considera historica.
