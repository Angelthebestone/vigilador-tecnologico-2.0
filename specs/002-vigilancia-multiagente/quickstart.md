# Quickstart: Vigilancia Tecnologica Multiagente

## 1. Prerequisites

- **Docker Desktop** (para PostgreSQL + pgvector)
- **Node.js 20+** (para MCPs STDIO: Brave, Firecrawl)
- **Python 3.11+** (para MCPs Python: Fetch, Google Scholar, ArXiv)
- API keys configuradas en `.env`: Tavily, Exa, Jina, Brave, Firecrawl, Serper, Gemini
- MiniMax key solo si quieres activar razonamiento adicional (opcional)

## 2. Infrastructure Setup

### PostgreSQL + pgvector (Docker)

```bash
docker run -d --name pgvector -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=vigilancia \
  pgvector/pgvector:pg18
```

### MCP Providers (global install)

```bash
# HTTP (sin instalacion local)
# Tavily, Exa, Jina, Serper — se conectan por HTTPS

# STDIO via npm
npm install -g @brave/brave-search-mcp-server
npm install -g firecrawl-mcp

# STDIO via pip
pip install mcp-server-fetch
pip install arxiv-mcp-server

# Google Scholar — extraer zip en .mcp-servers/
pip install -r .mcp-servers/google-scholar/Google-Scholar-MCP-Server-main/requirements.txt
```

## 3. Configure environment

Copiar `.env.example` a `.env` y completar:

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `VT_TAVILY_API_KEY` | ✅ | Búsqueda web |
| `VT_EXA_API_KEY` | ✅ | Búsqueda semántica |
| `VT_JINA_API_KEY` | ✅ | Extracción de contenido |
| `VT_BRAVE_API_KEY` | ✅ | Noticias y web |
| `VT_FIRECRAWL_API_KEY` | ✅ | Scraping JS-heavy |
| `VT_SERPER_API_KEY` | ✅ | Patentes y búsqueda |
| `VT_EMBEDDING_API_KEY` | ✅ | Embeddings Gemini |
| `VT_MINIMAX_API_KEY` | ❌ | Opcional (sin fallback) |
| `VT_DATABASE_URL` | ✅ `postgresql+asyncpg://postgres:Angeld09@localhost:5432/vigilancia` |

## 4. Run migrations

```bash
# Las migrations se aplican automaticamente al iniciar la API
# O manualmente:
docker exec -i pgvector psql -U postgres -d vigilancia < src/.../migrations/001_init.sql
docker exec -i pgvector psql -U postgres -d vigilancia < src/.../migrations/002_graph_analytics.sql
```

## 5. Run lifecycle

```bash
# Iniciar API
uvicorn vigilancia_multiagente.api.app:app --reload

# Flujo de investigacion:
# 1. POST /api/v2/research — iniciar sesion con user_query
# 2. POST /api/v2/research/{id}/clarify — responder clarificaciones
# 3. POST /api/v2/research/{id}/plan — obtener plan de ramas
# 4. POST /api/v2/research/{id}/approve — aprobar y ejecutar
# 5. GET  /api/v2/research/{id}/events?stream=true — SSE en vivo
# 6. GET  /api/v2/research/{id}/report — reporte final
# 7. GET  /api/v2/research/{id}/graph — grafo de conocimiento
```

## 6. MCP Provider Status

| Provider | Transport | API Key | Status |
|----------|-----------|---------|--------|
| Tavily | HTTP | ✅ | Verificado |
| Exa | HTTP | ✅ | Verificado |
| Jina | HTTP | ✅ | Verificado |
| Brave | STDIO (npx) | ✅ | Instalado |
| Firecrawl | STDIO (npx) | ✅ | Instalado |
| Serper | HTTP | ✅ | Verificado |
| Google Scholar | STDIO (python) | No requiere | Integrado |
| ArXiv | STDIO (pip) | No requiere | Instalado |
| Fetch | STDIO (pip) | No requiere | Instalado |
| Gemini Embedding | HTTP | ✅ | Verificado |
| MiniMax | HTTP | ❌ | Bloqueado |

## 7. Prompt Architecture

Los 21 archivos de prompt usan estructura HTML semantica:

```
src/vigilancia_multiagente/prompts/
├── branches/        # 6 prompts de rama (avances, comercial, riesgo, etc.)
├── orchestration/   # 3 prompts (clarify, planning, synthesis)
├── tools/           # 8 prompts de herramientas (tavily, exa, jina, etc.)
└── minimax_examples/ # 4 prompts (system, user_system, sample_*)
```

## 8. System Base Pipeline

El sistema compone prompts en runtime a partir de tres capas:

1. **System Base** (`contracts/system-base.md`) — reglas globales
2. **Branch Overlay** — instrucciones especificas por rama
3. **User Query** — consulta original

La composicion usa `PromptComposer.compose()` y el resultado se entrega al agente via tool execution.

## 9. Validation checklist

- [ ] `GET /health` devuelve `status: ok`, `ready: true`
- [ ] Postgres accesible (`research_sessions`, `embedding_vectors`, etc.)
- [ ] Embeddings Gemini responden (HTTP 200)
- [ ] Al menos 3 MCP providers responden
- [ ] 59+ tests unitarios pasan
- [ ] Ruff 0 issues
- [ ] `.env` no esta en git
- [ ] `.mcp-servers/` en `.gitignore`
