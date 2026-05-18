# Arquitectura — Vigilador Tecnológico 2.0

## Capas

```mermaid
flowchart TD
    API["API · FastAPI<br/>12 routes · DI ~47 svcs · guards"]
    APP["Application<br/>orquestación · agentes · gobernanza<br/>fusión · grafo · evaluación · routing"]
    DOM["Domain<br/>entidades · repos · state machine · contratos"]
    INF["Infrastructure<br/>DB · MCP · LLM · embeddings · pgvector"]
    API --> APP --> DOM
    APP --> INF --> DOM
```

## Pipeline de sesión + estados

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> CLARIFYING: start
    CLARIFYING --> PLANNING: respuestas
    PLANNING --> APPROVED: usuario aprueba
    APPROVED --> EXECUTING: 6 ramas ∥
    EXECUTING --> COMPLETED: fusión+grafo+forecast
    COMPLETED --> [*]
    DRAFT --> CANCELED
    CLARIFYING --> CANCELED
    PLANNING --> CANCELED
    APPROVED --> CANCELED
    EXECUTING --> FAILED
```

## Orquestación completa

```mermaid
flowchart TD
    U[Usuario] --> CL[ClarifyService<br/>preguntas]
    CL --> PB[PlanBuilder<br/>ResearchPlan · 6 ramas]
    PB --> AP{Aprobado?}
    AP -->|sí| BC[BranchCoordinator]
    BC --> EXEC["6 BranchAgents ∥<br/>asyncio.gather"]
    EXEC --> FU[Fusion]
    FU --> EL[EvidenceLinker]
    EL --> IS[Intelligence Sections]
    IS --> AC[AdversarialCritic]
    AC --> CC[ConfidenceCalibrator]
    CC --> RS[ReportSynthesizer]
    RS --> GR[KnowledgeGraph<br/>NetworkX]
    RS --> TF[TrendForecaster<br/>no bloqueante]
    GR & TF --> RV[ReportVariants]
```

## Ejecución de rama + sub-agentes + planner reactivo

```mermaid
flowchart TD
    subgraph BR ["BranchAgent · iteración"]
        direction TB
        PC["PromptComposer<br/>SystemBase+Overlay+filtro allowed_tools"]
        TS["ToolSelector (sub-agente tool)<br/>1·cadena PDF→texto<br/>2·sugerencia payload<br/>3·afinidad query↔tool<br/>4·barrido determinista"]
        EXE["execute · MCP"]
        FS["FollowupStrategist (sub-agente query)<br/>propone next_query"]
        SAT["SaturationTracker<br/>¿aporta info nueva?"]
        PC --> TS --> EXE --> SAT
        SAT -->|sigue| FS --> TS
        SAT -->|saturado / depth| OUT[BranchResult]
    end

    EXE -.señal gap/entidad.-> SQ[(signal_queue)]
    SQ --> SCL["_signal_consumer_loop<br/>MAX_REPLANS=5"]
    SCL --> RP["ReplanAction<br/>directive → receive_directive"]
    RP -.mid-execution.-> BR
    EXE -.cross-branch.-> XS["_process_cross_signals<br/>sub-ejecución relevance>umbral"]
```

## Niveles de confianza · calibración

```mermaid
flowchart LR
    P["Prompt asigna<br/>confidence 0.7 / 0.9..."] --> CAL[ConfidenceCalibrator]
    subgraph CAL [ConfidenceCalibrator]
        direction TB
        B["buckets [0·0.2·0.4·0.6·0.8·1.0]"]
        R["record(predicho, ¿confirmado?)"]
        F["factor = real / predicho<br/>(min N obs)"]
        B --> R --> F
    end
    CAL --> O["confidence calibrada<br/>= raw × factor"]
    O --> RPT[CalibrationReport<br/>desvío por bucket]
```

## Pipeline de inteligencia (fusión)

```mermaid
flowchart TD
    BR["6 BranchResults<br/>findings + sources + entities"] --> EL[EvidenceLinker<br/>liga claim↔fuente]
    EL --> HD[HypeDetector<br/>madurez vs ruido]
    HD --> CA[ContradictionAnalyzer<br/>claims opuestos]
    CA --> WS[WeakSignalDetector<br/>señales tempranas]
    WS --> CT[CausalTimelineBuilder<br/>línea temporal]
    CT --> FI[FindingImpactScorer]
    FI --> AC["AdversarialCritic<br/>ataca claims sin evidencia"]
    AC --> CK{passed?}
    CK -->|no| FLAG[marca débiles]
    CK -->|sí| OK[ok]
    FLAG & OK --> SY[ReportSynthesizer<br/>secciones]
```

## Agente → MCP → fuentes

```mermaid
flowchart LR
    AG[BranchAgent] --> SR[SmartToolRouter<br/>clasifica: academic/company<br/>bibliometric/news...]
    SR --> SM[StrategyMemory<br/>orden aprendido]
    AG --> EC[MCPExecutionClient<br/>cache · retry · timeout]
    EC --> REG[MCPProviderRegistry<br/>14 providers]
    REG --> WEB[tavily · exa · jina<br/>brave · firecrawl · serper · fetch]
    REG --> ACA[arxiv · scholar · openalex]
    REG --> AUX[sandbox · markitdown<br/>playwright · minimax-image]
    AG --> OAR[OpenAlex REST<br/>fallback bibliométrico]
```

## SSE → Frontend

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant S as SSE
    participant H as sseHandlers
    participant V as AgentDetailPanel
    O->>S: SessionStarted / ClarificationRequested
    O->>S: BranchStarted (×6)
    loop iteración por rama
        O->>S: BranchProgress {reasoning, toolCall, confidence}
        S->>H: addIteration
        H->>V: render cadena de pensamiento
    end
    O->>S: ReplanTriggered {signal, source→target, directive}
    O->>S: BranchCompleted / AllBranchesCompleted
    O->>S: FusionProgress → GraphAnalyticsComputed
    O->>S: ReportGenerated / ReportVariantsGenerated
```

## Mock server vs backend real

```mermaid
flowchart TD
    subgraph REAL ["Backend real (requiere PostgreSQL + MCP + LLM)"]
        direction TB
        R1[Orquestación + 6 ramas ∥]
        R2[ToolSelector · FollowupStrategist]
        R3[Planner reactivo · ConfidenceCalibrator]
        R4[7 detectores + AdversarialCritic]
        R1 --> R2 --> R3 --> R4
    end

    subgraph MOCK ["Mock server (datos estáticos · sin deps)"]
        direction TB
        M1[Eventos SSE simulados]
        M2["Cadenas de pensamiento ✓<br/>BRANCH_ITERATIONS"]
        M3["ReplanTriggered ✓<br/>REPLAN_SIGNALS"]
        M4["Calibración ✓<br/>confidenceCalibration"]
        M5["6 secciones inteligencia ✓<br/>markdown reporte"]
        M1 --> M2 & M3 & M4 & M5
    end

    REAL -.simula salida observable.-> MOCK
    MOCK --> FE[Frontend · misma UI para ambos]
```

## Ejecución aislada de código (TrendForecaster)

```mermaid
flowchart TD
    TF[TrendForecaster] --> P1{subproceso<br/>aislado}
    P1 -->|ok| OUT[proyección polinómica]
    P1 -->|falla| P2{numpy<br/>en proceso}
    P2 -->|ok| OUT
    P2 -->|falla| P3[regresión lineal<br/>sin numpy]
    P3 --> OUT

    subgraph NOTA ["Limitación conocida"]
        direction TB
        N1["MCP sandbox server: existe y es MCP válido"]
        N2["execution_client: protocolo MCP real (JSON-RPC)"]
        N3["stdio_client SDK cuelga en teardown<br/>en Windows con tareas lentas"]
        N1 --- N2 --- N3
    end

    TF -.NO usa el server MCP.-> NOTA
```

> **Aislamiento de ejecución:** el TrendForecaster ejecuta numpy en
> `subprocess.run` aislado (cwd/env acotado, en `asyncio.to_thread`), no vía
> el servidor MCP sandbox. El protocolo MCP STDIO de `execution_client` se
> reparó (JSON-RPC real, antes era ad-hoc roto), pero el `stdio_client` del
> SDK MCP tiene un teardown que cuelga en Windows con servidores lentos
> (`list_libraries` ✓, `execute_code` ✗). El subproceso directo logra el
> mismo aislamiento, es portable, y degrada con 3 niveles.
