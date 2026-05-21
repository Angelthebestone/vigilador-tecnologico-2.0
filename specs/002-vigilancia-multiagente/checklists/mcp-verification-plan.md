# MCP Verification Plan

**Purpose**: Verificar que todos los proveedores MCP estén instalados, configurados y funcionales.
**Created**: 2026-05-12
**Current state**: Ningún MCP productivo instalado todavía.
**Documentación**: `documentation/` (7 MCPs + serper como REST API)

---

## Estado Actual del Entorno

| Componente | Estado | Notas |
|------------|--------|-------|
| Node.js | ✅ v11.11.0 | Necesario para tavily, exa, brave, firecrawl, jina (npx) |
| npm | ✅ v11.11.0 | Necesario para npx |
| Python 3.11 | ✅ pip 26.1 | Necesario para google-scholar, arxiv |
| uv | ❌ No instalado | Necesario para arxiv-mcp-server (vía `uv tool install`) |
| npm global MCPs | ❌ Solo lucide-icons + fetch | Ninguno de los 7 MCPs del proyecto instalados |
| Python MCP packages | ❌ Ninguno | google-scholar-mcp-server, arxiv-mcp-server no instalados |
| API keys en `.env` | ❌ Solo VT_MCP_DEFAULT_* | Faltan TAVILY, EXA, BRAVE, FIRECRAWL, JINA, SERPER |

---

## Provider Matrix (qué necesita cada uno)

| Provider | Tipo | Instalación | API Key | Tools usadas en el proyecto |
|----------|------|-------------|---------|---------------------------|
| **Tavily** | MCP remoto HTTP | `npx -y tavily-mcp@latest` (env: TAVILY_API_KEY) | ✅ Requerida | tavily-search, tavily-extract |
| **Exa** | MCP remoto HTTP | URL `https://mcp.exa.ai/mcp` + header auth | ✅ Requerida | exa-search, exa-company-search |
| **Jina** | MCP remoto HTTP (Streamable) | URL `https://mcp.jina.ai/v1` + Bearer token | ✅ Requerida | jina-read_url, jina-guess_datetime_url |
| **Brave** | MCP local STDIO/HTTP | `npx -y @brave/brave-search-mcp-server` (env: BRAVE_API_KEY) | ✅ Requerida | brave-web-search, brave-news-search |
| **Firecrawl** | MCP local STDIO | `npx -y firecrawl-mcp` (env: FIRECRAWL_API_KEY) | ✅ Requerida | firecrawl-scrape |
| **Google Scholar** | MCP local STDIO (Python) | `pip install` + `python google_scholar_server.py` | ❌ No requiere (scrapea) | google-scholar-search |
| **ArXiv** | MCP local STDIO (Python) | `uv tool install arxiv-mcp-server` o `pip` | ❌ No requiere | arxiv-search |
| **Serper** | ❌ NO es MCP — REST API | Scripts Python directos (`requests`) | ✅ Requerida | serper-news, serper-patents (via scripts) |

---

## Fases de Verificación

### Fase 1: Runtime Dependencies

- [ ] **Node.js ≥ v20** — verificar `node --version` (actual: v11.11.0 → **necesita upgrade** a v20+ para Brave Search MCP)
- [ ] **uv** — instalar `pip install uv` o `curl ...` (necesario para arxiv-mcp-server)
- [ ] **Python packages base** — `pip install requests` (necesario para serper scripts)

### Fase 2: API Keys en `.env`

Agregar al `.env`:

```env
# === MCP PROVIDERS ===
TAVILY_API_KEY=<your-key>
EXA_API_KEY=<your-key>
JINA_API_KEY=<your-key>
BRAVE_API_KEY=<your-key>
FIRECRAWL_API_KEY=<your-key>
SERPER_API_KEY=<your-key>
```

Nota: Google Scholar y ArXiv no requieren API key.

### Fase 3: Instalación MCP por Provider

#### 3.1 Tavily (MCP remoto HTTP)
- [ ] Verificar: `npx -y tavily-mcp@latest` se ejecuta sin error
- [ ] Opción remota: configurar URL `https://mcp.tavily.com/mcp/?tavilyApiKey=<key>`
- [ ] Tools esperadas: `tavily-search`, `tavily-extract`

#### 3.2 Exa (MCP remoto HTTP)
- [ ] Verificar: conexión a `https://mcp.exa.ai/mcp` responde
- [ ] Opción: `npx -y exa-mcp-server` con env `EXA_API_KEY`
- [ ] Tools esperadas: `web_search_exa`, `web_fetch_exa`, `web_search_advanced_exa`

#### 3.3 Jina (MCP remoto HTTP — Streamable)
- [ ] Verificar: conexión a `https://mcp.jina.ai/v1` responde
- [ ] Header `Authorization: Bearer ${JINA_API_KEY}`
- [ ] Filtrar tools via query params: `?include_tags=search,read`
- [ ] Tools esperadas: `read_url`, `search_web`, `guess_datetime_url`

#### 3.4 Brave (MCP local STDIO vía npx)
- [ ] Instalar: `npx -y @brave/brave-search-mcp-server --transport stdio`
- [ ] Env: `BRAVE_API_KEY`
- [ ] Tools esperadas: `brave_web_search`, `brave_news_search`, `brave_local_search`

#### 3.5 Firecrawl (MCP local STDIO vía npx)
- [ ] Instalar: `npx -y firecrawl-mcp`
- [ ] Env: `FIRECRAWL_API_KEY`
- [ ] Tools esperadas: `firecrawl_scrape`, `firecrawl_search`

#### 3.6 Google Scholar (MCP local STDIO vía Python)
- [ ] Instalar: `pip install mcp scholarly` en virtualenv
- [ ] O clonar: `git clone https://github.com/JackKuo666/google-scholar-MCP-Server.git`
- [ ] Tools esperadas: `search_google_scholar_key_words`, `search_google_scholar_advanced`

#### 3.7 ArXiv (MCP local STDIO vía Python)
- [ ] Instalar: `uv tool install arxiv-mcp-server` o `pip install arxiv-mcp-server`
- [ ] Tools esperadas: `search_papers`, `download_paper`, `read_paper`

### Fase 4: Configuración Serper (REST API, no MCP)

Serper NO tiene MCP. Se usa via REST API con scripts Python.

- [ ] Agregar `SERPER_API_KEY` al `.env`
- [ ] Verificar script `documentation/serper/serper_news.py` — endpoint `https://google.serper.dev/news`
- [ ] Verificar script `documentation/serper/serper_patents.py` — endpoint `https://google.serper.dev/patents`
- [ ] Verificar script `documentation/serper/serper_scholar.py` — endpoint `https://google.serper.dev/scholar`
- [ ] Integrar serper como tool en la aplicación via HTTP directo (no MCP)

### Fase 5: Smoke Tests

Para cada provider MCP instalado:

- [ ] **Connection test**: provider responde a `initialize` request
- [ ] **Tool list test**: provider expone las tools esperadas
- [ ] **Execution test**: tool más simple retorna resultado exitoso
- [ ] **Timeout config**: respeta `VT_MCP_DEFAULT_TIMEOUT_MS` (30000ms)

Para Serper (REST):

- [ ] **HTTP 200**: `POST https://google.serper.dev/news` con API key retorna 200
- [ ] **Batch support**: payload array funciona (actual scripts usan arrays de queries)

### Fase 6: Integración con el Proyecto

- [ ] Actualizar `contracts/mcp-providers.json` con URLs reales (no `example-*.local`)
- [ ] Actualizar `contracts/agent-governance.md` con tools reales de cada MCP
- [ ] Verificar que `dependencies.py` `validate_ready()` incluye todas las tools
- [ ] Verificar `contract_loader.py` skill matrix coincide con providers instalados
- [ ] Ejecutar `python -m pytest -q` — 43 tests deben pasar
- [ ] Probar `GET /api/v2/system-base` devuelve system base sin errores de MCP

---

## Mapeo Tools → Branch (post-serper removal)

| Branch | Tools MCP | Provider |
|--------|-----------|----------|
| **AVANCES** | tavily-search, exa-search, jina-read_url | Tavily, Exa, Jina |
| **COMERCIAL** | exa-company-search, brave-news-search, tavily-extract | Exa, Brave, Tavily |
| **RIESGO** | brave-web-search, firecrawl-scrape, jina-guess_datetime_url | Brave, Firecrawl, Jina |
| **PI_NORMATIVA** | google-scholar-search, arxiv-search, jina-read_url | Google Scholar, ArXiv, Jina |
| **COMPETITIVO** | exa-company-search, brave-news-search, jina-read_url | Exa, Brave, Jina |
| **OPORTUNIDADES** | tavily-search, exa-search, brave-web-search | Tavily, Exa, Brave |

---

## Dependencias entre providers

- **Tavily** + **Exa** + **Jina** + **Brave** + **Firecrawl**: solo necesitan Node.js y API key
- **Google Scholar**: necesita Python + virtualenv + `scholarly` package
- **ArXiv**: necesita Python + `uv` o `pip install arxiv-mcp-server`
- **Serper**: necesita Python + `requests` + API key — NO es MCP

## Prioridad de instalación

1. Tavily, Exa (remotos, más simples)
2. Brave, Firecrawl (npx, requieren API key)
3. Jina (remoto, requiere API key)
4. Google Scholar, ArXiv (Python, sin API key pero más setup)
5. Serper (solo API key + scripts Python)
