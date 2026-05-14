# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -e ".[dev]"
```

**Run dev server:**
```bash
uvicorn vigilancia_multiagente.api.app:app --reload --host 0.0.0.0 --port 8000
```

**Run with Docker Compose (app + PostgreSQL):**
```bash
docker-compose up --build
```

**Run all tests:**
```bash
pytest
```

**Run a single test file:**
```bash
pytest tests/test_orchestrator.py -v
```

**Lint and format:**
```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

### Layers
- **API** (`api/`): FastAPI routes, dependency injection (`dependencies.py` wires ~47 services), security guards
- **Application** (`application/`): Orchestration, agents, governance, planning, fusion, graph, evaluation
- **Domain** (`domain/`): Core entities, repository protocols, session state machine, governance contracts
- **Infrastructure** (`infra/`): DB, MCP execution, LLM (MiniMax), embeddings (Gemini), vector index (pgvector), Serper REST

### Research Workflow
```
Clarify → Plan → Approve → Execute (6 parallel branches) → Fuse → Report
```
Managed by `OrchestratorService` (session lifecycle) + `BranchCoordinator` (parallel `asyncio.gather()`).

### Six Branch Agents
`AVANCES`, `COMERCIAL`, `RIESGO`, `PI_NORMATIVA`, `COMPETITIVO`, `OPORTUNIDADES` — each in `application/agents/<branch>_agent.py`, inheriting `BaseBranchAgent`.

### Governance Contracts
- **SystemBase** (`domain/system_base.py`): Frozen global rules (tool policy, safety limits, output style). Single source of truth.
- **BranchOverlay**: Domain-specific extensions layered on SystemBase. Must NOT redefine SystemBase fields.
- **PromptComposer** (`application/governance/prompt_composer.py`): Composes SystemBase + BranchOverlay + user query → `ComposedPrompt`.
- **AgentSkillPolicy** (`application/governance/contract_loader.py`): Per-branch tool order, timeouts, retry limits.

### MCP Integration
`infra/mcp/mcp-providers.json` defines 10 providers (tavily, exa, jina, brave, firecrawl, google_scholar, arxiv, fetch, serper). `MCPProviderRegistry` loads them at startup; `MCPExecutionClient` executes tools via STDIO or HTTP with caching (`mcp_cache.py`).

### Configuration
Pydantic Settings with prefix `VT_`. Copy `.env.example` to `.env`. Key variables:
- `VT_MINIMAX_API_KEY` — primary LLM
- `VT_EMBEDDING_API_KEY` — Gemini embeddings
- `VT_DATABASE_URL` — PostgreSQL+asyncpg (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/vigilancia`)
- Per-provider API keys: `VT_TAVILY_API_KEY`, `VT_EXA_API_KEY`, `VT_JINA_API_KEY`, `VT_BRAVE_API_KEY`, `VT_FIRECRAWL_API_KEY`, `VT_SERPER_API_KEY`

### Key Files
| File | Role |
|------|------|
| `api/dependencies.py` | Full dependency injection graph |
| `application/orchestration/orchestrator_service.py` | Session lifecycle |
| `application/execution/branch_coordinator.py` | Parallel branch execution |
| `application/agents/base.py` | BaseBranchAgent |
| `application/governance/contract_loader.py` | AgentSkillPolicy per branch |
| `application/governance/prompt_composer.py` | SystemBase + Overlay composition |
| `application/graph/knowledge_graph_service.py` | NetworkX graph analytics |
| `infra/mcp/mcp-providers.json` | MCP provider manifest |
| `infra/mcp/execution_client.py` | Tool execution engine |
| `domain/session_state.py` | SessionStatus transitions |
| `config/settings.py` | All env-backed settings |

### Environment Constraints
- **No leer `.env`**: el archivo `.env` real no está disponible en este repositorio. Usar solo `.env.example` como referencia de variables disponibles.
- **`VT_MINIMAX_API_KEY` no está configurada**: el sistema no tiene clave MiniMax activa. Por eso muchos bloques relacionados con MiniMax en `infra/llm/minimax_client.py` y en la configuración tienen cuerpos vacíos (`pass`) o retornan valores por defecto. No intentar corregirlos como si fueran bugs — es comportamiento intencional dado que la integración está incompleta.

### Testing Patterns
- `tests/conftest.py` provides in-memory repositories (`MemorySessionRepository`) and a `FakeDatabase` stack — use these for unit tests that must not hit PostgreSQL.
- MCP connectivity tests (`test_mcp_connectivity.py`) require real API keys and network; skip in offline environments.
- Ruff line-length: 100 chars, target Python 3.11.
