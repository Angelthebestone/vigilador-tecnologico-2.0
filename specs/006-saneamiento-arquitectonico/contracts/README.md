# Contratos de Interfaz: Saneamiento Arquitectonico

Este directorio documenta los contratos (interfaces) entre capas definidos
durante el refactor. Los contratos en `domain/ports/` son la unica via de
comunicacion entre capas.

## Mapa de Contratos

```
┌─────────────────────────────────────────────────┐
│                    API Layer                     │
│  (FastAPI routes → delgados, solo validan)       │
├─────────────────────────────────────────────────┤
│                Application Layer                  │
│  ┌───────────────────────────────────────────┐   │
│  │  Use Cases / Services / Agents            │   │
│  │  Dependen SOLO de Protocols (domain/ports/)│   │
│  └──────────────┬────────────────────────────┘   │
│                 │ uses                           │
│  ┌──────────────▼────────────────────────────┐   │
│  │  Pipeline Steps                            │   │
│  │  PipelineStep[T] interface                 │   │
│  └──────────────┬────────────────────────────┘   │
│                 │ implements                     │
│  ┌──────────────▼────────────────────────────┐   │
│  │  ComposePrompt | ToolLoop | Sandbox |      │   │
│  │  AssembleBranchResult                      │   │
│  └───────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│                 Domain Layer                     │
│  ┌───────────────────────────────────────────┐   │
│  │  Protocols (domain/ports/)                 │   │
│  │  LLMClient, EmbeddingGateway,              │   │
│  │  ToolExecutor, VectorIndex,                │   │
│  │  GlobalKnowledgeStore,                     │   │
│  │  SourceTrustStore, EventPublisher          │   │
│  └──────────────┬────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│                 Infra Layer                      │
│  ┌──────────────▼────────────────────────────┐   │
│  │  Adaptadores                              │   │
│  │  Implementan Protocols desde domain/ports/ │   │
│  └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Lista de Contratos

| # | Contrato | Metodo Principal | Implementacion |
|---|----------|-----------------|----------------|
| 1 | `LLMClient` | `generate(messages) -> LLMResponse` | MiniMaxClient |
| 2 | `EmbeddingGateway` | `embed(texts) -> list[vector]` | GeminiEmbeddingGateway |
| 3 | `ToolExecutor` | `execute(name, params) -> ToolResult` | MCPExecutionClient |
| 4 | `VectorIndex` | `search(vector, top_k) -> list[SearchResult]` | PgVectorIndex |
| 5 | `GlobalKnowledgeStore` | `store(snapshot) / get_recent() / merge()` | GlobalKnowledgeRepository |
| 6 | `SourceTrustStore` | `get_trust_score(source) -> float` | SourceTrustRepository |
| 7 | `EventPublisher` | `publish(event) / subscribe(type, handler)` | EventLogDB |
| 8 | `PipelineStep[T]` | `execute(context) -> T` | ComposePrompt, ToolLoop, etc. |

## Reglas de Contrato

1. **Application SOLO depende de Protocols** — nunca de implementaciones
   concretas en infra/.
2. **Cada Protocol tiene una unica responsabilidad** — si un consumidor
   necesita 2 capacidades, recibe 2 Protocols inyectados por separado.
3. **Los DTOs de respuesta** (MCP Response Types) viven en
   `application/mcp/types.py`, no en domain/.
4. **Las excepciones** deben ser tipos definidos en el Protocol o
   excepciones estandar de Python. Sin excepciones de infraestructura
   escapando a capas superiores.
5. **Todos los adaptadores en infra/** deben implementar al menos un
   Protocol y declararlo explicitamente.
