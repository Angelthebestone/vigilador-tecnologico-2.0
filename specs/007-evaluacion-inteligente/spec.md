# Feature Specification: Sistema de Evaluacion Inteligente — Reemplazo de Heuristicas Hardcodeadas

## Problem Statement

El sistema actual de evaluacion y scoring depende de heuristicas
hardcodeadas que limitan la precision, adaptabilidad y escalabilidad:

- **SourceScorer**: Score basado en匹配 de dominio padre y volumen;
  no considera reputacion del autor, h-index, retracciones ni conflictos
  de interes. El decaimiento temporal es uniforme, no especifico por
  dominio.
- **ConfidenceCalibrator**: Buckets fijos con formula heuristico
  `buzz = max(0, substance // 2)` sin validacion empirica. No persiste
  estado entre reinicios.
- **TRL inference**: Derivado de senales relativas heuristicas, sin
  metrica de reproducibilidad real ni validacion contra datos concretos.
- **ContradictionAnalyzer**: Solapamiento lexico de 4+ letras para
  detectar contradicciones; no identifica asunciones implicitas, no
  genera mapas de consenso/disputa.
- **Sintesis y validacion**: Sin meta-analisis cuantitativo, sin paso de
  falsificacion, sin auditoria de sesgos, sin trazabilidad forense
  completa.
- **Deteccion de patrones**: Limitada a clustering basico de entidades;
  no hay deteccion de convergencia tecnologica temprana, redes de
  colaboracion, cambios de narrativa ni movilidad de talento.

Cada nueva metrica o criterio requiere codigo ad-hoc en vez de
plug-and-play. No hay paralelismo porque las evaluaciones estan
acopladas al pipeline secuencial de cada rama.

## Scope Boundaries

### In Scope

Cinco workstreams paralelos que construyen nuevo sistema de evaluacion
desde cero. Cada workstream produce componentes independientes y
reemplaza progresivamente las heuristicas actuales.

- **WS-A — Evaluacion de Fuentes (Source Quality)**: Reputacion
  multidimensional, deteccion de conflictos, temporal decay por dominio,
  cross-validation externa, monitor de retractaciones, metrica de
  reproducibilidad.
- **WS-B — Procesamiento Inteligente (Data Intelligence)**: Busqueda
  neuronal hibrida, query expansion contextual, deduplicacion semantica,
  extraccion con esquemas estrictos, normalizacion multilingue, mapas
  de consenso/disputa.
- **WS-C — Analisis Profundo (Deep Analysis)**: Deteccion de asunciones
  implicitas, trayectoria tecnologica y curvas-S, dependencias criticas,
  sintesis contrafactual, meta-analisis cuantitativo.
- **WS-D — Senales Estrategicas (Strategic Signals)**: Convergencia
  tecnologica temprana, redes de colaboracion, linaje de ideas, cambios
  de narrativa, movilidad de talento, brechas de patentamiento.
- **WS-E — Garantia de Calidad (Output Assurance)**: Golden cases
  benchmark, simulacion de stakeholders, busqueda de falsificadores,
  auditoria de sesgos, explicabilidad de trazas.

Cada workstream incluye:
- Su propia arquitectura de puertos (Protocols) e implementaciones
- Sus propias fuentes de datos (MCP, APIs externas, DB)
- Capacidad de ejecucion paralela independiente

### Out of Scope

- Refactor de la infraestructura base (cubierto por spec 006).
- Cambios en el pipeline base de agentes (pipeline steps del spec 006).
- Proveedores MCP concretos (se reusan los existentes).
- Interfaz de usuario frontend (cambios puramente backend).
- Migracion de datos existentes (sistema nuevo corre en paralelo).

## Assumptions

- El spec 006 (fundacional) se ejecuta primero o en paralelo solo si
  sus cambios no son requisito previo — WS-A y WS-B necesitan los
  puertos de dominio (006 Fase 2), el resto puede empezar desde el
  dia 1.
- Cada workstream produce artefactos que coexisten con el sistema
  actual hasta que se complete su migracion.
- Los golden cases (WS-E) se disenan primero para servir como
  especificacion ejecutable del resto.
- Todos los workstreams son independientes y pueden asignarse a
  distintos desarrolladores simultaneamente.
- La puntuacion del sistema actual (6.2/10 → 7.5-8/10 post-006) no
  incluye estas nuevas capacidades; se medira por separado.

## User Scenarios & Testing

### Primary User Story

**Como** analista de vigilancia tecnologica,
**Quiero** que el sistema evalue fuentes con criterios multidimensionales
y detecte patrones estrategicos automaticamente,
**Para** tomar decisiones informadas sin depender de heuristicas fijas
ni analisis manual repetitivo.

### Acceptance Scenarios

1. **Given** una fuente con autor conocido,
   **When** WS-A evalua su credibilidad,
   **Then** debe considerar h-index, retracciones y afiliacion,
   no solo el dominio.

2. **Given** dos articulos sindicados (mismo contenido, distinta URL),
   **When** WS-B procesa las fuentes,
   **Then** debe deduplicarlas semanticamente y no contarlas como
   fuentes independientes.

3. **Given** tres estudios con datos numericos dispersos sobre el mismo
   fenomeno,
   **When** WS-C ejecuta meta-analisis,
   **Then** debe extraer rangos consensuados e identificar valores
   anomalos.

4. **Given** una tecnologia emergente (ej: IA + biologia sintetica),
   **When** WS-D analiza publicaciones y patentes,
   **Then** debe senalar convergencia temprana antes de que sea obvia
   en la literatura mainstream.

5. **Given** una conclusion del sistema,
   **When** WS-E ejecuta busqueda de falsificadores,
   **Then** debe generar explicitamente: "Esta conclusion se podria
   tumbar si apareciera evidencia de [X]".

6. **Given** un reporte generado,
   **When** WS-E audita sesgos,
   **Then** debe detectar sesgos geograficos, de genero o
   institucionales y bloquear la salida si son críticos.

### Edge Cases

- Fuentes sin autor identificable: WS-A debe degradar gracefulmente
  (scoring basado solo en dominio + contenido).
- Idioma mixto en fuentes: WS-B debe detectar cambio de idioma y
  aplicar normalizacion automatica o marcar como advertencia.
- Sin datos historicos suficientes: WS-C debe senalar baja confianza
  en curvas-S y trayectorias.
- Patentes sin correlato cientifico: WS-D debe marcar como "oceano
  azul candidato" con alta incertidumbre.
- Golden case que falla: WS-E no debe bloquear el despliegue pero si
  marcar la regresion con prioridad critica.

## Functional Requirements

### WS-A — Evaluacion de Fuentes (Source Quality)

- **FR-A01** (Idea 7): Expandir SourceScorer para incluir reputacion
  multidimensional del autor: h-index, historial de retracciones,
  afiliacion institucional, numero de citas. Cada dimension con peso
  configurable por dominio tecnologico. Los scores de reputacion deben
  persistirse usando el Protocol `SourceTrustStore` definido en 006
  FR-010, evitando crear un almacenamiento duplicado.
- **FR-A02** (Idea 8): Detectar conflicto de intereses analizando
  financiamiento corporativo vs. academico en metadatos de la fuente.
  Marcar hallazgos como "alto riesgo de sesgo" si la proporcion
  supera un umbral configurable.
- **FR-A03** (Idea 9): Implementar Temporal Decay Weighting con curva
  de decaimiento especifica por dominio tecnologico (ej: IA decae mas
  rapido que matematicas). El decay debe ser configurable por tipo
  de fuente y revisable periodicamente.
- **FR-A04** (Idea 10): Cross-validar claims contra bases de datos
  de hechos conocidos (fact-checking APIs, bases de dominio publico)
  antes del analisis profundo. Marcar discrepancias como "no verificado"
  o "contradicho por fuente externa".
- **FR-A05** (Idea 11): Monitor de retractaciones en tiempo real:
  chequeo periodico contra bases de retractacion (Retraction Watch,
  PubMed). Si una fuente clave es retractada, invalidar todos los
  findings que dependen de ella y notificar.
- **FR-A06** (Idea 12): Anadir metrica de reproducibilidad para
  hallazgos tecnicos: verificar existencia de repositorio, datos
  abiertos, ambiente replicable. Alimentar la deteccion de TRL
  (Technology Readiness Level) como senal adicional.

### WS-B — Procesamiento Inteligente (Data Intelligence)

- **FR-B01** (Idea 1): Implementar busqueda neuronal hibrida que
  combine busqueda vectorial (embeddings) + busqueda por keywords con
  pesos ajustables. Usar triangulacion automatica para validar claims
  apareciendo en multiples fuentes con diferentes perspectivas
  (confirmacion vs contradiccion).
- **FR-B02** (Idea 2): El followup_strategist debe usar expansion
  contextual basada en entidades detectadas en iteraciones anteriores.
  Aprender terminos y relaciones nuevas de cada ciclo de follow-up
  para refinar busquedas subsecuentes.
- **FR-B03** (Idea 3): Implementar deduplicacion semantica profunda
  que compare contenido textual (no solo URL) usando embeddings de
 相似idad. Noticias sindicadas con redaccion distinta pero mismo
  contenido factual deben contarse como una sola fuente.
- **FR-B04** (Idea 4): Los extractores MCP deben devolver JSON
  validado contra esquemas estrictos (JSON Schema) definidos por tipo
  de fuente y dominio. Los esquemas deben construirse sobre los MCP
  Response Types definidos en 006 FR-019 (NavigationResult,
  ScreenshotResult, SearchResult, etc.), anadiendo validacion semantica
  por dominio. Eliminar todo parsing post-extraccion.
- **FR-B05** (Idea 5): Normalizacion multilingue de metadatos:
  traducir titulos, abstracts y palabras clave al idioma de trabajo.
  Detectar burbujas de idioma (sobrerrepresentacion de fuentes en un
  solo idioma) y marcarlas en el reporte.
- **FR-B06** (Idea 13): ContradictionAnalyzer debe generar mapas
  visuales de consenso y disputa (quien dice que, nivel de evidencia,
  direccion del desacuerdo). Resolver contradicciones activamente
  cuando sea posible (triangulacion con tercera fuente).
- **FR-B07** (Idea 6): Detectar contenido generado por IA y refinar
  el scoring de frescura con autenticidad. Calcular para cada fuente
  un `ai_probability` combinando perplejidad/burstiness (via LLM en
  modo log-prob) y heuristicas de boilerplate. Publicar
  `effective_freshness = raw_freshness * (1 - ai_probability *
  penalty_factor)` con `penalty_factor` configurable por dominio.
  No eliminar fuentes — solo penalizar peso downstream en
  `SourceScorer`.

### WS-C — Analisis Profundo (Deep Analysis)

- **FR-C01** (Idea 14): Detectar asunciones implicitas en textos
  fuente ("asumiendo que X crece linealmente", "bajo condiciones de
  laboratorio"). Exponerlas en el campo `uncertainty_reason` del
  finding y refinar el nivel de confianza automaticamente.
- **FR-C02** (Idea 15): Proyectar trayectoria tecnologica usando
  frecuencia y calidad de publicaciones en el tiempo. Ajustar curvas-S
  (logisticas) por dominio. Detectar puntos de inflexion donde una
  tecnologia acelera o se estanca.
- **FR-C03** (Idea 16): Mapear dependencias criticas a nivel de
  tecnologia: materiales raros, librerias abandonadas, cuellos de
  botella en supply chain. Marcar tecnologias con dependencias
  fragiles como "alto riesgo de adopcion".
- **FR-C04** (Idea 17): Generar sintesis contrafactual como parte
  estandar del reporte: "Que pasaria si [proveedor X cierra]? Que
  pasaria si [regulacion Y cambia]?" Cada escenario con nivel de
  probabilidad estimado.
- **FR-C05** (Idea 18): Realizar meta-analisis cuantitativo automatico
  sobre datos numericos dispersos en multiples fuentes. Extraer
  rangos consensuados, valores anomalos y tamanos de efecto. Validar
  concordancia entre estudios (I^2, Q-test).

### WS-D — Senales Estrategicas (Strategic Signals)

- **FR-D01** (Idea 19): Usar clustering semantico sobre embeddings de
  abstracts para detectar convergencia tecnologica temprana (ej:
  tecnicas de IA aplicadas a biologia molecular). La convergencia debe
  senalarse antes de que sea evidente en el numero de publicaciones.
- **FR-D02** (Idea 20): Mineria de redes de colaboracion: analizar
  co-autorias en publicaciones y co-inventores en patentes para
  mapear hubs de innovacion. Detectar burbujas (grupo pequeno de
  autores que se auto-citan).
- **FR-D03** (Idea 21): Rastrear linaje de ideas hasta su origen
  primario: para cada tecnologia o concepto, identificar la
  publicacion seminal y la cadena de citas. Detectar circularidad
  (A cita a B que cita a A).
- **FR-D04** (Idea 22): Monitorear cambios de narrativa en series
  temporales: detectar cuando el tono de la literatura cambia
  (revolucionario → problematico, prometedor → estancado). Usar
  analisis de sentimiento y frecuencia de terminos calificativos.
- **FR-D05** (Idea 23): Rastrear movilidad de talento como indicador
  de madurez comercial: detectar cuando autores publican en academia
  y luego aparecen como inventores en patentes o empleados de
  startups. Alta movilidad = senal de transferencia tecnologica.
- **FR-D06** (Idea 24): Cruzar literatura cientifica con bases de
  patentes para identificar brechas (tecnologia con mucha ciencia
  pero poca patente = oceano azul). Mapa de densidad ciencia vs.
  patentes por subdominio tecnologico.

### WS-E — Garantia de Calidad (Output Assurance)

- **FR-E01** (Idea 25): Disenar suite de golden cases: escenarios
  reales con resultados esperados conocidos. Ejecutar en cada cambio
  significativo (commits a componentes de evaluacion). Cualquier
  regresion en calidad de sintesis debe detener el pipeline.
- **FR-E02** (Idea 26): Agentes criticos que simulan perspectivas
  de stakeholders (inversor, regulador, competidor, academia). Cada
  agente ataca las conclusiones desde su optica, generando
  contrapuntos estructurados anexos al reporte.
- **FR-E03** (Idea 27): Paso de falsificacion obligatorio al final
  del analisis: "Que evidencia hipotetica tumbaria esta conclusion?".
  Si no se puede formular al menos un escenario de falsificacion
  plausible, la conclusion se marca como "no falsable" (advertencia).
- **FR-E04** (Idea 28): Auditoria automatica de sesgos antes de
  entregar el reporte: sesgo geografico (sobrerrepresentacion de
  paises), de genero (autores), institucional (solo academia, solo
  industria). Si un sesgo supera el umbral critico, bloquear la
  salida y notificar al operador.
- **FR-E05** (Idea 29): Garantizar trazabilidad forense completa
  para cada claim en el reporte: claim → fuente(s) → extracto(s) →
  razonamiento → nivel de confianza. Cada paso debe ser auditable
  en una sola traza sin saltos.
- **FR-E06** (Calibracion): Implementar sistema de calibracion de
  confianza que reemplace el ConfidenceCalibrator actual. La calibracion
  debe basarse en golden cases historicos (FR-E01): cada vez que un
  golden case se ejecuta, el resultado real (acierto/fallo) se compara
  con la confianza estimada y se ajusta el calibrador. Los buckets de
  calibracion deben persistirse en DB y cargarse al iniciar. La formula
  `buzz = max(0, substance // 2)` debe reemplazarse por una curva de
  calibracion empirica derivada de datos reales.

### Integracion con Spec 006

- **FR-X01** (Cross-cutting): Cada workstream debe integrarse como un
  paso del pipeline definido en 006 FR-014 (ComposePromptStep,
  ToolLoopStep, SandboxExecutionStep, AssembleBranchResultStep). Los
  workstreams de evaluacion (WS-A, WS-C, WS-D) ejecutan como sub-pasos
  dentro de ToolLoopStep o como pasos posteriores a
  AssembleBranchResultStep. La integracion exacta (antes/despues de
  cada paso) debe definirse durante `/speckit.plan` de 007, pero la
  infraestructura de pipeline del 006 debe soportar la insercion de
  nuevos steps sin modificar el flujo base.

## Key Entities

- **ReputacionAutor**: Score multidimensional con h-index, retracciones,
  afiliacion, citas, peso por dominio.
- **ConflictoIntereses**: Relacion fuente → entidad financiadora,
  tipo (corp/academico), proporcion, nivel de riesgo.
- **TemporalDecayConfig**: Curva de decaimiento parametrizada por
  dominio tecnologico y tipo de fuente.
- **ClaimExternalValidation**: Resultado de cross-validation contra
  bases de hechos externas (verificado/contradicho/no verificado).
- **RetractionMonitor**: Servicio que chequea retractaciones y
  mantiene indice de fuentes invalidadas con hallazgos dependientes.
- **ReproducibilidadScore**: Indicadores de repo, datos abiertos,
  ambiente replicable; alimenta TRL.
- **DeduplicacionSemantica**: Indice de similaridad entre fuentes
  basado en embeddings; umbral configurable para considerar duplicado.
- **EsquemaExtraccion**: JSON Schema por tipo de fuente/dominio;
  validates salida de extractores MCP.
- **MapaConsensoDisputa**: Grafo dirigido de afirmaciones con
  niveles de evidencia, direccion de desacuerdo, fuentes por lado.
- **AsuncionImplicita**: Afirmacion no declarada en texto fuente
  que afecta la validez de la conclusion.
- **CurvaS**: Modelo logistico de madurez tecnologica con punto de
  inflexion, tasa de crecimiento, estimacion de meseta.
- **DependenciaCritica**: Recurso externo (material, libreria,
  proveedor) del cual depende una tecnologia, con nivel de riesgo.
- **EscenarioContrafactual**: Pregunta "que pasaria si" con
  probabilidad estimada e impacto en conclusiones.
- **MetaAnalisis**: Conjunto de estudios con tamanos de efecto,
  heterogeneidad (I^2), rangos consensuados, outliers.
- **ClusterConvergencia**: Grupo de tecnologias de diferentes
  dominios con similaridad semantica creciente en el tiempo.
- **RedColaboracion**: Grafo de co-autores/co-inventores con
  metricas de centralidad, deteccion de burbujas.
- **LinajeIdeas**: Arbol de citas desde publicacion seminal hasta
  estado del arte; deteccion de circularidad.
- **CambioNarrativa**: Transicion de tono en series temporales con
  punto de cambio, sentimiento pre/post.
- **BrechaPatentamiento**: Diferencia entre densidad de publicaciones
  cientificas y patentes por subdominio.
- **GoldenCase**: Escenario de prueba con fuentes, pipeline y
  resultado esperado conocido.
- **SimulacionStakeholder**: Perfil de agente critico (inversor,
  regulador, etc.) con sesgos y criterios de evaluacion conocidos.
- **EscenarioFalsificacion**: Evidencia hipotetica que, de aparecer,
  invalidaria la conclusion.
- **AuditoriaSesgos**: Reporte de sesgos detectados (geo, genero,
  institucional) con umbrales y accion tomada.
- **TrazaForense**: Cadena completa claim → fuente → extracto →
  razonamiento → confianza, serializable para auditoria.

## Success Criteria

- **SC-A01**: WS-A asigna score de autor considerando >= 4
  dimensiones (h-index, retracciones, afiliacion, citas) —
  verificable contra fuentes con metadata completa.
- **SC-A02**: WS-A detecta conflicto de intereses en >= 80% de
  fuentes con financiamiento corporativo explicito.
- **SC-A03**: Temporal decay difiere por dominio tecnologico
  (ej: IA vs matematicas) — verificable via configuracion.
- **SC-A04**: Cross-validation externa ejecutada contra >= 2 bases
  de hechos antes del analisis profundo.
- **SC-A05**: Retraction monitor chequea fuentes cada <= 24h e
  invalida findings dependientes automaticamente.
- **SC-A06**: Metrica de reproducibilidad disponible para >= 90%
  de hallazgos tecnicos con repo publico.
- **SC-B01**: Busqueda hibrida produce recall >= 20% superior a
  busqueda solo-keyword en corpus de prueba multilenguaje.
- **SC-B02**: Deduplicacion semantica reduce conteo de fuentes
  sindicadas en >= 60% sin falsos positivos en fuentes unicas.
- **SC-B03**: Esquemas JSON validan 100% de respuestas de
  extractores MCP; cero parsing post-extraccion.
- **SC-B04**: Mapas de consenso/disputa generados para >= 3
  afirmaciones contradictorias en el mismo reporte.
- **SC-B05**: `ai_probability` y `effective_freshness` poblados para
  >= 95% de fuentes procesadas con WS-B activo; corpus de prueba
  con muestras humanas y muestras LLM logra precision >= 0.7 en la
  clasificacion (umbral 0.5).
- **SC-C01**: Asunciones implicitas detectadas en >= 50% de
  fuentes con supuestos declarados implicitamente.
- **SC-C02**: Curvas-S proyectadas para >= 3 dominios con
  R^2 >= 0.8 en datos historicos suficientes.
- **SC-C03**: Dependencias criticas mapeadas para toda tecnologia
  que declare componentes externos en su descripcion.
- **SC-C04**: Sintesis contrafactual generada como seccion
  estandar en >= 90% de reportes.
- **SC-D01**: Convergencia temprana detectada con >= 6 meses de
  antelacion a pico de publicaciones (validable con datos historicos).
- **SC-D02**: Redes de colaboracion con >= 10 nodos mapeadas
  correctamente (co-autoria verificable).
- **SC-D03**: Linaje de ideas rastreado hasta publicacion seminal
  con >= 80% de precision en cadena de citas.
- **SC-D04**: Cambios de narrativa detectados con sentimiento
  pre/post en series de >= 12 meses.
- **SC-E01**: Suite de golden cases >= 10 escenarios; ejecucion
  automatica en cada commit relevante.
- **SC-E02**: Simulacion de stakeholders genera >= 3 perspectivas
  distintas por reporte, con contrapuntos estructurados.
- **SC-E03**: Paso de falsificacion ejecutado en 100% de
  conclusiones; las no falsables marcadas con advertencia.
- **SC-E04**: Auditoria de sesgos bloquea >= 1 salida con sesgo
  critico detectable en corpus de prueba.
- **SC-E05**: Cada claim en reporte tiene traza forense completa
  (claim → fuente → extracto → razonamiento) verificable por
  auditor externo.
- **SC-E06**: ConfidenceCalibrator reemplazado por curva de
  calibracion empirica basada en golden cases historicos. El
  calibrador debe persistir estado en DB y recuperarlo al reiniciar
  el servicio. La formula `buzz = max(0, substance // 2)` no debe
  existir en el codigo base.

## Delivery Constraints

- Cada workstream es independiente y debe poder asignarse a
  distintos equipos/personas en paralelo (simplicidad, bajo
  acoplamiento — Principios de Diseno de Software).
- Todos los componentes nuevos deben definirse via Protocols en
  domain/ (ISP, DIP — Constitucion).
- Ningun workstream debe requerir modificaciones en el pipeline
  base de agentes (cubierto por spec 006).
- Golden cases (WS-E) deben disenarse primero como especificacion
  ejecutable, antes de implementar los demas workstreams (Entrega
  Verificable — Constitucion).
- Todo nuevo componente debe incluir tests unitarios y de
  integracion; los golden cases sirven como tests de regresion.
- No se permite modificar heuristicas existentes hasta que el
  reemplazo este completo y validado (coexistencia).
