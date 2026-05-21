# Backend Flow — Vigilador Tecnológico 2.0

## Arquitectura General

```mermaid
graph TB
    User["🧑 Usuario"] -->|HTTP| API["FastAPI Gateway"]
    API -->|POST /start| Orchestrator["OrchestratorService"]
    API -->|POST /clarify| Orchestrator
    API -->|POST /approve| Orchestrator
    API -->|GET /stream| SSE["SSE Event Stream"]
    API -->|POST /obsolescence| OD["ObsolescenceDetector"]
    API -->|POST /hype-analysis| HD["HypeDetector"]
    API -->|POST /decision| DA["DecisionAssistant"]
    API -->|GET /ecosystem| Graph

    Orchestrator -->|"Crea plan (MiniMax opcional)"| PlanBuilder["PlanBuilder"]
    Orchestrator -->|Ejecuta ramas| Coordinator["BranchCoordinator"]

    Coordinator -->|Post-ejecución| PL["ParameterLearner"]
    Coordinator -->|Señales cross-branch| Coordinator

    subgraph Agents["6 Agentes (paralelo)"]
        Agent1["AvancesAgent"]
        Agent2["ComercialAgent"]
        Agent3["RiesgoAgent"]
        Agent4["PiNormativaAgent"]
        Agent5["CompetitivoAgent"]
        Agent6["OportunidadesAgent"]
    end

    Coordinator --> Agents
    Agents -->|"SmartRouter elige orden"| MCP["MCPExecutionClient"]
    MCP -->|"Cache transparente"| Cache["MCPSmartCache"]
    Cache --> Tavily
    Cache --> Exa
    Cache --> Jina
    Cache --> Brave
    Cache --> Firecrawl
    Cache --> Scholar
    Cache --> ArXiv
    Cache --> Fetch

    Coordinator -->|Resultados| Fusion["EvidenceLinker + ReportSynthesizer"]
    Fusion -->|SourceScorer| SS["SourceScorer (confianza x dominio)"]
    Fusion --> Graph["KnowledgeGraphService"]
    Fusion --> Report["FinalReport"]
    Graph -->|search_across_sessions| DB[(Postgres)]

    subgraph MCPs["Providers MCP"]
        Tavily["Tavily (search + extract)"]
        Exa["Exa (semantic + company)"]
        Jina["Jina (read + search)"]
        Brave["Brave (web + news)"]
        Firecrawl["Firecrawl (scrape)"]
        Scholar["Google Scholar (papers)"]
        ArXiv["ArXiv (preprints)"]
        Fetch["Fetch (gratis)"]
    end
```

## Flujo de una Investigación (con nuevas features)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant MM as MiniMaxClient
    participant O as Orchestrator
    participant P as PlanBuilder
    participant C as BranchCoordinator
    participant A as Agentes
    participant R as SmartRouter
    participant Cache as MCPSmartCache
    participant M as MCP Providers
    participant F as Fusion
    participant SC as SourceScorer
    participant PL as ParameterLearner
    participant DB as Postgres

    U->>API: POST /research/start
    API->>O: iniciar_sesion(query)
    O->>DB: crear ResearchSession
    Note over O,P: MiniMax opcional: ClarificationService.generate_questions(llm)
    API-->>U: {session_id, questions}

    U->>API: POST /research/{id}/clarify
    API->>O: registrar_respuestas(answers)
    O->>P: build(session_id, answers, llm)
    Note over P: MiniMax genera focus_queries inteligentes. Sin key: templates.
    P-->>O: ResearchPlan (6 ramas)
    O->>DB: guardar plan
    API-->>U: {plan, requires_approval: true}

    U->>API: POST /research/{id}/approve
    O->>C: execute_parallel(plan)
    O->>DB: status = EXECUTING
    API-->>U: {status: "executing"}

    par Ramas en paralelo
        C->>A: AvancesAgent.run()
        A->>R: select(query) → tool_order
        R-->>A: tool_order dinámico
        loop Por cada tool
            A->>Cache: get(tool, query)
            alt Cache hit
                Cache-->>A: resultado cachead
            else Cache miss
                A->>M: ejecutar tool
                M-->>A: resultado
                A->>Cache: set(tool, query, result)
            end
            A-->>C: señal cross-branch si aplica
        end
        A-->>C: BranchResult + señales
        C->>PL: record_outcome(branch, params, success)
    and
        C->>A: ComercialAgent.run()
        A->>R: select(query)
        A->>M: tool dinámico
        M-->>A: resultado
        A-->>C: BranchResult
    and
        C->>A: RiesgoAgent.run()
        A->>M: tool dinámico
        M-->>A: resultado
        A-->>C: BranchResult
    and
        C->>A: PiNormativaAgent.run()
        A->>M: tool dinámico
        M-->>A: resultado
        A-->>C: BranchResult
    and
        C->>A: CompetitivoAgent.run()
        A->>M: tool dinámico
        M-->>A: resultado
        A-->>C: BranchResult
    and
        C->>A: OportunidadesAgent.run()
        A->>M: tool dinámico
        M-->>A: resultado
        A-->>C: BranchResult
    end

    C->>C: _process_cross_signals()
    C->>F: fusionar resultados
    F->>SC: score(url) por fuente
    SC-->>F: confidence por dominio
    F->>F: report_synthesizer con MiniMax opcional
    F->>DB: guardar FinalReport + KnowledgeGraph
    O->>DB: status = COMPLETED
    U->>API: GET /research/{id}/report
    API-->>U: FinalReport
```

## Nuevos Endpoints de Inteligencia

```mermaid
graph LR
    subgraph Endpoints["Nuevos endpoints Phase 9"]
        E1["POST /research/{id}/obsolescence?tech=..."]
        E2["POST /research/{id}/hype-analysis?tech=..."]
        E3["POST /research/{id}/decision?question=..."]
    E4["GET /research/{id}/graph/ecosystem?seed=...&depth=..."]
    E5["GET /research/{id}/graph/search-cross-session?query=..."]

    subgraph Servicios
        S1["ObsolescenceDetector\n+ brave_news + exa"]
        S2["HypeDetector\n+ arxiv + exa + firecrawl"]
        S3["DecisionAssistant\n+ branch_results heuristic"]
        S4["discover_ecosystem()"]
        S5["search_across_sessions()"]
    end

    E1 --> S1
    E2 --> S2
    E3 --> S3
    E4 --> S4
    E5 --> S5
```

## Internal Architecture (con nuevas clases)

```mermaid
classDiagram
    class BaseBranchAgent {
        +branch_type: BranchType
        +run(session, branch_config, depth) : AgentRunOutput
        +signal_branch(target, payload)
        #_resolve_providers()
    }

    class PromptComposer {
        +compose(system_base, overlay, query, config, policy) : ComposedPrompt
        +agrega Tool Usage Guide desde prompts/tools/
    }

    class SmartToolRouter {
        +classify(query) : str
        +select(query) : tuple~str~
        QUERY_TYPES: academic | company | patent | news | deep_research
    }

    class MCPSmartCache {
        +get(tool, query) : dict | None
        +set(tool, query, data, ttl)
        TTL: 1h tavily, 1h exa, 24h jina, etc.
    }

    class SourceScorer {
        +score(url) : float
        -DOMAIN_SCORES: 45+ dominios
    }

    class ParameterLearner {
        +record_outcome(branch, params, success, coverage)
        +suggest(branch) : dict
    }

    class MCPExecutionClient {
        +execute_tool(provider, tool, args) : ToolExecutionResult
        +usa MCPSmartCache como wrapper transparente
    }

    class KnowledgeGraphService {
        +search_across_sessions(query, vector) : list
        +discover_ecosystem(seed, graph, depth) : dict
    }

    class ObsolescenceDetector {
        +analyze(tech) : ObsolescenceSignal
    }

    class HypeDetector {
        +analyze(tech) : HypeReport
    }

    class DecisionAssistant {
        +analyze(question) : DecisionReport
    }

    class MiniMaxClient {
        +complete(messages, tools) : MiniMaxResponse
        +roles: system, user_system, sample_message_*
        +name field para distinguir roles
    }

    BaseBranchAgent --> SmartToolRouter : elige orden dinámico
    BaseBranchAgent --> PromptComposer : compone prompt
    BaseBranchAgent --> MCPExecutionClient : ejecuta tools
    MCPExecutionClient --> MCPSmartCache : cache transparente
    KnowledgeGraphService --> MCPSmartCache : usa en discover

    AvancesAgent --|> BaseBranchAgent
    ComercialAgent --|> BaseBranchAgent
    RiesgoAgent --|> BaseBranchAgent
    PiNormativaAgent --|> BaseBranchAgent
    CompetitivoAgent --|> BaseBranchAgent
    OportunidadesAgent --|> BaseBranchAgent
```

## Composición de Prompts (System Base + Tool Usage)

```mermaid
flowchart LR
    SBase["SystemBase\nsystem-base.md\nreglas globales"] --> Compose
    Overlay["BranchOverlay\nobjetivo + do/dont\ncontexto del dominio"] --> Compose
    Skill["AgentSkillPolicy\ntool order + timeout\nretry + fallback"] --> Compose
    Query["user_query\nconsulta original"] --> Compose
    Tools["Tool Usage Guides\n(src/prompts/tools/*.txt)\nparámetros reales de cada tool"] --> Compose
    MiniMax["MiniMax Roles\nsystem + user_system\nsample_message_user/ai"] --> Compose

    Compose["PromptComposer.compose()"] --> Result["ComposedPrompt\ncon 10+ secciones"]
    Result --> MCP["Se envía como\ncomposed_prompt en\npayload de MCP tools"]
```

## Mapeo Ramas → MCPs (con Fetch)

```mermaid
graph LR
    subgraph Branches
        A[Avances]
        C[Comercial]
        R[Riesgo]
        P[PI_Normativa]
        K[Competitivo]
        O[Oportunidades]
    end

    subgraph Providers
        T[Tavily]
        E[Exa]
        J[Jina]
        B[Brave]
        FC[Firecrawl]
        GS[Google Scholar]
        AX[ArXiv]
        FET[Fetch]
    end

    A --> T & E & J & FET
    C --> E & B & T & FET
    R --> B & FC & J & FET
    P --> GS & AX & J & FET
    K --> E & B & J & FET
    O --> T & E & B & FET
```

## Flujo de Datos por Rama (con SmartRouter + Cache)

```mermaid
flowchart TB
    subgraph Rama["Cada rama ejecuta:"]
        direction TB
        Q["focus_query[0]"] --> Router["SmartToolRouter.select()"]
        Router -->|"academic"| MCP1["search_papers"]
        Router -->|"company"| MCP1["web_search_advanced_exa"]
        Router -->|"general"| MCP1["tool_order por defecto"]

        MCP1 -->|cache hit| Payload["ToolExecutionResult"]
        MCP1 -->|cache miss| Tool1["Ejecutar tool #1"]
        Tool1 -->|"éxito"| Store1["MCPSmartCache.set()"]
        Store1 --> Payload
        Tool1 -->|"falla"| MCP2["Tool #2 (fallback)"]

        MCP2 -->|cache hit| Payload
        MCP2 -->|cache miss| Tool2
        Tool2 -->|"éxito"| Store2
        Store2 --> Payload
        Tool2 -->|"falla"| MCP3["Tool #3 (fallback)"]

        MCP3 -->|cache hit| Payload
        MCP3 -->|cache miss| Tool3
        Tool3 -->|"éxito"| Store3
        Store3 --> Payload
        Tool3 -->|"falla"| FAIL["FAILED branch"]

        Payload --> Iteration["run_followup_loop()"]
        Iteration -->|needs_follow_up| Q2["next_query"]
        Q2 --> Router
        Iteration -->|depth_limit| Done["Iteraciones completadas"]
    end

    Done --> Signal["signal_branch() cross-branch"]
    Signal --> PL["ParameterLearner.record_outcome()"]
    PL -->["_process_cross_signals()\nre-ejecuta agent.run()\ncon depth_limit=2"]
    PL --> Embed["Gemini Embedding 2\nembedding vectors por iteración"]
    Embed --> Relations["build_relations()\nsemantic dedup + support"]
    Relations --> Result["BranchResult\nfindings + sources + errores\n+ SourceRef.confidence aplicado"]
```

## Archivos Clave

| Capa | Archivos |
|------|---------|
| **API** | `api/app.py`, `api/router.py`, `api/routes/research_*.py`, `api/routes/system_base.py` |
| **Agentes** | `application/agents/base.py`, `application/agents/*_agent.py` |
| **Gobernanza** | `application/governance/contract_loader.py`, `application/governance/prompt_composer.py`, `application/governance/system_base_loader.py`, `application/governance/validators.py`, `application/governance/smart_router.py` |
| **MCP** | `infra/mcp/provider_registry.py`, `infra/mcp/execution_client.py`, `infra/mcp/mcp_cache.py` |
| **MiniMax** | `infra/llm/minimax_client.py`, `domain/system_base.py` (MiniMaxMessage) |
| **Orquestación** | `application/orchestration/orchestrator_service.py`, `application/execution/branch_coordinator.py` |
| **Gráfo** | `application/graph/knowledge_graph_service.py`, `infra/persistence/vector_index.py` |
| **Fusión** | `application/fusion/evidence_linker.py`, `application/fusion/report_synthesizer.py`, `application/fusion/decision_assistant.py` |
| **Evaluación** | `application/evaluation/source_scorer.py`, `application/evaluation/parameter_learner.py`, `application/evaluation/obsolescence_detector.py`, `application/evaluation/hype_detector.py` |
| **Prompts** | `prompts/orchestration/*.txt`, `prompts/branches/*.txt`, `prompts/tools/*.txt`, `prompts/minimax_examples/*.txt` |
| **Serper** | `infra/serper/serper_client.py` (REST API, no MCP) |
| **Config** | `config/settings.py` |
| **Tests** | `tests/test_*.py` **(59 tests)** |
