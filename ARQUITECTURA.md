# Arquitectura — Vigilador Tecnológico 2.0

## Flujo completo de una investigación

```mermaid
flowchart TD
    subgraph ENTRADA["1. Entrada"]
        U["👤 Usuario<br/>POST /research/start<br/>query + scope"]
    end

    subgraph CLARIFICACION["2. Clarificación"]
        CS[ClarifyService<br/>LLM genera preguntas]
        ANS["Usuario responde<br/>POST /research/{id}/clarify"]
    end

    subgraph PLANIFICACION["3. Planificación"]
        PRE["preload_for_session<br/>memoria cross-session<br/>entidades recurrentes"]
        PB["PlanBuilder<br/>LLM planning prompt<br/>→ 6 ramas + constraints"]
        PLAN["ResearchPlan v1<br/>depth_limit=3<br/>requires_approval=true"]
    end

    subgraph APROBACION["4. Aprobación"]
        AP{"¿usuario<br/>aprueba?"}
        MOD["POST /modify<br/>ajusta ramas<br/>nueva versión"]
        REJ["rechazado ✗"]
    end

    subgraph EJECUCION["5. Ejecución paralela · 6 ramas"]
        direction LR
        subgraph RAMA["BranchAgent × 6 ∥"]
            PC[PromptComposer<br/>SystemBase+Overlay+filtro tools]
            TS[ToolSelector<br/>selecciona tool × query]
            EXE[execute MCP<br/>tavily·exa·brave·scholar…]
            FS[FollowupStrategist<br/>propone next_query]
            SAT{SaturationTracker<br/>¿saturado?}
            PC --> TS --> EXE --> SAT
            SAT -->|no, depth<3| FS --> TS
            SAT -->|sí| BRES[BranchResult<br/>findings+sources+entities]
        end
        SIG["_signal_consumer_loop<br/>cross-branch signals<br/>MAX_REPLANS=5"]
        RAMA -.gap/entidad.-> SIG
        SIG -.replan directive.-> RAMA
    end

    subgraph EVALUACION["6. Workstreams de evaluación · spec 007 · opt-in"]
        direction TB
        WSA["WS-A · SourceQuality<br/>reputación autor · conflicto<br/>factcheck · retractación<br/>reproducibilidad · decay"]
        WSB["WS-B · DataIntelligence<br/>BM25+embed · dedup semántico<br/>schema pydantic · IA detector<br/>multilingüe · consenso/disputa"]
        WSC["WS-C · DeepAnalysis<br/>curva-S logística · meta-análisis<br/>asunciones · contrafactual<br/>dependencias críticas"]
        WSD["WS-D · StrategicSignals<br/>convergencia · redes colaboración<br/>linaje ideas · narrativa<br/>talento · brechas patentes"]
        WSA --> WSB --> WSC --> WSD
    end

    subgraph FUSION["7. Fusión + inteligencia"]
        EL[EvidenceLinker<br/>dedup URL + link claim↔fuente<br/>cross-branch consensus boost]
        HD[HypeDetector<br/>madurez vs ruido<br/>Gartner stage]
        CA[ContradictionAnalyzer<br/>claims opuestos<br/>triangulación]
        WS[WeakSignalDetector<br/>señales tempranas<br/>baja confianza + alta novedad]
        CT[CausalTimelineBuilder<br/>causa→efecto temporal]
        FI[FindingImpactScorer<br/>autoridad×novedad×convergencia]
        AC["AdversarialCritic<br/>ataca claims sin evidencia<br/>descarta o marca débiles"]
        EL --> HD --> CA --> WS --> CT --> FI --> AC
    end

    subgraph QUALITY["8. Quality Gate · WS-E"]
        direction TB
        T1["1·forensic trace<br/>JSONB paso a paso<br/>audit trail inmutable"]
        T2["2·bias audit<br/>geográfico/género/institucional<br/>→ 409 si crítico"]
        T3["3·falsificación<br/>LLM prober × conclusión<br/>¿puede refutarse?"]
        T4["4·stakeholders<br/>investor·regulator<br/>competitor·academic"]
        T5["5·calibración isotónica<br/>sklearn IsotonicRegression<br/>vs golden cases"]
        T1 --> T2 --> T3 --> T4 --> T5
        T2 -.bloquea si bias crítico.-> BLOCK["❌ HTTP 409<br/>QualityGateBlocked"]
    end

    subgraph SALIDA["9. Salida"]
        RS["ReportSynthesizer<br/>LLM synthesis prompt<br/>→ ejecutivo+técnico+riesgo<br/>recomendaciones+confianza"]
        GR["KnowledgeGraph<br/>NetworkX · centralidad<br/>clusters · layout"]
        TF["TrendForecaster<br/>proyección polinómica<br/>subproceso aislado"]
        OUT["📄 FinalReport<br/>+ 3 variantes<br/>+ graph analytics<br/>+ forecast"]
        RS --> OUT
        GR --> OUT
        TF --> OUT
    end

    ENTRADA --> CLARIFICACION
    CLARIFICACION --> PLANIFICACION
    PLANIFICACION --> APROBACION
    AP -->|sí| MOD
    AP -->|sí| EJECUCION
    AP -->|no| REJ
    MOD --> EJECUCION
    EJECUCION --> EVALUACION
    EVALUACION --> FUSION
    FUSION --> QUALITY
    QUALITY --> BLOCK
    QUALITY --> SALIDA
```

> **Estados de sesión**: `DRAFT → CLARIFYING → PLANNING → APPROVED → EXECUTING → COMPLETED`
> **Workstreams de evaluación**: WS-A (`VT_EVAL_WS_A_ENABLED`), WS-B, WS-C, WS-D, WS-E — todas `default=false`. Si están apagadas, el pipeline es byte-idéntico a pre-007.

---

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

## 5 Workstreams de evaluación (spec 007) — detalle por etapa

```mermaid
flowchart LR
    subgraph WSA["WS-A · SourceQuality<br/>ANTES de AssemblyResult"]
        direction TB
        A1["author_reputation<br/>h-index + domain weights"]
        A2["conflict_of_interest<br/>funder↔author ≥0.7→high"]
        A3["factcheck<br/>Google FactCheck + Wikidata"]
        A4["retraction_watch<br/>CSV cron diario"]
        A5["reproducibilidad<br/>GitHub markers"]
        A6["temporal_decay<br/>freshness configurable"]
    end

    subgraph WSB["WS-B · DataIntelligence<br/>DENTRO de ToolLoop"]
        direction TB
        B1["hybrid_search<br/>BM25 + cosine embed"]
        B2["dedup semántico<br/>umbral configurable"]
        B3["extraction_schema<br/>pydantic × type,domain"]
        B4["authenticity detector<br/>perplexity+burstiness IA"]
        B5["multilingual normalizer<br/>1 LLM call × doc"]
        B6["consensus_dispute map<br/>triangulación+embedding"]
    end

    subgraph WSC["WS-C · DeepAnalysis<br/>DESPUÉS de AssemblyResult"]
        direction TB
        C1["s_curve projection<br/>scipy logistic fit → TRL"]
        C2["meta_analysis<br/>DerSimonian-Laird numpy"]
        C3["implicit assumptions<br/>LLM assumption detection"]
        C4["counterfactual<br/>LLM 3 scenarios"]
        C5["critical dependencies<br/>LLM + KnowledgeGraph"]
    end

    subgraph WSD["WS-D · StrategicSignals<br/>DESPUÉS de DeepAnalysis"]
        direction TB
        D1["convergence clusters<br/>hierarchical clustering"]
        D2["collaboration network<br/>co-author+co-inventor"]
        D3["idea lineage<br/>referenced_works → leaves"]
        D4["narrative shift<br/>VADER + 90d z-score"]
        D5["talent mobility<br/>OpenAlex↔USPTO"]
        D6["patenting gap<br/>papers vs patents density"]
    end

    subgraph WSE["WS-E · Output Assurance<br/>QualityGate al FINAL"]
        direction TB
        E1["1 forensic_trace<br/>JSONB paso a paso"]
        E2["2 bias_audit<br/>geográfico/género/institucional"]
        E3["3 falsification<br/>LLM prober ×conclusion"]
        E4["4 stakeholders<br/>investor/regulator/competitor/academic"]
        E5["5 isotonic calibration<br/>curva empírica golden cases"]
    end
```

## Calibración isotónica

```mermaid
flowchart LR
    GC[golden_case_run<br/>expected vs actual] --> RET[retrain<br/>sklearn IsotonicRegression]
    RET --> CURVE[curva calibrada<br/>DB · activate × model_version]
    CURVE --> CAL[calibrate raw]
    CAL --> OUT["hype_ratio = 1 − calibrado"]
    CAL -.N < 5.-> ID[curva identidad]
```

## Wire-up · opt-in por flag

```mermaid
flowchart TD
    ENV[".env<br/>VT_EVAL_WS_{A,B,C,D,E}_ENABLED<br/>default=false"] --> DI[dependencies.py]
    DI --> BLD["_build_assurance_services (E)<br/>_build_source_quality_services (A)<br/>_build_data_intelligence_services (B)<br/>_build_deep_analysis_services (C)<br/>_build_strategic_signals_services (D)"]
    BLD --> BASE["base.py · concatena Steps<br/>solo si injected≠None"]
    BASE --> PIPELINE["Pipeline<br/>byte-identical a pre-007<br/>cuando flags=false"]
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
