# Plan: Extracción del Toolkit Empresarial v3.0 — COMPLETO

> **Fuentes:** Hermes Agent | OpenClaw | Awesome MCP (~7,260 servidores en 2 READMEs) | Vigilador 2.0
> **Objetivo:** Convertir Vigilador 2.0 en LLM empresarial multi-propósito. Vigilancia tecnológica = un módulo más (deep research).

---

## I. HERRAMIENTAS DE HERMES AGENT (12 extracciones)

| # | Herramienta | Archivo Fuente | Propuesta v3.0 |
|---|------------|---------------|----------------|
| 1 | **Delegación Multi-Agente** | `tools/delegate_tool.py`, `agent/tool_executor.py` | `AgentOrchestrator` generalizado (spawn any agent type) |
| 2 | **Tool Registry + Auto-Descubrimiento** | `tools/registry.py`, `toolsets.py`, `model_tools.py` | Reemplazar `MCPProviderRegistry` con registry unificado Python+MCP |
| 3 | **Compresión de Contexto** | `agent/context_compressor.py` | Pipeline de síntesis pre-reportes largos |
| 4 | **Memory Providers (8 backends)** | `agent/memory_provider.py`, `plugins/memory/` | Reemplazar `CrossSessionService` (pgvector + mem0 + honcho) |
| 5 | **Gateway Multi-Canal (22+)** | `gateway/run.py`, `gateway/platforms/` | API OpenAI-compatible + Slack + Teams + Email |
| 6 | **Cron Scheduler** | `cron/scheduler.py`, `cron/jobs.py` | Alertas automáticas + reportes periódicos |
| 7 | **Kanban Work Queue** | `plugins/kanban/` | Dashboard empresarial de tareas de investigación |
| 8 | **Curator (Auto-Skills)** | `agent/curator.py` | Auto-gestión de prompts y skills empresariales |
| 9 | **Checkpoints (Git Snapshots)** | `tools/checkpoint_manager.py` | Versionado de reportes + rollback |
| 10 | **Provider Abstraction (13+ LLMs)** | `providers/base.py`, `agent/auxiliary_client.py` | Multi-provider: Claude, GPT-4o, Gemini, DeepSeek, Grok |
| 11 | **Skill System (Progressive Disclosure)** | `skills/`, `agent/skill_commands.py` | Reemplazar `prompts/*.txt` con SKILL.md estandarizado |
| 12 | **TUI Embebida** | `ui-tui/`, `tui_gateway/` | Chat empresarial con xterm.js + WebSocket |

---

## II. HERRAMIENTAS DE OPENCLAW (4 patrones)

- **Gateway Protocol** — versionado aditivo, prompt cache determinístico
- **Plugin SDK** — boundary enforcement plugins↔core solo vía SDK
- **Security** — secrets en `~/.openclaw/credentials/`, nunca en repo
- **Testing** — Vitest colocado, behavior tests sobre string greps

---

## III. MCP SERVERS — CATÁLOGO COMPLETO POR CATEGORÍA EMPRESARIAL

### A. SEARCH & RETRIEVAL (7 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Brave Search | `thomasvan/mcp-brave-search` | Búsqueda web + noticias, sin dependencia Google |
| Tavily Search | (ya integrado) | Búsqueda optimizada para AI agents |
| Exa/Metaphor | (ya integrado) | Búsqueda semántica empresarial |
| Serper | `pskill9/web-search` | Google Search sin API key, 13 tools |
| Jina Reader | (ya integrado) | Conversión URL→Markdown |
| FireCrawl | (ya integrado) | Scraping empresarial, batch 10k URLs |
| Context7 | — | Documentación actualizada de librerías (anti-alucinación) |

### B. DATABASES (20+ servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| PostgreSQL | `modelcontextprotocol/server-postgres` | RDBMS canónico, ya integrado vía pgvector |
| Snowflake | `Snowflake-Labs/mcp` | Data warehouse. RBAC, Cortex Agents, semantic views |
| Neo4j | `neo4j-contrib/mcp-neo4j` | Grafo de conocimiento persistente (reemplaza NetworkX RAM) |
| SQLAlchemy Universal | `runekaagaard/mcp-alchemy` | Multi-DB: PostgreSQL, MySQL, Oracle, MSSQL, SQLite, MariaDB |
| BigQuery | `LucasHild/mcp-server-bigquery` | Analytics warehouse |
| MongoDB Lens | `furey/mongodb-lens` | NoSQL document store |
| Elasticsearch | `cr7258/elasticsearch-mcp-server` | Search/index analytics |
| ClickHouse | `ClickHouse/mcp-clickhouse` | Real-time analytics DB |
| Redis | `redis/mcp-redis` | Caching/real-time data layer |
| MS SQL Server | `cwilby/mcp-node-mssql` | Microsoft enterprise stack |
| Confluent Kafka | `confluentinc/mcp-confluent` | Event streaming/data pipelines |
| Oracle/Universal | `runekaagaard/mcp-alchemy` | Oracle + multi-DB |
| PlanetScale | — | Serverless MySQL branching |
| Weaviate | `weaviate/mcp-server-weaviate` | Vector DB para RAG |
| Supabase | `supabase-community/supabase-mcp` | Backend-as-a-service |
| Couchbase | — | Multi-model NoSQL |
| Chroma | `chroma-core/chroma-mcp` | Vector embedding store |
| Trino | `Dataring-engineering/mcp-server-trino` | Federated query engine |
| DuckDB | `mustafahasankhan/duckdb-mcp-server` | In-process OLAP, embedded analytics |
| Teradata | `arturborycki/mcp-teradata` | Enterprise data warehouse |
| Altibase | `hesslee/mcp-server-altibase` | In-memory DB BI |

### C. CODE EXECUTION + SANDBOXES (27 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| E2B Sandbox | `asif-nvc/e2b-sandbox-mcp` | 29 tools, cloud sandboxes Linux VM, isolated |
| Dagger Container-Use | `dagger/container-use` | Multi-agent isolated containers + git branches |
| YepCode | `yepcode/mcp-server-js` | Serverless sandbox, JS/Python, full NPM/PyPI |
| Capsule (WASM) | `mavdol/capsule` | Rust WASM sandboxes Python/JS, near-native |
| Piston | `alvii147/piston-mcp` | Remote polyglot code execution (any language) |
| Docker Code Interpreter | `svngoku/mcp-docker-code-interpreter` | Docker isolated containers |
| MATLAB | `HanSur94/matlab-mcp-server-python` | Engineering/scientific computing + Plotly |
| Mathematica | `texra-ai/mcp-server-mathematica` | Symbolic math verification |
| Safe Local Python | `maxim-saplin/mcp_safe_local_python_executor` | HF Smolagents-based safe execution |
| Python Sandbox + SSE | `cloudywu0410/python_sandbox_mcp_server` | Docker + SSE streaming |
| Isolator MCP | `Ompragash/isolator-mcp` | Python, Go, JS in Docker |
| Prolog Reasoner | `rikarazome/prolog-reasoner` | SWI-Prolog logic programming 90% accuracy |
| Edict | `Sowiedu/Edict` | Agent-first PL, JSON AST → WASM via Z3/SMT |
| Node Code Sandbox | `alfonsograziano/node-code-sandbox-mcp` | JS Docker sandboxes + npm on-the-fly |
| pkgx MCP | `pkgxdev/mcp` | Execute any OSS tool via pkgx sandbox |
| PRIMS | `hileamlakB/PRIMS` | Python Runtime Interpreter isolated |
| Frostbyte | `OzorOwn/frostbyte-mcp` | 20+ languages, 13 tools |
| Jupyter MCP Server | `datalayer/jupyter-mcp-server` | Jupyter notebook AI integration |
| Jupyter Notebook MCP | `jjsantos01/jupyter-notebook-mcp` | Claude → Jupyter control |
| JupyterCAD MCP | `asmith26/jupytercad-mcp` | CAD dentro de Jupyter |
| Kaggle MCP | `arrismo/kaggle-mcp` | Dataset download + analysis |
| Fermat MCP | `abhiphile/fermat-mcp` | SymPy + NumPy + Matplotlib unificados |
| NetworkX MCP | `Bright-L01/networkx-mcp-server` | Graph analysis: centrality, PageRank, community |
| R MCP | `phisanti/MCPR` | Interactive R sessions via AI |
| MCP Compress | `ShipItAndPray/mcp-compress` | 7 compression tools: gzip, brotli, deflate, TurboQuant |
| MCP TurboQuant | `ShipItAndPray/mcp-turboquant` | LLM quantization → GGUF, GPTQ, AWQ |
| MATLAB Executor | `JSFrouws/mcp-matlab-executor` | MATLAB seguro con approval prompts |

### D. COMPUTER USE + DESKTOP AUTOMATION (20 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Touchpoint | `Touchpoint-Labs/touchpoint` | "Playwright for entire OS" — cualquier desktop app |
| Terminator MCP Agent | `mediar-ai/terminator` | Accessibility APIs: Windows, macOS, Linux, workflow recording |
| ScreenPilot | `Mtehabsim/ScreenPilot` | Mouse/keyboard control para desktop automation |
| ScreenPipe | `mediar-ai/screenpipe` | 24/7 screen+audio recording, SQL/embedding search |
| ContextPulse | `ContextPulse/contextpulse` | Screen (OCR), voice (Whisper), keyboard/mouse, clipboard — 35 tools |
| DesktopCommanderMCP | `wonderwhy-er/DesktopCommanderMCP` | Swiss-army-knife: ejecutar programas, leer/escribir/editar código |
| Computer Control MCP | `AB498/computer-control-mcp` | Mouse, keyboard, OCR via PyAutoGUI + RapidOCR |
| macOS Use MCP | `mediar-ai/mcp-server-macos-use` | macOS app control via accessibility APIs |
| Wayland MCP | `someaka/wayland-mcp` | Linux Wayland: screenshot, input control |
| Clipboard MCP | `mnardit/clipboard-mcp` | Cross-platform clipboard (read, write, watch) |
| Terminal MCP | `aybelatchane/mcp-server-terminal` | "Playwright for terminals" — TUI/CLI State Tree |
| Console Automation | `ooples/mcp-console-automation` | 40 tools: sessions, SSH, testing, monitoring, background jobs |
| iTerm MCP | `ferrislucas/iterm-mcp` | macOS iTerm: run commands, ask about terminal content |
| PTY MCP | `raychao-oao/pty-mcp` | Interactive PTY sessions, SSH, serial ports |
| Mac Apps Launcher | `joshuarileydev/mac-apps-launcher-mcp-server` | List + launch macOS apps |
| Local MCP (macOS) | `lanchuske/local-mcp` | 82 tools: Mail, Calendar, Contacts, Reminders, Notes, iMessage, Finder, Safari, OmniFocus, Teams, Outlook, OneDrive, Office |
| Homebrew MCP | `jeannier/homebrew-mcp` | macOS package management |
| Arch Linux MCP | `nihalxkumar/arch-mcp` | Arch Wiki, AUR, repos |
| Kali Linux MCP | `Stoicmehedi/K-MCP` | AI-driven penetration testing |
| Android Device Control | `us-all/android-mcp-server` | 76 ADB tools: device, apps, UI, logcat, emulator, files, debug |

### E. APP-SPECIFIC: EXCEL, POWER BI, GOOGLE SHEETS, OFFICE (20 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Excel MCP Server | `sbroenne/mcp-server-excel` | 173 operaciones: Power Query, DAX, VBA, PivotTables, Charts. 100% Excel |
| Office Editor MCP | `theWDY/office-editor-mcp` | Word, Excel, PowerPoint creación/edición |
| Power BI Analyst | `mbrummerstedt/powerbi-analyst-mcp` | Semantic models, DAX queries, browse workspaces |
| Tableau (Twilize) | `subhatta123/twilize` | 47 tools: .twb/.twbx generation, charts, dashboards, CSV→dashboard |
| Google Workspace MCP | `taylorwilsdon/google_workspace_mcp` | Calendar, Drive, Gmail, Docs, Forms, Chats, Slides, Sheets |
| Google Drive + Workspace | `us-all/google-drive-mcp-server` | 98 tools: Docs, Sheets, Slides, Shared Drives, Approvals |
| Google Sheets MCP | `xing5/mcp-google-sheets` | Spreadsheet automation |
| MS 365 MCP Server | `softeria/ms-365-mcp-server` | Full M365 Graph API: Outlook, Excel, Calendar, files |
| GWS MCP Server | `conorbronsdon/gws-mcp-server` | 23 tools: Drive, Sheets, Calendar, Docs, Gmail |
| Keynote MCP | `ByAxe/keynote-mcp` | Apple Keynote: 30+ tools, AppleScript |
| Alai MCP | `getalai/alai-mcp-server` | AI presentations → PDF, PPTX, shareable link |
| Vizro MCP (McKinsey) | `mckinsey/vizro` | Data charts + dashboards validados |
| XLSM MCP Server | `orlando2019/xlsm-mcp-server` | Excel macro-enabled workbook automation |
| Excel MCP Server (variablenigh) | `variablenigh/excel-mcp-server` | Excel read/write via MCP |
| Bilig WorkPaper | `proompteng/bilig` | Headless spreadsheet: formula readback, input edits, JSON |
| Metabase MCP | `cheukyin175/metabase-mcp` | BI analytics via AI assistants |
| Metabase MCP (1luvc0d3) | `1luvc0d3/metabase-mcp` | 28 tools: NL data analysis, dashboards, SQL, guardrails |
| Superset MCP | `bintocher/mcp-superset` | 135+ tools: dashboards, charts, SQL Lab, security |
| UnMarkdown MCP | `UnMarkdown/mcp-server` | Markdown→Google Docs, Word, Slack, OneNote, Email, 62 templates |
| Google Drive MCP | `isaacphi/mcp-gdrive` | Google Drive + Sheets editing |

### F. FINANCE, ACCOUNTING, BANKING (50+ servers)

**CORE ENTERPRISE:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Xendit | `mrslbt/xendit-mcp` | SEA payments: invoices, disbursements, bank transfers (ID, PH, TH, VN, MY) |
| Mercado Pago | `dan1d/cobroya` | LATAM payments: links, search, refunds |
| Frihet | `frihet/mcp-server` | AI-native SMB: invoices, expenses, clients, products, quotes (31 tools) |
| HLedger MCP | `iiatlas/hledger-mcp` | Double-entry plain text accounting with AI |
| Chargebee | `chargebee/mcp` | Subscription billing + revenue management |
| AgentPay | `joepangallo/mcp-server-agentpay` | Payment gateway AI agents: Stripe + x402 USDC |
| Alpha Vantage | `berlinbra/alpha-vantage-mcp` | Stock + crypto data feeds |
| EquiVault | `equivault/equivault-mcp` | 38 tools: fundamentals, financial statements, ratios, screening, insider transactions |
| Financial Data Net | `financialdatanet/mcp-server` | EOD/intraday stocks, financial statements, insider/institutional data, earnings |
| DebtStack | `debtstack-ai/debtstack-python` | Corporate debt: 250+ issuers, 5,000+ bonds, leverage ratios, covenants, FINRA TRACE |
| FinMap | `finmap-org/mcp-server` | Historical data: US, UK, Russian, Turkish exchanges |
| Axiom Calculator | `vdalhambra/axiom-calculator-mcp` | Personal finance: mortgage, compound interest, FIRE, debt payoff |
| Copilot Money MCP | `ignaciohermosillacornejo/copilot-money-mcp` | 30 tools: transactions, budgets, accounts, investments |
| Personal Finance MCP | `JosueM1109/personal-finance-mcp` | Plaid-based: banks, credit cards, loans, brokerages |
| CalcNook | `Declan142/calcnook-mcp-server` | 7 countries + Islamic finance (Zakat, Murabaha, Ijarah, Mudarabah) |
| Monarch Money | `carsol/monarch-mcp-server` | Read-only: transactions, budgets, accounts, cashflow + MFA |
| Firma | `evan-moon/firma` | Portfolio tracker for overseas stock investors (Finnhub) |
| MetaTrader 5 MCP | `ariadng/metatrader-mcp-server` | Automated forex/CFD trading via MT5 |
| Kite MCP | `aranjan/kite-mcp` | Indian stocks: Zerodha Kite, 14 tools (holdings, orders, GTT) |
| Korean Stock MCP | `jjlabsio/korea-stock-mcp` | OPEN DART + KRX API |
| Vietnam Stock MCP | `cuthongthai-vn/vimo-mcp-server` | 35 tools: real-time SSI, technical analysis, financial statements, AI picks |
| China A-Share (Baostock) | `HuggingAGI/mcp-baostock-server` | Chinese stock market data |
| Stooq MCP | `hoqqun/stooq-mcp` | Global real-time prices: US, Japan, UK, Germany, no API key |
| Argentine Dolar MCP | `dan1d/dolar-mcp` | Blue, oficial, MEP, CCL, crypto, tarjeta rates |
| Czech NB FX Rates | `czagents/cnb` | ČNB daily CZK exchange rates |
| CBR Rates | `atomno-labs/mcp-cbr-rates` | Russian Central Bank: FX, key rate, inflation |
| DART MCP | `2geonhyup/dart-mcp` | Financial statement analysis + visualization via DART API |
| FEC MCP | `sh-patterson/fec-mcp-server` | US campaign finance: candidates, donations, Super PACs |

**CRYPTO / WEB3 (selección enterprise):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Alchemy MCP | `alchemyplatform/alchemy-mcp-server` | Official blockchain APIs |
| CoinMarket MCP | `anjor/coinmarket-mcp-server` | Crypto listings + quotes |
| Codex MCP | `Codex-Data/codex-mcp` | 60+ networks real-time enriched blockchain data |
| DexPaprika MCP | `coinpaprika/dexpaprika-mcp` | 20+ chains, 5M+ tokens, real-time pricing, OHLCV |
| Base MCP | `base/base-mcp` | Official Base L2: onchain tools, wallets, DeFi |
| BICScan MCP | `ahnlabio/bicscan-mcp` | Risk score / asset holdings of EVM addresses + domains |
| Armor Crypto MCP | `armorwallet/armor-crypto-mcp` | Multi-chain: staking, DeFi, swap, bridging, DCA, limit orders |
| Arbitova | `arbitova/mcp-server` | On-chain escrow + AI dispute arbitration for USDC payments |
| Azeth Protocol | `azeth-protocol/mcp-server` | ERC-4337 smart accounts, x402 payments, on-chain reputation |
| ClawPay | `up2itnow0822/clawpay-mcp` | Non-custodial x402 payment layer for AI agents |
| Bitcoin Lightning | `getAlby/mcp` | Global instant payments via Lightning |
| Arcadia Finance | `arcadia-finance/mcp-server` | Uniswap/Aerodrome liquidity, leverage, yield optimization |
| Clicks Protocol | `clicks-protocol/mcp-server` | Autonomous USDC yield for AI agents on Base |

### G. LEGAL + COMPLIANCE (9 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| EU AI Act MCP | `ark-forge/mcp-eu-ai-act` | Compliance scanner: regulatory violations, risk classification, remediation |
| GIBS MCP | `buildsyncinc/gibs-mcp` | Multi-regulation: AI Act, GDPR, DORA with article-level citations |
| Gavelin MCP | `gavelin-ai/mcp` | US state legislative intelligence: hearing transcripts, bills, votes |
| US Legal MCP | `JamesANZ/us-legal-mcp` | Comprehensive US legislation access |
| Open Agreements | `open-agreements/open-agreements` | Legal document automation: NDAs, SAFEs, NVCA, employment, cloud terms → DOCX |
| NexusFeed MCP | `NexusFeed/nexusfeed-mcp` | US state ABC liquor license compliance (CA, TX, NY, FL) |
| RIS MCP (Austria) | `philrox/ris-mcp-ts` | Austrian federal/state laws, court decisions, 12 tools |
| EGRUL MCP (Russia) | `atomno-labs/mcp-egrul` | Russian legal entities + entrepreneurs registry |
| FNS Check (Russia) | `atomno-labs/mcp-fns-check` | Russian counterparty due diligence: INN/OGRN, bankruptcy, tax debts |

### H. SALES, CRM, MARKETING, E-COMMERCE (35+ servers)

**CRM / SALES:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Salesforce Marketing MCP | `ZLeventer/salesforce-marketing-mcp` | 47 tools: leads, contacts, accounts, campaigns, 17 reporting tools |
| HubSpot MCP | `NaorAIdeas/hubspot-mcp-server` | API integration: sales + project management |
| HubSpot MCP (deezsecc) | `deezsecc/Hubspot-MCP` | CRM integration |
| Apollo.io MCP | `louis030195/apollo-io-mcp` | 275M+ contacts: B2B sales prospecting + enrichment |
| Apollo.io MCP (edwardchoh) | `edwardchoh/apollo-io-mcp-server` | Apollo.io API: data enrichment + search |
| Tomba MCP | `tomba-io/tomba-mcp-server` | Email discovery, verification, enrichment, LinkedIn profiles |
| RocketReach MCP | `Meerkats-Ai/rocketreach-mcp-server` | Email/phone finding + company enrichment |
| Prospeo MCP | `Meerkats-Ai/prospeo-mcp-server` | Email finding + LinkedIn profile enrichment |
| HeroHunt MCP | `herohunt-ai/herohunt-mcp` | 1B candidates: LinkedIn + GitHub, verified emails/phones |
| JobNimbus MCP | `clykins90/jobnimbus-mcp-server` | CRM: contacts, jobs, tasks, products, workflows, invoices |
| DocuSign MCP | `MGDS01/docusign-test-js-sdk-public` | API for AI applications |
| Close.com MCP | `ShiftEngineering/mcp-close-server` | Leads, contacts, emails, tasks, opportunities, calls |
| CallRail MCP | `pghdma/callrail-mcp` | 49 tools: call tracking, transcripts, agency aggregation |
| SigParser | `SigParser` | Email contact extraction → CRM enrichment → Salesforce, HubSpot, Dynamics |

**MARKETING / ADS:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Meta Ads MCP | `pipeboard-co/meta-ads-mcp` | 10,000+ businesses: analyze, test creatives, optimize spend |
| Meta Ads Full | `mikusnuz/meta-ads-mcp` | 123 tools: Facebook + Instagram campaigns, audiences, creatives, catalogs |
| Google Ads MCP | `gomarble-ai/google-ads-mcp-server` | Programmatic Google Ads management |
| Google Ad Manager | `MatiousCorp/google-ad-manager-mcp` | Publisher ad management |
| Amazon Ads MCP | `MarketplaceAdPros/amazon-ads-mcp-server` | Campaign metrics + configurations |
| TikTok Ads MCP | `AdsMCP/tiktok-ads-mcp-server` | Campaign management, OAuth |
| Synter Media MCP | `Synter-Media-AI/mcp-server` | Cross-platform: Google, Meta, LinkedIn, Microsoft, Reddit, TikTok |
| LinkedIn Ads MCP | (parte de Synter Media) | LinkedIn advertising |
| Mailchimp MCP | `damientilman/mailchimp-mcp-server` | 53 tools: campaigns, audiences, reports, automations, e-commerce |
| Smartlead MCP | `jean-technologies/smartlead-mcp-server-local` | Email marketing campaign management |
| Metricool MCP | `metricool/mcp-metricool` | Social media metrics + campaign scheduling |
| Post For Me MCP | `PostForMe` | Multi-platform social media posting, feeds, analytics |

**SEO:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| SearchAtlas MCP | `SearchAtlas/searchatlas-mcp-server` | SEO, content, PPC, keyword research, site auditing, 16 tools |
| Google Search Console MCP | `lionkiii/google-searchconsole-mcp` | 13 SEO tools: search analytics, URL inspection, sitemaps |
| Ahrefs SEO MCP | `cnych/seo-mcp` | Backlink + keyword research |
| Screaming Frog MCP | `bzsasson/screaming-frog-mcp` | Website crawling + SEO data export |
| SiteAudit MCP | `vdalhambra/siteaudit-mcp` | Instant audits: SEO (20+ checks), security headers, Lighthouse, Schema.org |
| WebCheck MCP | `yifanyifan897645/webcheck-mcp` | SEO audit, accessibility scan, broken links, performance |
| IndexNow MCP | `sharozdawa/indexnow-mcp` | Instant URL indexing: Bing, Yandex, Naver, Seznam + Google Indexing API |
| Schema Gen MCP | `sharozdawa/schema-gen` | JSON-LD markup: 12 types (Person, Product, FAQ, Article, Organization) |
| AI Visibility MCP | `sharozdawa/ai-visibility` | Brand tracking: ChatGPT, Perplexity, Claude, Gemini |
| Robots.txt AI | `sharozdawa/robotstxt-ai` | Visual robots.txt: toggle 20+ AI crawlers |

**ECOMMERCE:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Shopify/Amazon Intel | `samrothschild23/intelligence-api` | Analyze any Shopify store, research Amazon FBA products |
| DSers MCP | `lofder/dsers-mcp-product` | AliExpress/Alibaba → Shopify/Wix dropshipping automation |
| AgentLux MCP | `agentlux/agentlux-mcp` | Agent marketplace: 33 tools, Base/x402 commerce |
| Ozon MCP | `PCDCK/ozon-mcp` | Full Ozon Seller API (466 methods, 15 tools, 13 analytical workflows) |
| Color Me Shop MCP | `pepabo/colormeshop-mcp` | Japanese e-commerce: orders, products, inventory, customers |
| Rakuten MCP | `mrslbt/rakuten-mcp` | Japan's largest e-commerce: product search, hotel/travel |
| WooCommerce MCP | `thoy-le-duc/mcp-woocommerce-thoy` | Store management via JSON-RPC 2.0 + WordPress REST |
| Supply Chain MCP | `OFODevelopment/cerebrochain-mcp-server` | 20 tools: rate shopping 85+ carriers, inventory, order tracking, fleet logistics |
| SupplyMaven MCP | `SupplyMaven-SCR/supplymaven-mcp-server` | 25 tools: Global Disruption Index, commodity prices, port congestion, trade policy |

### I. ENGINEERING, CAD, DESIGN (74 servers)

**CAD / 3D MODELING (14):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Blender MCP | `ahujasid/blender-mcp` | 3D modeling, animation, rendering |
| Fusion 360 MCP | `mikan-atomoki/text-to-model` | 64 CAD tools: sketches, extrudes, fillets, JIS parts |
| SolidWorks MCP | `hussam0is/solidworks-mcp-server` | Parametric solid modeling |
| Maya MCP | `PatrickPalmer/MayaMCP` | 3D animation, rigging, VFX |
| CAD-MCP Universal | `daobataotie/CAD-MCP` + `HuaLuAI/CAD-MCP` | Multi-CAD platform abstraction |
| JupyterCAD | `asmith26/jupytercad-mcp` | CAD in Jupyter notebooks |
| Unreal Engine 5 MCP | `edi3on/py-ue5-mcp-server` | Natural language → 3D scenes, Blueprint actors |
| UnrealMCP Bridge | `appleweed/UnrealMCPBridge` | UE Python API for MCP |
| Unity MCP | `sinkect/unity-mcp-for-editor` + `Signal-Loop/UnityCodeMCPServer` | Game/AR/VR editor automation |
| NVIDIA Isaac Sim MCP | `omni-mcp/isaac-sim-mcp` | Robotics simulation + digital twins |
| 3D Printer MCP | `OctoEverywhere/mcp` | Live printer state, webcam, control |
| 3D Relief MCP | `Bigchx/mcp_3d_relief` | 2D images → STL 3D relief models |

**ENGINEERING (10):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| MATLAB MCP (×2) | `HanSur94/...` + `JSFrouws/...` | Numerical computing, async jobs, Plotly |
| Mathematica MCP | `texra-ai/mcp-server-mathematica` | Symbolic computation, theorem verification |
| Modelica MCP | `Orthogonalpub/modelica_simulation_mcp_server` | Multi-domain physical simulation |
| Stella MCP | `bradleylab/stella-mcp` | System dynamics modeling (.stmx/XMILE) |
| GNU Radio MCP | `yoelbassin/gnuradioMCP` | RF/SDR flowcharts |
| MoldSim MCP | `kobzevvv/moldsim-mcp` | Injection molding: 21 materials, 230+ knowledge chunks, DFM |
| Modbus MCP | `kukapay/modbus-mcp` | Industrial IoT: PLC/RTU communication |
| OPC UA MCP | `kukapay/opcua-mcp` | Industry 4.0: SCADA, MES, manufacturing |
| ESP-IDF MCP | `horw/esp-mcp` | ESP32 firmware builds |

**PCB / ELECTRONICS (3):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Altium MCP | `coffeenmusic/altium-mcp` | PCB design manipulation + querying |
| JLCPCB Parts MCP | `nvsofts/jlcpcb-parts-mcp` | PCBA component search |
| Component Datasheets | `octoco-ltd/sheetsdata-mcp` | Electronic specs, pinouts, max ratings |

**ARCHITECTURE & DESIGN (20):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Figma MCP (×7) | `GLips/Figma-Context-MCP`, `dannote/figma-use`, `vkhanhqui/figma-mcp-go` + others | Design ↔ code, 80+ tools, no rate limits, WebSocket streaming |
| Figma Flutter MCP | `mhmzdev/Figma-Flutter-MCP` | Figma → Flutter widgets |
| After Effects MCP | `sunqirui1987/ae-mcp` | Motion graphics + VFX automation |
| Illustrator MCP | `AnshulDalua/illustrator-mcp` | Vector illustration via JavaScript/AppleScript |
| Premiere Pro MCP | `morim3/mcp_adobe_premiere` | AI-assisted video editing |
| DaVinci Resolve MCP | `samuelgursky/davinci-resolve-mcp` | Color grading, media management, project control |
| Photopea MCP | `attalla1/photopea-mcp-server` | Browser-based Photoshop: 34 tools |
| Design System MCPs | `primitiv`, `m-moire`, `kenneives/design-token-bridge-mcp` | Design contracts, token mgmt, WCAG audits, cross-platform sync |
| Storybook MCP | `freema/mcp-design-system-extractor` | Extract components: HTML, styles, props, dependencies |
| Kolibri MCP | `public-ui/kolibri` | 200+ accessible web components for government/public sector |

**DIAGRAMS & FLOWCHARTS (16):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Mermaid MCP (×5) | `Narasimhaponnada/mermaid-mcp`, `hustcc/mcp-mermaid`, `veelenga/claude-mermaid` + others | 22+ diagram types, 50+ templates, SVG/PNG/PDF |
| Excalidraw MCP | `BV-Venky/excalidraw-architect-mcp` | Hand-drawn architecture: 50+ tech mappings |
| AI Diagram Maker | `erajasekar/ai-diagram-maker-mcp` | Flowcharts, sequence, ERD, UML, mindmaps from NL/code/images |
| FlowZap MCP | `flowzap-xyz/flowzap-mcp` | Diagram-as-code: diff, patch, validation |
| Tentra MCP | `rdanieli/tentra-mcp` | NL → typed diagram (167 cloud components) → 14 frameworks + drift detection |
| Endiagram MCP | `endiagram/mcp` | 12 graph tools: topology, bottlenecks, blast radius, centrality |
| Mindmap MCP | `YuChenSSR/mindmap-mcp-server` | Interactive mindmaps from text |
| D2 MCP | `h0rv/d2-mcp` | D2 declarative diagramming |
| ECharts MCP | `hustcc/mcp-echarts` | Interactive Apache ECharts |
| AntV Chart MCP | `antvis/mcp-server-chart` | Visual charts via AntV |

**UI/UX DESIGN (11):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Magic MCP | `21st-dev/Magic-MCP` | UI components by 21st.dev design engineers |
| shadcn/ui MCP (×2) | `Jpisnice/shadcn-ui-mcp-server` + `shadcn/studio` | shadcn/ui v4 components, blocks, demos |
| Flowbite MCP | `themesberg/flowbite-mcp` | Tailwind CSS UI framework |
| Storybook Addon MCP | `storybookjs/addon-mcp` | Auto write + test UI stories |
| Reftrix MCP | `TKMD/ReftrixMCP` | 26 tools: layout extraction, motion detection, quality scoring, semantic search |
| UI Annotator MCP | `mcpware/ui-annotator-mcp` | Hover labels for AI UI review |
| Icon Genie MCP | `albertnahas/icogenie-mcp` | SVG icon generation from text |
| SVG Maker MCP | `GenWaveLLC/svgmaker-mcp` | AI-driven SVG creation + editing |
| Hugeicons MCP | `hugeicons/mcp-server` | Professional icon library |

### J. DOCUMENT PROCESSING, MEDIA, CONVERSION (35+ servers)

**PDF:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| MinerU MCP | `linxule/mineru-mcp` + `opendatalab/MinerU-Ecosystem` | PDF/DOCX/PPTX/images → Markdown, OCR 109 languages |
| PDFMux | `NameetP/pdfmux` | Intelligent router: digital vs scanned vs tables |
| PDF Researcher | `kokilabo/pdf-researcher` | PDF search via Brave Search API |
| Slideshot | `06ketan/slideshot` | HTML → PDF/PNG/WebP/PPTX: LinkedIn, Instagram, pitch decks |
| DeckRun MCP | `agenticdecks/deckrun-mcp` | Markdown → PDF presentations + narrated videos + MP3 |
| Rendoc | `yoryocoruxo-ai/rendoc` | Template-driven PDF generation: invoices, reports, contracts |
| PageBolt MCP | `Custodia-Admin/pagebolt-mcp` | Screenshot, PDF, OG image, AI-narrated video, multi-step |
| Sifter MCP | `sifter-ai/sifter` | Structure any document, query like DB, schema-defined records |
| Talonic MCP | `talonicdev/talonic-mcp` | Schema-validated document extraction from PDFs, scans, forms |
| Docx MCP | `SecurityRonin/docx-mcp` | 18 tools: Word .docx track changes, comments, footnotes, validation |
| TexMCP | `devroopsaha744/TexMCP` | LaTeX → high-quality PDF: reports, resumes, research papers |

**VIDEO DOWNLOADERS / YOUTUBE:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Yutu MCP | `eat-pray-ai/yutu` | CLI + MCP: full YouTube automation |
| YouTube Transcript | `kimtaeyoon83/mcp-server-youtube-transcript` | Captions for AI analysis |
| YouTube Summarize | `zlatkoc/youtube-summarize` | Transcripts + summaries, multi-language |
| YouTube MCP (format37) | `format37/youtube_mcp` | yt-dlp + Whisper-1 for precise transcription |
| YouTube Uploader | `anwerj/youtube-uploader-mcp` | AI-powered uploads: no CLI, no YouTube Studio |
| Rippr | `mrslbt/rippr` | Transcript extraction: text, timestamps, JSON |
| CrabCut MCP | `realcrabcut/crabcut-mcp-server` | YouTube → short-form clips: AI highlight detection, subtitles, 9:16 |
| Ssemble MCP | `ssembleinc/ssemble-mcp-server` | AI short-form clips: captions, music, gameplay overlays, viral scoring |
| SubDownload MCP | `SubDownload/subdownload-mcp` | YouTube knowledge base: summaries, transcripts, channel/playlist search |

**AUDIO / TRANSCRIPTION / VOICE:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Whipscribe MCP | `neugence/whipscribe-mcp` | Audio/video → txt/json/srt/vtt/docx + speaker diarization |
| Transcribe App MCP | `transcribe-app/mcp-transcribe` | Fast audio/video transcription |
| Voice MCP | `mbailey/voice-mcp` | Complete voice: STT, TTS, real-time via mic + LiveKit |
| Telephony MCP | `khan2a/telephony-mcp-server` | Voice calls: STT/SR, summarize, SMS, voicemail detection |
| Spix MCP | `Spix-HQ/spix-mcp` | AI phone agents: outbound/inbound, ~500ms latency (Deepgram + Claude + Cartesia) |
| AI Call Assistant | `Leximo-AI/leximo-ai-call-assistant-mcp-server` | Book reservations, schedule appointments, view transcripts |
| CallCenter MCP | `gerkensm/callcenter.js-mcp` | VoIP/SIP + OpenAI Realtime: observe transcripts |
| Carbon Voice MCP | `PhononX/cv-mcp-server` | Voice-first workplace: messages, conversations, voice memos |
| Gaudio MCP | `gaudiolab-jp/gaudio-developers-mcp` | Stem separation, DME (dialogue/music/effects), AI lyrics sync |
| BareValue MCP | `quietnotion/barevalue-mcp` | AI podcast editing: filler removal, noise reduction, show notes, clips |
| Brainiall MCP | `fasuizu-br/brainiall-mcp-server` | Pronunciation assessment, STT language detection, TTS |

**IMAGE / CREATIVE:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| MCPFlux | `AceDataCloud/MCPFlux` | Flux AI: Black Forest Labs image gen + editing |
| MCPNanoBanana | `AceDataCloud/MCPNanoBanana` | Virtual try-on + product placement |
| MCPSeedream | `AceDataCloud/MCPSeedream` | ByteDance Seedream image gen |
| ComfyUI Pilot | `ConstantineB6/comfy-pilot` | View, edit, run ComfyUI workflows |
| Fal.ai MCP | `raveenb/fal-mcp-server` | FLUX, Stable Diffusion, MusicGen via Fal.ai |
| Studio MCP Hub | `codex-curator/studiomcphub` | 32 tools: SD 3.5, ESRGAN, background removal, CMYK, SVG, Arweave |
| Imagen3 MCP | `hamflx/imagen3-mcp` | Google Imagen 3.0: photography, artistic, photorealistic |
| Agent Media MCP | `yuvalsuede/agent-media` | 7 models: Kling, Veo, Sora, Seedance, Flux, Grok Imagine |
| PromptPilot MCP | `doctorm333/promptpilot-mcp-server` | 20+ AI models: image, video, audio generation |
| AlphaBanana MCP | `tasopen/mcp-alphabanana` | Local Gemini image gen: transparent PNG/WebP, exact resize |
| SVMaker MCP | `GenWaveLLC/svgmaker-mcp` | SVG generation + editing via NL |
| Nakkas MCP | `arikusi/nakkas` | SVG artist: CSS keyframes, SMIL, 16+ element types |
| MeiGen MCP | `jau123/MeiGen-AI-Design-MCP` | 1,500+ curated prompts, multi-provider routing |
| Topaz MCP | `TopazLabs/topaz-mcp` | AI enhancement: upscaling, denoising, sharpening (8 models) |
| Prompt-to-Asset MCP | `MohamedAbdallah-14/prompt-to-asset` | App icons, favicons, OG images, logos, wordmarks. 30+ models |
| Suno MCP | `AceDataCloud/MCPSuno` | AI music generation: lyrics, covers, vocal extraction |
| Mureka MCP | `SkyworkAI/Mureka-mcp` | Create lyrics, songs, background music |
| SuperCollider MCP | `Tok/SuperColliderMCP` | Audio synthesis, processing, OSC |
| MIDI MCP | `sandst1/mcp-server-midi` | Transmit MIDI from LLM to any MIDI software/hardware |
| Elektron MCP | `zerubeus/elektron-mcp` | Elektron synthesizer MIDI control |
| OSC Bridge MCP | `roomi-fields/osc-bridge` | OSC↔MIDI/SysEx: 849 hardware synthesizers |
| Reaper MCP | `TwelveTake-Studios/reaper-mcp` | 129 tools: mixing, mastering, MIDI composition |
| Vibe MCP | `trevhud/vibe-mcp` | Music generation from coding context |

### K. CLOUD PLATFORMS + INFRASTRUCTURE (109 servers)

**AWS (6), Azure (5), GCP (1), Multi-Cloud (4):**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| AWS Labs MCP | `awslabs/mcp` | Official AWS integration |
| AWS SSO MCP | `aashari/mcp-server-aws-sso` | SSO login, roles, temp credentials |
| AWS S3 MCP | `ofershap/mcp-server-s3` | Buckets, objects, presigned URLs |
| AWS Pricing MCP | `trilogy-group/aws-pricing-mcp` | Pre-parsed EC2 pricing, FinOps |
| AWS Security MCP | `groovyBugify/aws-security-mcp` | Security analysis + threat modeling |
| AWS Cost Explorer | `sanxxit/my-aws-cost-explorer` | Spend analysis + visualization |
| LocalStack MCP | `localstack/localstack-mcp-server` | Local AWS: lifecycle, deployments, fault injection |
| Azure Blue Bridge | `Azure/blue-bridge` | Official: zero-secret auth, Managed Grafana, ADX |
| Azure CLI MCP | `jdubois/azure-cli-mcp` + `JCallico/py-az-mcp` | Conversational Azure + full CLI wrapper |
| Azure Resource Graph | `hardik-id/azure-resource-graph-mcp-server` | Multi-subscription resource exploration |
| Azure Cost (CloudScope) | `alexpota/cloudscope-mcp` | Spending, forecasts, anomaly detection, budgets |
| Azure Data Lake | `erikhoward/adls-mcp-server` | Container + file management |
| GCP Billing | `curious-pm/mcp-google_cloud_billing` | Cloud cost management |
| Cloud Cost MCP | `jasonwilbur/cloud-cost-mcp` | Multi-cloud: AWS, Azure, GCP, OCI. 2,700+ instances |
| OCI Pricing | `jasonwilbur/oci-pricing-mcp` | Oracle Cloud: 602 products |
| CloudWright MCP | `xmpuspus/cloudwright` | NL → ArchSpec, cost, compliance (HIPAA, SOC 2, FedRAMP, GDPR), Terraform/CFN |

**KUBERNETES (24 servers):**
- `alexei-led/k8s-mcp-server` — kubectl, helm, istioctl, argocd en Docker seguro
- `manusa/kubernetes-mcp-server` — OpenShift + CRUD for any K8s resource
- `weibaohui/k8m` + `weibaohui/kom` — Multi-cluster, ~50 tools, UI, CRD support
- `mctlhq/mctl-mcp` — AI-native K8s + GitOps (30+ tools)
- `Flux159/mcp-server-kubernetes` — TypeScript K8s operations
- `silenceper/mcp-k8s` — Natural language K8s + CRDs
- `cyclops-ui/mcp-cyclops` — K8s via Cyclops abstraction
- `strowk/mcp-k8s-go` + `reza-gholizade/k8s-mcp-server` + `wenhuwang/mcp-k8s-eye` + others
- `spre-sre/lumino-mcp-server` — 40+ tools SRE: Tekton, logs, RCA, predictive monitoring
- `kubestellar/console` — Multi-cluster edge+cloud: 50+ tools, workload placement
- `rancher-mcp-server` — Rancher + Harvester HCI + Fleet GitOps
- `tilt-mcp` + `kubefwd` + `helmfile-mcp` — Dev workflows
- `cert-manager-mcp-server` — TLS automation
- `portainer/portainer-mcp` — Container management via NL

**OTHER CLOUD / INFRASTRUCTURE:**
| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Cloudflare MCP (×2) | `cloudflare/mcp-server-cloudflare` + `ofershap/mcp-server-cloudflare` | Workers, KV, R2, D1, Pages, DNS |
| Fastly MCP | `Arodoid/FastlyMCP` | CDN: caching, security, performance |
| Render MCP | `render-oss/render-mcp-server` | Official: services, static sites, cron, Postgres, KV, logs |
| DigitalOcean MCP | `oliverbenns/digitalocean-mcp` + billing | App platform + cost management |
| Alibaba Cloud MCP | `aliyun/alibaba-cloud-ops-mcp-server` | ECS, Cloud Monitor, OOS |
| Tencent Cloud MCP | `TencentCloudBase/CloudBase-AI-ToolKit` + `Tencent/cos-mcp` | Serverless, DB, storage, WeChat ecosystem |
| Pulumi MCP | `pulumi/mcp-server` | IaC: Automation API + Cloud API |
| Terraform MCP | `hashicorp/terraform-mcp-server` + `nwiizo/tfmcp` | Official: provider discovery, module analysis, Registry API |
| Proxmox MCP | `antonio-mello-ai/mcp-proxmox` | 29 tools: VMs, containers, snapshots, cloud-init, firewall |
| VMware ESXi MCP | `bright8192/esxi-mcp-server` + `lijian-ui/vcenter-mcp-server` | vCenter management |
| NetBox MCP | `ardecode/netbox-mcp-server` | DCIM + network infrastructure |
| pfSense MCP | `antonio-mello-ai/mcp-pfsense` | 17 tools: firewall rules, DHCP, DNS, gateway monitoring |
| Consul MCP (×3) | `3loka/consul-mcp-server` + others | Service mesh: discovery, health, KV |
| Nomad MCP | `kocierik/mcp-nomad` | HashiCorp workload orchestration |
| Spinnaker MCP | `GeiserX/spinnaker-mcp` | Multi-cloud deployment pipeline management |
| Portainer MCP | `portainer/portainer-mcp` | Container management via NL |
| Buildkite MCP | `buildkite/buildkite-mcp-server` | Pipeline, build, job data |
| Airflow MCP | `us-all/airflow-mcp-server` + `hipposys-ltd/airflow-mcp` | DAG: list, runs, task instances, log tails, trigger, clear |
| SSH MCP (×4) | `blakerouse/ssh-mcp`, `tufantunc/ssh-mcp`, `classfang/ssh-mcp-server` + others | Multi-host server management |
| Subnet Calculator | `melihteke/Subnet-Calculator-MCP-Server` | Network planning |
| Harness MCP | `vistaarjuneja/harness-mcp` | CI/CD connector management |
| Bazel MCP | `aaomidi/mcp-bazel` | Build, test, dependency analysis |
| Maven MCP | `thepragmatik/mcp-server-jvm-build-tools` | Natural language Maven builds |

### L. HEALTHCARE, MEDICAL, BIO (30+ servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Genomic Agent Discovery | `HelixGenomics/Genomic-Agent-Discovery` | Multi-agent: 16 DBs (ClinVar, GWAS, gnomAD, CPIC, AlphaMissense) |
| MyMedi AI MCP | `MyMedi-AI/mymedi-ai-mcp-server` | 81,769 codes: ICD-10/CPT/HCPCS, prior auth, claims, denial-risk, HIPAA audit |
| DICOM-HL7-FHIR Bridge | `NyxToolsDev/dicom-hl7-mcp-server` | Cross-standard mapping, Mirth Connect channel gen, vendor tags |
| FHIR MCP Server (×2) | `wso2/fhir-mcp-server` + `the-momentum/fhir-mcp-server` | SMART-on-FHIR: clinical data CRUD, patient history NL |
| OMOP MCP | `OHNLP/omop_mcp` | Clinical terminology → OMOP concepts, healthcare data standardization |
| HEOR Agent MCP | `neptun2000/heor-agent-mcp` | 41 sources: PubMed, NICE, CADTH, ICER. Markov/PartSA/PSA modeling |
| ARIA MCP Server | `pkotecha-eng/aria-mcp-server` | Clinical: PubMed 35M+ papers + ClinicalTrials.gov 400K+ trials |
| BioMCP | `genomoncology/biomcp` | Biomedical: PubMed, ClinicalTrials.gov, MyVariant.info |
| Medical MCP | `JamesANZ/medical-mcp` | Drug databases, interactions, clinical guidelines |
| DICOM MCP (×2) | `ChristianHinge/dicom-mcp` + `shaunporwal/DICOM-MCP` | Medical imaging: query, read, move from PACS |
| Apple Health MCP | `the-momentum/apple-health-mcp-server` | Exported Apple Health data + analytics |
| Fulcra Context MCP | `fulcradynamics/fulcra-context-mcp` | Sleep, HRV, glucose, workouts via OAuth2 |
| Oura MCP | `johnie/oura-mcp` | Oura Ring health metrics |
| Eight Sleep MCP | `elizabethtrykin/8sleep-mcp` | Sleep Pod data + settings |
| ChatSpatial MCP | `cafferychen777/ChatSpatial` | Spatial transcriptomics: 60+ methods (deconvolution, statistics) |
| ENCODE Toolkit | `ammawla/encode-toolkit` | ENCODE Project genomic data |
| UCSC Genome MCP | `hlydecker/ucsc-genome-mcp` | Genome Browser API |
| BioThings MCP | `longevity-genie/biothings-mcp` | Genes, variants, drugs, taxonomy |
| OpenGenes MCP | `longevity-genie/opengenes-mcp` | Aging + longevity research |
| SynergyAge MCP | `longevity-genie/synergy-age-mcp` | Genetic interactions in longevity |
| PubTator MCP (×2) | `BioMCP-Hub/PubTator-MCP-Server` + `JackKuo666/...` | Biomedical literature annotation + relationship mining |
| PubMed MCP | `codingaslu/PubMed-MCP-Server` | Async PubMed article search via BioPython Entrez |
| PubChem MCP (×3) | `BioContext/PubChem-MCP` + `JackKuo666/...` | Compounds, substances, bioassays |
| ChEMBL MCP | `BioContext/ChemBL-MCP` | Molecules, targets, assays, bioactivity |
| ClinicalTrials MCP | `JackKuo666/ClinicalTrials-MCP-Server` | AI-driven clinical trial search |
| Cortellis MCP | `uh-joan/cortellis-mcp-server` | Drug search + ontology |
| OPDStar NHI MCP | `tatsuju/opdstar-nhi-mcp` | Taiwan NHI: 234 rejection codes, 1,497 ICD-10 mappings |
| FoodDB MCP | `eiz/fooddb` | USDA Food Data Central: keyword + semantic vector search |
| Open Dental MCP | `AojdevStudio/open-dental-mcp` | OpenDental documentation via Qdrant |
| Molecule MCP | `ChatMol/molecule-mcp` | Molecular modeling with Claude |

### M. HR, RECRUITING, JOBS (14 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| HeroHunt MCP | `herohunt-ai/herohunt-mcp` | 1B candidates: LinkedIn + GitHub, verified emails/phones |
| Teamtailor MCP | `crunchloop/mcp-teamtailor` | ATS: candidate data management |
| LinkedIn Jobs MCP | `Rom7699/linkedin-jobs-mcp-server` | Job search via RapidAPI |
| JobSpy MCP | `borgius/jobspy-mcp-server` | Multi-platform: LinkedIn, Indeed, Glassdoor, ZipRecruiter |
| Workopia MCP | `workopia/workopia-mcp` | Employer career pages + PDF resume gen (50+ templates) + career advice |
| Agentic Engineering Jobs | `agentic-engineering-jobs.com/mcp` | Live agentic AI jobs: filter by framework, seniority, salary benchmarks |
| MadGapun PBP | `MadGapun/PBP` | DACH market: 73 tools, 18 job portal scrapers, AI coaching, scoring |
| Apollo.io MCP | `louis030195/apollo-io-mcp` | 275M+ contacts: sales prospecting + enrichment |
| RocketReach MCP | `Meerkats-Ai/rocketreach-mcp-server` | Email/phone finding |
| Prospeo MCP | `Meerkats-Ai/prospeo-mcp-server` | Email + LinkedIn enrichment |
| Tomba MCP | `tomba-io/tomba-mcp-server` | Email discovery, verification, LinkedIn profiles |
| SigParser | `SigParser` | Contact extraction → CRM enrichment |
| Web3 Jobs MCP | `kukapay/web3-jobs-mcp` | Curated Web3 jobs |

### N. SUPPLY CHAIN, LOGISTICS, MANUFACTURING (18 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| CerebroChain MCP | `OFODevelopment/cerebrochain-mcp-server` | 20 tools: rate shopping 85+ carriers, inventory, order tracking, fleet logistics, demand forecasting |
| SupplyMaven MCP | `SupplyMaven-SCR/supplymaven-mcp-server` | 25 tools: Global Disruption Index, Manufacturing Index, commodity prices, port congestion, border delays, chokepoints, air cargo, trade policy, energy, rail, freight |
| Shipi MCP | `aarsiv-groups/shipi-mcp-server` | 18 tools: shipments, tracking, rate comparison across carriers |
| Royal Mail MCP | `catrinmdonnelly/royalmail-mcp` | 33 UK + international services: book, label, track, cancel |
| DoorDash MCP | `jordandalton/doordash-mcp-server` | Delivery integration |
| UUPT MCP | `uupt-mcp/uupt-mcp-server` | Order creation on delivery platform |
| Packrift MCP | `Packrift/packrift-mcp` | Packaging supplies catalog: product search, pricing, inventory |
| MyCarTracks | `MyCarTracks` | GPS vehicle tracking + automatic mileage |
| Auto Dev Skill | `drivly/auto-dev-skill` | Automotive: VIN decode, vehicle listings, payments, recalls, specs |
| Dragon MCP | `arthurpanhku/DragonMCP` | Greater China: Meituan/Ele.me delivery, Didi ride-hailing |
| MRC Data MCP | `meacheal-ai/mrc-data` | Chinese apparel supply chain: 3,000+ manufacturers, 350+ fabrics, 170+ clusters |
| Modbus MCP | `kukapay/modbus-mcp` | Industrial IoT: PLC/RTU communication |
| OPC UA MCP | `kukapay/opcua-mcp` | SCADA, MES, manufacturing execution |
| MoldSim MCP | `kobzevvv/moldsim-mcp` | Injection molding: materials, DFM, troubleshooting |
| IoTDB MCP (×3) | `apache/iotdb-mcp-server` + variants | Industrial time-series: SQL for IoT |
| Arduino MCP | `Volt23/mcp-arduino-server` | Arduino CLI: sketch, board, library, file management |
| ESP RainMaker MCP (×2) | `espressif/esp-rainmaker-mcp` + `dhavalgujar/...` | IoT device management |
| MQTT MCP | `ioehub/ioehub-mqtt-mcp-server` | IoT: temperature sensing, LED control |

### O. CUSTOMER SUPPORT, HELPDESK (8 servers)

| Server | Repo | Enterprise Use |
|--------|------|---------------|
| Zendesk MCP | `nicekon/zendesk-mcp-server-kon` | Tickets, community posts, knowledge base |
| Zammad MCP | `arush15june/zammad-mcp-go` | Tickets + users |
| AI Concierge (Perspective AI) | `Perspective-AI/mcp` | Lead qualification, customer research, onboarding feedback |
| Smart Customer Support MCP | `precariat365/SmartCustomerSupportMCP` | Q&A, human agent handover, order info, product knowledge |
| Housecall Pro MCP | `service-hero/housecallpro-mcp-server` | Field service management |
| Octolis Tech Support | `slavatHatnuke/octolis-tech-support` | Technical support operations |
| Telnyx MCP | `team-telnyx/telnyx-mcp-server` | Telephony, messaging, AI assistant APIs |
| Commune MCP | `commune-sh/commune-mcp` | Email infrastructure for AI agents: inboxes, threads, custom domains, SMS |

---

## IV. ARQUITECTURA PROPUESTA v3.0

```
┌─────────────────────────────────────────────────────────────┐
│                  ENTERPRISE LLM PLATFORM v3.0                │
├─────────────────────────────────────────────────────────────┤
│  Gateway Multi-Canal (Slack, Teams, Email, API OpenAI-compat)│
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ VIGILANCIA│  │  DEEP     │  │ BUSINESS │  │  CUSTOM     │  │
│  │ TECNOL.  │  │ RESEARCH  │  │ INTEL    │  │  SKILLS     │  │
│  │ (6 ramas)│  │ (genérico)│  │ (fin, RH)│  │  (plugins)  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       └──────────────┴─────────────┴──────────────┘         │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           AGENT ORCHESTRATOR (delegate_task)         │   │
│  │  • AgentFactory: spawn ANY agent type                │   │
│  │  • ToolRegistry: auto-discover Python + MCP tools    │   │
│  │  • Toolset Composition: recursive includes           │   │
│  │  • ContextCompressor: multi-phase summarization      │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         MCP HUB — 100+ servers, 15 categorías        │   │
│  │  Search | DB | Code Exec | Browser | Computer Use    │   │
│  │  Office/Excel/PowerBI | Finance | Legal | CRM        │   │
│  │  CAD/Engineering | Design | Cloud/K8s | Healthcare   │   │
│  │  Documents/Media | Supply Chain | HR | Support       │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              INFRASTRUCTURE LAYER                     │   │
│  │  • Multi-Provider LLM (Claude, GPT, Gemini, DeepSeek) │   │
│  │  • Memory Providers (pgvector + mem0 + honcho)       │   │
│  │  • Knowledge Graph (Neo4j persistente)               │   │
│  │  • Checkpoints | Cron Scheduler | Kanban | Curator   │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Frontend: React 19 + Zustand + SSE + D3 + xterm.js         │
└─────────────────────────────────────────────────────────────┘
```

## V. QUÉ PRESERVAR DE v2.0

| Componente | Acción |
|-----------|--------|
| Arquitectura hexagonal (36 Protocols) | Preservar |
| Gobernanza (SystemBase + BranchOverlay) | Preservar y generalizar para skills |
| Evaluation Workstreams (WS-A→E) | Preservar |
| SSE event-driven frontend | Preservar |
| Diseño Atlas Científico (CSS tokens) | Preservar |
| 8 Zustand stores | Preservar |
| 6 branch agents pipeline | Generalizar en AgentOrchestrator |
| SmartToolRouter + StrategyMemory | Preservar y expandir |
| Constitution compliance tests | Preservar |
| 14 MCP providers actuales | Expandir a 100+ |

---

---

## VI. METODOLOGÍAS INNOVADORAS DE HERMES AGENT (Deep Dive)

### A. Sistema de Compresión de Contexto (agent/context_compressor.py)
**Algoritmo multi-fase con template estructurado:**
1. **Prune**: tool outputs viejos → resúmenes de 1 línea (`[terminal] ran 'npm test' → exit 0`)
2. **Protect**: system prompt + primeras N interacciones + últimas por token budget (no fixed count)
3. **Summarize**: LLM del modelo barato → main → static placeholder → abort
4. **Iterative updates**: en re-compactación, el summary previo se alimenta como "previous compaction" → preserva info a través de múltiples compresiones
5. **Anti-thrashing**: tracks savings ratio, backs off después de 2 compresiones <10%
6. **Focus-topic guided**: `/compress <focus>` prioriza preservar info del tópico específico

**Template de 13 secciones:** `## Active Task`, `## Goal`, `## Constraints`, `## Completed Actions`, `## Active State`, `## In Progress`, `## Blocked`, `## Key Decisions`, `## Resolved Questions`, `## Pending User Asks`, `## Relevant Files`, `## Remaining Work`, `## Critical Context`

### B. Mixture of Agents (tools/mixture_of_agents_tool.py)
**Deliberación multi-modelo como TOOL (no feature):**
- **Layer 1**: 4 modelos frontier en paralelo (Claude Opus 4.6, Gemini 2.5 Pro, GPT 5.4 Pro, DeepSeek V3.2) — reasoning=xhigh, temp=0.6 para diversidad
- **Layer 2**: Aggregator (Claude Opus 4.6, temp=0.4) recibe las 4 respuestas + query → síntesis crítica
- **6 retries por modelo** con exponential backoff (2s→4s→8s→16s→32s→60s)
- **MIN_SUCCESSFUL_REFERENCES=1** — funciona aunque fallen 3 de 4 modelos
- El agente DECIDE cuándo invocar MoA para problemas complejos

### C. Computer Use Tool (tools/computer_use_tool.py)
**Control de escritorio macOS universal:**
- 13 acciones en 1 tool consolidado: capture, click, double_click, right_click, drag, scroll, type, key, set_value, wait, list_apps, focus_app
- **Background operation** — no roba cursor/teclado/Space. Funciona en ventanas ocultas/minimizadas
- **Model-agnostic** — schema OpenAI function-calling, no Anthropic-only
- **SOM mode**: overlays numerados en elementos interactuables + AX tree
- **set_value**: selecciona dropdowns y sliders sin abrir menús nativos (sin focus steal)
- **Hard-blocked combos**: cmd+shift+backspace, cmd+ctrl+q, fork bomb patterns
- **Intelligent vision routing**: PNG a modelo principal si soporta visión, o a aux vision si no

### D. Browser CDP Supervisor (tools/browser_supervisor.py)
**El sistema de browser más avanzado:**
- **3-capas**: high-level tools → CDP passthrough → Dialog supervisor
- **CDP Supervisor**: WebSocket persistente por task_id, inyecta JS bridge que overridea alert/confirm/prompt vía Fetch.requestPaused
- **3 políticas de diálogo**: must_respond, auto_dismiss, auto_accept
- **OOPIF frame tree**: tracking de cross-origin iframes con session IDs
- **Ring buffer de eventos de consola**
- **180x más rápido** — evaluaciones JS por WebSocket persistente vs abrir nueva sesión CDP cada vez
- **5+ backends**: agent-browser local, Browserbase, Browser Use, Firecrawl, Camofox (anti-detección), CDP endpoint

### E. Terminal Tool con 7 Backends (tools/terminal_tool.py)
**Shell environment management completo:**
- **Session snapshot**: captura env vars, funciones, aliases, shell options → ~6ms más rápido por comando
- **CWD tracking** via marcadores in-band en stdout
- **Compound background rewriting**: `A && B &` → `A && { B & }` (bash grammar-aware)
- **Adaptive poll loop**: 5ms→200ms exponencial, ~195ms ahorrado en fast commands
- **Grandchild pipe leak prevention**: select.select() + stop drain post-bash exit
- **Sudo password prompting** con session-scoped cache + hidden input
- **Exit code interpretation**: grep=1→"No matches (not an error)", diff=1→"Files differ (expected)"
- **foreground→background guidance**: detecta npm run dev, docker compose up → sugiere background=true
- **CWD deletion recovery**: camina up el path tree al ancestro existente más cercano
- **7 backends**: local, docker, ssh, modal, daytona, singularity, + todos comparten BaseEnvironment.execute()

### F. Code Execution RPC Sandbox (tools/code_execution_tool.py)
**Dual-transport RPC donde el LLM escribe scripts reales:**
- **Local (UDS/TCP)**: socket Unix domain → RPC listener thread → child process ejecuta script
- **Remote (file-based)**: base64-encode + echo a remote → polling thread lee request files → dispatch → escribe response files
- **Code-generated stubs** con type hints por tool (solo 7 tools whitelisted)
- **Head+tail stdout truncation**: 40% head + 60% tail, preserva errores tempranos y output final
- **Process group kill con escalation**: psutil → SIGTERM → 5s wait → SIGKILL

### G. Plugin Architecture (hermes_cli/plugins.py)
**4 fuentes de descubrimiento con override semántico:**
1. Bundled (`<repo>/plugins/<name>/`) — siempre scanned
2. User (`~/.hermes/plugins/<name>/`) — overridea bundled
3. Project (`./.hermes/plugins/<name>/`) — gated by env var
4. Pip (`hermes_agent.plugins` entry-points) — siempre scanned

**15+ lifecycle hooks**: pre_tool_call (puede vetar), post_tool_call, transform_tool_result, pre_llm_call, post_llm_call, pre_api_request, post_api_request, transform_terminal_output, on_session_start, on_session_end, on_session_finalize, on_session_reset, subagent_stop, pre_gateway_dispatch, pre_approval_request, post_approval_response

### H. Frozen-Snapshot Memory Pattern
**La innovación arquitectónica más significativa:**
- t=0: READ MEMORY.md + USER.md → TAKE frozen snapshot → BUILD system prompt
- t=1..N: writes VAN A DISCO inmediatamente pero NO afectan el prompt actual
- t=N+1: futuras sesiones ven el MEMORY.md actualizado
- Resuelve la tensión fundamental: escrituras durables + sesión estable
- `system_prompt_frozen_snapshot` en SQLite para resumir sesiones idénticamente

### I. SessionDB con FTS5 (hermes_state.py)
- SQLite + FTS5 full-text search en transcripts
- Búsqueda cross-session con snippets y BM25 ranking
- `session_search_tool.py` → el LLM busca su propia historia antes de investigar

### J. Curator (agent/curator.py)
- Lifecycle automático active→stale→archived
- LLM review fork para consolidación de skills
- Classification reconciliation: 3 fuentes (model YAML + tool-call heuristic + absorbed_into declarations)
- Pinned skills bypass all auto-transitions
- Pre-run snapshots para rollback

### K. CheckpointManager (tools/checkpoint_manager.py)
- Single shared git store con content-addressable dedup
- Auto-snapshots antes de write_file, patch, terminal commands
- Git isolation (GIT_CONFIG_GLOBAL=/dev/null)
- Rollback full o single-file
- Retention: max_snapshots=20, max_total_size_mb=500

### L. Provider Abstraction (providers/base.py)
- ProviderProfile declarativo: ~30 campos
- 29 providers bundled (openrouter, anthropic, deepseek, gemini, openai, etc.)
- 3-tier scan: bundled → user → legacy, last-writer-wins
- Auxiliary client router: per-task overrides + HTTP 402 fallback
- 17 provider aliases

### M. Skill Usage Tracking + Implicit Feedback (tools/skill_usage.py)
- use_count, view_count, patch_count, last_activity_at per skill
- Top 5 más usadas injectadas en system prompt
- Curator usa estos datos para auto-prune/consolidate

### N. LSP Semantic Diagnostics on Write
- Cada write_file/patch → language server corre → type errors, undefined symbols, missing imports → feedback al agente antes del próximo turno
- Va más allá del syntax linting básico

### O. File Mutation Verifier Footer
- Footer post-turn resumiendo exactamente qué cambió en disco (paths, line counts, deltas)
- El agente detecta sus propios errores (write que no landed, archivo no guardado)

---

## VII. HERRAMIENTAS ÚNICAS DE HERMES AGENT (Deep Dive)

### Browser System (3 archivos, 3 capas)
| Capa | Tool | Innovación |
|------|------|-----------|
| High-level | browser_navigate, snapshot, click, type, scroll, vision, console | Auto-snapshot en navigate, accessibility tree, vision routing |
| CDP passthrough | browser_cdp | Raw CDP WebSocket, target_id + frame_id targeting, OOPIF support |
| Dialog supervisor | browser_dialog | JS injection que overridea alert/confirm/prompt a nivel Fetch |

### Web Tools (8 backends, per-capability routing)
- web_search, web_extract, web_crawl
- 7 providers: brave-free, ddgs, searxng, exa, parallel, tavily, firecrawl
- web.search_backend ≠ web.extract_backend independientes
- Chunked LLM summarization: 500K+ chars → 100K chunks paralelos → synthesis pass
- SSRF protección multi-nivel: pre-flight + redirect-guard + secret-in-URL
- clean_base64_images() para ahorrar tokens

### Messaging Platform Tools (agente actúa SOBRE plataformas)
- **Discord tool**: 15 acciones (list_guilds, server_info, channels, roles, members, messages, pins, threads, add/remove_role). Privileged intent auto-detection. Per-action user allowlist
- **Send Message tool**: cross-platform (Telegram, Discord, Slack, Signal, WhatsApp, Matrix, WeChat, Feishu, Yuanbao). Multi-level target resolution. Media via inline directive
- **Feishu/Lark tools**: doc read (raw_content), drive comments CRUD. Lazy import (5s startup saving)
- **Home Assistant**: 4 tools. 6 service domains permanentemente bloqueados (shell_command, python_script, etc.)

### Media Generation (plugin-architected, 0 backends in-tree)
- **Video generation**: unified schema (generate, edit, extend). Backends vía plugins/video_gen/<name>/
- **Image generation**: 11 FAL models catalog (FLUX 2 Klein, Recraft V3, Ideogram 3.0, SD 3.5, etc.). 3 size-spec families (preset, aspect_ratio, gpt_literal). Supports whitelist per model
- **TTS**: 8+ providers (Edge TTS free, ElevenLabs, OpenAI, MiniMax, Mistral Voxtral, Gemini, xAI, NeuTTS local, Piper 44 languages, custom command providers)

### Transcription (tools/transcription_tools.py)
- 6 providers: local faster-whisper, Groq, OpenAI, Mistral, xAI, CLI
- Auto-detection cascade: local → Groq free → OpenAI paid → xAI
- Lazy-install de faster_whisper
- Cloud model name correction

### Vision Tools (tools/vision_tools.py)
- Native vision fast path → modelo principal ve píxeles directamente (sin aux LLM)
- Magic number MIME detection (lee primeros 64 bytes)
- Auto-resize en API rejection (Pillow, progressive halving)
- Multimodal tool-result envelope con fallback a texto
- SSRF redirect guard en downloads

### X/Twitter Search (tools/x_search_tool.py)
- Dual auth: SuperGrok OAuth auto-refresh O XAI_API_KEY
- Client-side date validation (previene llamadas billables fallidas)
- degraded signal: cuando xAI devuelve 0 citations → flag degraded=True
- Handle filtering: hasta 10 allowed o excluded

---

## VIII. METODOLOGÍAS INNOVADORAS DE OPENCLAW (Deep Dive)

### A. ChannelPlugin Interface (~30 adapters opcionales)
- El centro del sistema de plugins. Un solo tipo con ~30 adapters opcionales
- ChannelConfigAdapter, ChannelGatewayAdapter (startAccount/stopAccount), ChannelOutboundAdapter, ChannelDirectoryAdapter, ChannelSecurityAdapter (DM policies, allowlists), ChannelThreadingAdapter, ChannelMessagingAdapter, ChannelMessageActionAdapter (describeMessageTool → schema dinámico)
- Cada plugin implementa SOLO lo que necesita. Core llena defaults

### B. Message Tool con Schema Dinámico
- Un solo `message` tool adapta su schema según el canal activo
- ChannelMessageActionAdapter.describeMessageTool() → acciones disponibles (send, react, edit, delete), capacidades (media, polls, threads), fragments de schema, media source params
- El AI siempre sabe qué acciones están disponibles sin hardcoding

### C. Gateway Multi-Auth Simultáneo
- 6 métodos de auth simultáneos: token, password, Tailscale identity, device tokens (iOS/Android/browser), bootstrap tokens (one-time setup), trusted proxy
- Rate limiting per-IP con serialized attempt tracking
- Operator Scopes: ADMIN_SCOPE, APPROVALS_SCOPE, custom scopes por método

### D. Lazy Loading Extremo
- Casi cada subsistema cargado vía dynamic import() con cached promises
- Model catalog, channel runtime, MCP server, process registry, auth, config
- Gateway bootea en etapas: auth handshake primero → monta subsistemas progresivamente

### E. Subagent Registry con Full Lifecycle
- Registration, persistence, restore from disk
- Announcement delivery a parent agents
- Orphan recovery
- Depth limits, session reconciliation
- Completion tracking + delivery retry

### F. Auth Profile Rotation + Cooldown
- Multi-credential rotation system para AI providers
- API keys, OAuth credentials, token credentials
- Failed profiles → cooldowns → round-robin
- External CLI integration (Anthropic CLI, Codex CLI)
- OAuth refresh runtime

### G. Dreaming — Memory Consolidation con Fases Biológicas
- Light phase: sort and stage short-term material
- Deep phase: 6 weighted signals (frequency, relevance, query diversity, recency, consolidation, conceptual richness). Multi-threshold gates → promueve a MEMORY.md
- REM phase: extract patterns and reflective themes
- Dream Diary: entradas narrativas
- Historical backfill: replay old notes through grounded promotion

### H. Mantis — Visual E2E Verification para Live Transports
- Reproduce bugs en transports reales (Discord, Slack, Telegram, WhatsApp)
- Before/after evidence con screenshots + browser automation
- Corre en Crabbox VMs con VNC rescue
- Publica PR evidence artifacts en R2/S3 con motion-trimmed GIFs
- Deterministic oracles (Discord REST reaction reads, Slack thread API)

### I. Crestodian — Rescue Mode Configless-Safe
- TUI fallback alcanzable vía bare `openclaw` cuando el agent path está ROTO
- Muestra model, config validity, gateway reachability, debug actions
- Funciona en git checkouts Y npm installs

### J. SOUL.md — Personality Injection
- Archivo de personalidad dedicado, alta prioridad
- "Molty prompt" para reescribir: strong opinions, no hedging, natural humor, permission to call things out
- "Be the assistant you'd actually want to talk to at 2am"

### K. OpenGrep Security Rulepack
- Compiled `precise.yml` rulepack como regression firewall en CI
- Cada regla con provenance metadata (GHSA ID, advisory URL, detector bucket)
- Rule quality contract: catch vulnerable, be silent on fixed, classify current findings

### L. QA-Lab Runtime Parity Soak + Drift Detection
- Mock JSONL replay fixtures con first-drift reporting
- 100-turn runtime parity soak para Codex/Pi transcript drift
- Live-only long-context watchdog

### M. Channel Docking + Ambient Room Events
- Multi-platform presence con location sharing, broadcast groups
- QR code + explicit code pairing
- Ambient room events: el agente observa y surfacea info relevante sin menciones explícitas

### N. Meeting Notes Plugin — Source-Only External
- Plugin externo (fuera del core npm package)
- Auto-start capture config, manual transcript imports, read-only CLI
- Discord voice como primer live source
- Speaker-labeled transcript sections

### O. Embedding Provider Capability Contract
- Generic embeddingProviders capability + registration API
- Embeddings como provider surface reusable (fuera de memory-specific adapters)
- Session workflow helpers, channel-target routing, poll sender sin SDK facades

---

## IX. FASES DE IMPLEMENTACIÓN

### Fase 1: Extracción (Hermes → v3.0)
- ToolRegistry + Toolset Composition
- ContextCompressor
- Memory Providers
- Gateway multi-canal (api_server primero)
- Cron Scheduler + Kanban + Curator + Checkpoints
- Multi-Provider LLM abstraction

### Fase 2: Integración MCP
- Añadir 80+ nuevos MCP servers por categoría
- Unificar Python tools + MCP tools bajo ToolRegistry

### Fase 3: Generalización
- AgentOrchestrator reemplaza BranchCoordinator
- Skills first-class (reemplaza prompts/*.txt)
- Vigilancia Tecnológica = skill "deep-research-tech"

### Fase 4: Verificación
- Constitution compliance tests
- Pipeline byte-idéntico con flags=false
- healthcheck.py + SSE events mantienen contrato

---

## X. HERMES AGENT — CATÁLOGO COMPLETO DE TOOLS (64+ tools)

> Cada tool se mapea a un módulo de dominio en v3.0. Las tools de Hermes se integran como **tools nativas Python** vía ToolRegistry unificado, coexistiendo con MCP tools externas.

### WEB (toolsets: `web`, `search`)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 1 | `web_search` | Búsqueda web con operadores (site:, filetype:pdf). 5 resultados. 8 backends: Brave, DDGS, SearXNG, Exa, Tavily, Firecrawl, Parallel | **Módulo Deep Research** — search primaria para todas las ramas |
| 2 | `web_extract` | Extracción página→Markdown. PDFs. LLM-summarized si >5000 chars | **Pipeline de extracción** — reemplaza Jina/Fetch readers |
| 3 | `web_crawl` | Crawling interno (no expuesto como tool, API interna) | **Background jobs** vía Cron Scheduler |

### TERMINAL (7 backends)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 4 | `terminal` | Ejecuta comandos en sandbox (local, Docker, SSH, Modal, Daytona, Singularity). Foreground/background. PTY support. | **SandboxExecutionStep** — reemplaza sandbox actual |
| 5 | `process` | Gestiona procesos: list, poll, log, wait, kill, stdin write/submit/close | **ProcessManager** para jobs largos (crawls, batch processing) |

### FILE (4 tools)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 6 | `read_file` | Lectura con paginación offset/limit. Auto-detecta imágenes/videos | **FileSystemGateway** — acceso universal a archivos |
| 7 | `write_file` | Escritura/creación con auto-creación de directorios | **ReportRepository** — persistencia de reportes |
| 8 | `patch` | Ediciones precisas: replace, insert, delete. Fuzzy matching. | **DocumentEditor** — edición incremental de reportes |
| 9 | `search_files` | Búsqueda ripgrep + find por glob. Content y filename mode. | **CodebaseInspector** — search interna de código |

### VISION + VIDEO
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 10 | `vision_analyze` | Análisis de imágenes. Native fast path o fallback a aux LLM | **MultimodalPipeline** — análisis de gráficos, capturas, diagramas |
| 11 | `video_analyze` | Análisis de video vía Gemini multimodal. mp4/webm/mov/avi/mkv ≤50MB | **MediaAnalysis** — análisis de webinars, demos, grabaciones |

### MEDIA GENERATION
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 12 | `image_generate` | Generación vía FAL.ai: FLUX, Recraft, Ideogram, SD 3.5 | **VisualReportGenerator** — gráficos e infografías para reportes |
| 13 | `video_generate` | Generación/edición/extensión de video. Plugin-architected, 0 backends in-tree | **MediaModule** — generación de video-resúmenes |
| 14 | `text_to_speech` | 8+ providers: Edge TTS (gratis), ElevenLabs, OpenAI, MiniMax, Mistral, Gemini, xAI, Piper (44 idiomas) | **AudioNotifier** — alertas de vigilancia por voz |

### BROWSER (12 tools — 3 capas: high-level + CDP + Dialog)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 15 | `browser_navigate` | Navega a URL. Crea sesión en primer uso. CDP override. | **BrowserAgent** — reemplaza Playwright actual con CDP nativo |
| 16 | `browser_snapshot` | Accessibility tree snapshot de la página actual |
| 17 | `browser_click` | Click en elemento por accessibility ref |
| 18 | `browser_type` | Escribe texto en input. Modo composer para rich text |
| 19 | `browser_scroll` | Scroll up/down por viewport height |
| 20 | `browser_back` | Navega atrás en historial |
| 21 | `browser_press` | Envía tecla al navegador |
| 22 | `browser_get_images` | Extrae todas las URLs de imágenes de la página |
| 23 | `browser_vision` | Screenshot + pregunta al modelo de visión. Anotaciones opcionales |
| 24 | `browser_console` | Ve mensajes de consola o evalúa JS |
| 25 | `browser_cdp` | Raw Chrome DevTools Protocol — escape hatch para ops avanzadas |
| 26 | `browser_dialog` | Acepta/descarta diálogos nativos (alert/confirm/prompt) |

### CODE EXECUTION + DELEGATION
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 27 | `execute_code` | Ejecuta Python que llama otras tools vía RPC (UDS o file-based). Colapsa multi-step chains en 1 turno | **ProgrammaticToolCalling** — reemplaza sandbox actual |
| 28 | `delegate_task` | Spawnea subagentes con contexto aislado, toolsets restringidos, terminal propio. Single/batch. Parent bloquea hasta completar | **AgentOrchestrator** — core de la arquitectura v3.0 |

### MEMORY + SESSION
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 29 | `memory` | Memoria persistente cross-session. 2 stores: MEMORY.md (notas del agente) + USER.md (perfil). Frozen snapshot pattern | **MemoryLayer** — reemplaza CrossSessionService. pgvector + mem0 + honcho |
| 30 | `session_search` | Búsqueda FTS5 en sesiones pasadas. 3 modos: discovery, scroll, browse | **SessionHistory** — el agente busca su propia historia antes de investigar |

### PLANNING + INTERACTION
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 31 | `todo` | Gestiona lista de tareas de sesión. Write (merge=false) o update (merge=true por id) | **TaskTracker** — tracking de progreso de investigación |
| 32 | `clarify` | Pregunta al usuario. Multiple choice (≤4 opciones) o open-ended | **UserInteraction** — preguntas de clarificación en Slack/Teams |

### SKILLS (progressive disclosure 3-tier)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 33 | `skills_list` | Lista skills disponibles (nombre + descripción). Tier 1 | **SkillCatalog** — reemplaza prompts/*.txt |
| 34 | `skill_view` | Ve contenido completo: referencias, templates, tags. Tier 2 |
| 35 | `skill_manage` | CRUD de skills. Targeted edits vía old_string/new_string |

### CRON
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 36 | `cronjob` | Gestiona cron jobs: create, list, update, pause, resume, remove, run. Skills, model override, script mode (no_agent), context chaining | **Scheduler** — alertas automáticas, reportes periódicos |

### MESSAGING (multi-plataforma)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 37 | `send_message` | Envía mensajes cross-platform (Telegram, Discord, Slack, SMS, WhatsApp, Matrix, WeChat, Feishu, Yuanbao). Media attachments, channel targeting | **NotificationGateway** — alertas multicanal |

### DISCORD
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 38 | `discord` | fetch_messages, search_members, create_thread. Schema filtrado por bot intents + user allowlist | **DiscordChannel** — canal de notificación empresarial |
| 39 | `discord_admin` | list_guilds, server_info, channels, roles, members, pins, delete_message, add/remove_role |

### HOME ASSISTANT (IoT empresarial)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 40 | `ha_list_entities` | Lista entidades por dominio o área |
| 41 | `ha_get_state` | Estado detallado de una entidad |
| 42 | `ha_list_services` | Servicios disponibles por dominio |
| 43 | `ha_call_service` | Controla dispositivos. Bloques: shell_command, python_script |

### KANBAN (orquestación multi-agente)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 44 | `kanban_show` | Lee estado completo de tarea (row, parents, children, comments, runs, events) | **WorkQueue** — dashboard empresarial de tareas |
| 45 | `kanban_list` | Lista tareas con filtros (status, assignee, tenant, board) |
| 46 | `kanban_complete` | Marca tarea completada con handoff estructurado (result, children, summary) |
| 47 | `kanban_block` | Bloquea tarea para input humano |
| 48 | `kanban_heartbeat` | Señal de liveness durante operaciones largas |
| 49 | `kanban_comment` | Comentario en thread de tarea (handoff channel entre tasks) |
| 50 | `kanban_create` | Crea tarea hija. Idempotency keys, skills, triage mode |
| 51 | `kanban_link` | Vincula dos tareas (relación de dependencia) |
| 52 | `kanban_unblock` | Desbloquea tarea bloqueada |

### COMPUTER USE + MOA + X SEARCH
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 53 | `computer_use` | Control de escritorio macOS en background. 13 acciones: capture, click, drag, scroll, type, key, etc. SOM mode | **DesktopAutomation** — automatización de apps empresariales |
| 54 | `mixture_of_agents` | 4 modelos en paralelo → aggregator sintetiza. 6 retries con exponential backoff | **DeliberativeReasoning** — para decisiones estratégicas complejas |
| 55 | `x_search` | Búsqueda en X/Twitter vía xAI. Dual auth: SuperGrok OAuth o XAI_API_KEY | **SocialIntel** — monitoreo de tendencias en tiempo real |

### FEISHU/LARK (enterprise China)
| # | Tool | Descripción | Integración v3.0 |
|---|------|-------------|-----------------|
| 56 | `feishu_doc_read` | Lectura de documentos Feishu/Lark como texto plano | **FeishuConnector** — integración enterprise stack chino |
| 57 | `feishu_drive_list_comments` | Lista comentarios en documento |
| 58 | `feishu_drive_list_comment_replies` | Lista respuestas a comentario |
| 59 | `feishu_drive_reply_comment` | Responde a comentario |
| 60 | `feishu_drive_add_comment` | Añade comentario a documento |

### YUANBAO (Tencent)
| # | Tool | Descripción |
|---|------|-------------|
| 61 | `yb_query_group_info` | Info de grupo Yuanbao |
| 62 | `yb_query_group_members` | Miembros de grupo |
| 63 | `yb_send_dm` | Mensaje directo |
| 64 | `yb_search_sticker` | Búsqueda de stickers |
| 65 | `yb_send_sticker` | Envío de sticker |

### SPOTIFY
| # | Tool | Descripción |
|---|------|-------------|
| 66 | `spotify_playback` | Control de reproducción |
| 67 | `spotify_devices` | Dispositivos disponibles |
| 68 | `spotify_queue` | Cola de reproducción |
| 69 | `spotify_search` | Búsqueda en catálogo |
| 70 | `spotify_playlists` | Gestión de playlists |
| 71 | `spotify_albums` | Navegación de álbumes |
| 72 | `spotify_library` | Biblioteca guardada |

### DINÁMICOS
| Tipo | Descripción | Integración v3.0 |
|------|-------------|-----------------|
| **MCP tools** | Registradas dinámicamente por cada MCP server (`mcp-*` namespace) | **MCPHub** — conviven con tools nativas bajo ToolRegistry unificado |
| **Plugin tools** | Registradas por plugins en `~/.hermes/plugins/` | **PluginSystem** — extensibilidad enterprise |

---

## XI. HERMES AGENT — CATÁLOGO COMPLETO DE SKILLS (170 skills)

> Las skills de Hermes se integran como **módulos de dominio activables bajo demanda** en v3.0, reemplazando los prompts estáticos `prompts/*.txt`. Sistema de progressive disclosure: tier 1 (lista), tier 2 (ver contenido), tier 3 (editar).

### BUNDLED SKILLS (89) — Organizadas por dominio empresarial

**APPLE ECOSYSTEM (5)** → Integración: módulo `desktop-automation`
| Skill | Función |
|-------|---------|
| `apple-notes` | CRUD de Apple Notes vía memo CLI |
| `apple-reminders` | Recordatorios vía remindctl |
| `findmy` | Tracking de dispositivos Apple |
| `imessage` | iMessage/SMS vía imsg CLI |
| `macos-computer-use` | Desktop automation en background (mouse, teclado, scroll, drag) |

**CODING AGENTS (5)** → Integración: módulo `code-generation`
| Skill | Función |
|-------|---------|
| `claude-code` | Delega coding a Claude Code CLI |
| `codex` | Delega coding a OpenAI Codex CLI |
| `hermes-agent` | Auto-configuración y extensión de Hermes |
| `kanban-codex-lane` | Codex como lane aislado bajo Kanban |
| `opencode` | Delega coding a OpenCode CLI |

**CREATIVE & DESIGN (20)** → Integración: módulo `visual-communication`
| Skill | Función |
|-------|---------|
| `architecture-diagram` | Diagramas SVG dark-themed de arquitectura cloud/infra |
| `ascii-art` | ASCII art: pyfiglet, cowsay, boxes |
| `ascii-video` | Video→ASCII MP4/GIF |
| `baoyu-article-illustrator` | Ilustraciones para artículos (tipo × estilo × paleta) |
| `baoyu-comic` | Cómics de conocimiento (educación, biografía, tutorial) |
| `baoyu-infographic` | Infografías: 21 layouts × 21 estilos |
| `claude-design` | Artefactos HTML one-off (landings, decks, prototipos) |
| `comfyui` | Imágenes/video/audio con ComfyUI: instalar, lanzar, nodos, workflows |
| `creative-ideation` | Generación de ideas vía restricciones creativas |
| `design-md` | Authoring/validación de Google DESIGN.md |
| `excalidraw` | Diagramas hand-drawn (arquitectura, flujo, secuencia) |
| `humanizer` | Humaniza texto: quita AI-isms, añade voz real |
| `manim-video` | Animaciones 3Blue1Brown math/algo con Manim CE |
| `p5js` | Sketches p5.js: arte generativo, shaders, 3D |
| `pixel-art` | Pixel art con paletas de época (NES, Game Boy, PICO-8) |
| `popular-web-designs` | 54 sistemas de diseño reales como HTML/CSS |
| `pretext` | Layout de texto DOM-free para arte tipográfico |
| `sketch` | Mockups HTML throwaway: 2-3 variantes para comparar |
| `songwriting-and-ai-music` | Composición musical + prompts Suno AI |
| `touchdesigner-mcp` | Control de TouchDesigner vía twozero MCP (36 tools nativas) |

**DATA SCIENCE (1)** → Integración: módulo `analytics`
| Skill | Función |
|-------|---------|
| `jupyter-live-kernel` | Python iterativo vía kernel Jupyter live (hamelnb) |

**DEVOPS (3)** → Integración: módulo `orchestration`
| Skill | Función |
|-------|---------|
| `kanban-orchestrator` | Playbook de descomposición + reglas anti-tentación para orquestador |
| `kanban-worker` | Pitfalls, ejemplos, edge cases para workers Kanban |
| `webhook-subscriptions` | Suscripciones webhook: ejecuciones event-driven |

**DOGFOOD (1)**
| Skill | Función |
|-------|---------|
| `dogfood` | QA exploratorio de web apps: bugs, evidencia, reportes |

**EMAIL (1)** → Integración: módulo `communications`
| Skill | Función |
|-------|---------|
| `himalaya` | IMAP/SMTP desde terminal vía Himalaya CLI |

**GAMING (2)**
| Skill | Función |
|-------|---------|
| `minecraft-modpack-server` | Hosting de servidores Minecraft moddeados |
| `pokemon-player` | Juego de Pokémon vía emulador headless + RAM reads |

**GITHUB (6)** → Integración: módulo `devops`
| Skill | Función |
|-------|---------|
| `codebase-inspection` | Inspección de codebases: LOC, lenguajes, ratios (pygount) |
| `github-auth` | Setup de auth GitHub: HTTPS tokens, SSH keys, gh CLI |
| `github-code-review` | Review de PRs: diffs, comentarios inline vía gh CLI |
| `github-issues` | CRUD de issues: crear, triage, etiquetar, asignar |
| `github-pr-workflow` | Ciclo completo PR: branch, commit, open, CI, merge |
| `github-repo-management` | Gestión de repos: clone, create, fork, remotes, releases |

**MCP (1)** → Integración: módulo `mcp-hub`
| Skill | Función |
|-------|---------|
| `native-mcp` | Cliente MCP: conectar servers, registrar tools (stdio/HTTP) |

**MEDIA (5)** → Integración: módulo `media-processing`
| Skill | Función |
|-------|---------|
| `gif-search` | Búsqueda/descarga de GIFs vía Tenor |
| `heartmula` | Generación de canciones desde letras + tags |
| `songsee` | Espectrogramas/features de audio (mel, chroma, MFCC) |
| `spotify` | Control de Spotify: play, search, queue, playlists, dispositivos |
| `youtube-content` | Transcripciones→resúmenes, threads, blogs |

**MLOPS (9)** → Integración: módulo `ai-ml`
| Skill | Función |
|-------|---------|
| `weights-and-biases` | W&B: logging de experimentos, sweeps, model registry |
| `lm-evaluation-harness` | Benchmark de LLMs (MMLU, GSM8K, etc.) |
| `huggingface-hub` | HF CLI: search, download, upload de modelos y datasets |
| `llama-cpp` | Inferencia local GGUF + descubrimiento de modelos en HF Hub |
| `obliteratus` | Abliteración de refusal en LLMs (diff-in-means) |
| `vllm` | Serving high-throughput LLM, OpenAI API, cuantización |
| `segment-anything` | SAM: segmentación zero-shot vía puntos, boxes, máscaras |
| `audiocraft` | MusicGen text-to-music, AudioGen text-to-sound |
| `dspy` | Programas LM declarativos, auto-optimización de prompts, RAG |

**PRODUCTIVITY (9)** → Integración: módulos `office`, `collaboration`, `knowledge`
| Skill | Función |
|-------|---------|
| `airtable` | Airtable REST API: CRUD, filtros, upserts |
| `google-workspace` | Gmail, Calendar, Drive, Docs, Sheets vía gws CLI |
| `linear` | Gestión de issues, proyectos, equipos vía GraphQL |
| `maps` | Geocoding, POIs, rutas, timezones vía OSM/OSRM |
| `nano-pdf` | Edición de PDF con lenguaje natural |
| `notion` | Notion API + ntn CLI: páginas, BD, markdown, Workers |
| `ocr-and-documents` | Extracción de texto de PDFs/escaneos (pymupdf, marker-pdf) |
| `powerpoint` | CRUD de .pptx: decks, slides, notas, templates |
| `teams-meeting-pipeline` | Pipeline de resumen de reuniones Teams vía Graph API |

**RED-TEAMING (1)**
| Skill | Función |
|-------|---------|
| `godmode` | Jailbreak de LLMs: Parseltongue, GODMODE, ULTRAPLINIAN |

**RESEARCH (5)** → Integración: módulo `deep-research`
| Skill | Función |
|-------|---------|
| `arxiv` | Búsqueda de papers por keyword, autor, categoría, ID |
| `blogwatcher` | Monitoreo de blogs y feeds RSS/Atom |
| `llm-wiki` | Wiki de Karpathy: KB interconectada en markdown |
| `polymarket` | Query de mercados de predicción: precios, orderbooks |
| `research-paper-writing` | Escritura de papers ML: diseño→submit (NeurIPS, ICML, ICLR) |

**SOFTWARE DEVELOPMENT (11)** → Integración: módulo `dev-tools`
| Skill | Función |
|-------|---------|
| `debugging-hermes-tui-commands` | Debug de comandos TUI: Python, gateway, Ink UI |
| `hermes-agent-skill-authoring` | Authoring de SKILL.md in-repo: frontmatter, validador |
| `node-inspect-debugger` | Debug Node.js vía --inspect + Chrome DevTools Protocol |
| `plan` | Modo plan: escribe plan markdown a .hermes/plans/, sin ejecutar |
| `python-debugpy` | Debug Python: pdb REPL + debugpy remote (DAP) |
| `requesting-code-review` | Review pre-commit: security scan, quality gates, auto-fix |
| `spike` | Experimentos throwaway para validar ideas antes de construir |
| `subagent-driven-development` | Ejecución de planes vía delegate_task subagentes (review 2-stage) |
| `systematic-debugging` | Debugging de 4 fases: entender bugs antes de arreglar |
| `test-driven-development` | TDD: RED-GREEN-REFACTOR obligatorio |
| `writing-plans` | Escritura de planes de implementación: tareas bite-sized |

**SMART HOME (1)**
| Skill | Función |
|-------|---------|
| `openhue` | Control de luces Philips Hue, escenas, rooms |

**SOCIAL MEDIA (1)** → Integración: módulo `social-intel`
| Skill | Función |
|-------|---------|
| `xurl` | X/Twitter vía xurl CLI: post, search, DM, media, API v2 |

**NOTE-TAKING (1)** → Integración: módulo `knowledge`
| Skill | Función |
|-------|---------|
| `obsidian` | CRUD de notas en Obsidian vault |

**YUANBAO (1)**
| Skill | Función |
|-------|---------|
| `yuanbao` | Grupos Yuanbao: @menciones, info de grupo/miembros |

---

### OPTIONAL SKILLS (81) — Catálogo completo

**AUTONOMOUS AI AGENTS (2)**
| Skill | Función |
|-------|---------|
| `blackbox` | Coding vía Blackbox AI: multi-modelo con judge interno |
| `honcho` | Memoria Honcho: modelado cross-session, multi-perfil, dialéctica |

**BLOCKCHAIN (3)**
| Skill | Función |
|-------|---------|
| `evm` | EVM read-only: wallets, tokens, gas en 8 chains |
| `hyperliquid` | Hyperliquid: mercado, account history, trade review |
| `solana` | Solana: balances, tokens, NFTs, whales, network stats |

**COMMUNICATION (1)**
| Skill | Función |
|-------|---------|
| `one-three-one-rule` | Toma de decisiones: 1 problema, 3 opciones, 1 recomendación |

**CREATIVE (5)**
| Skill | Función |
|-------|---------|
| `blender-mcp` | Control de Blender 3D vía socket: objetos, materiales, animaciones |
| `concept-diagrams` | Diagramas SVG minimalistas con 9 rampas semánticas de color |
| `hyperframes` | Composiciones de video HTML: tarjetas animadas, overlays, shaders |
| `kanban-video-orchestrator` | Pipeline de producción de video multi-agente vía Kanban |
| `meme-generation` | Generación de memes reales: template + texto con Pillow |

**DEVOPS (4)**
| Skill | Función |
|-------|---------|
| `cli` (inference-sh) | 150+ apps AI vía inference.sh CLI |
| `docker-management` | Gestión de Docker: containers, imágenes, volúmenes, Compose |
| `pinggy-tunnel` | Túneles localhost sin instalación sobre SSH |
| `watchers` | Polling RSS, JSON APIs, GitHub con watermark dedup |

**DOGFOOD (1)**
| Skill | Función |
|-------|---------|
| `adversarial-ux-test` | UX testing adversarial: roleplay del usuario más difícil |

**EMAIL (1)**
| Skill | Función |
|-------|---------|
| `agentmail` | Inbox de email dedicado para el agente vía AgentMail |

**FINANCE (8)** → Integración: módulo `finance`
| Skill | Función |
|-------|---------|
| `3-statement-model` | Modelos financieros 3-estados (IS, BS, CF) en Excel |
| `comps-analysis` | Análisis de comparables: métricas operativas, múltiplos |
| `dcf-model` | Valoración DCF institucional: proyecciones, WACC, escenarios Bear/Base/Bull |
| `excel-author` | Workbooks Excel auditables: blue/black/green, fórmulas, named ranges |
| `lbo-model` | Modelos LBO: sources & uses, debt schedule, cash sweep, IRR/MOIC |
| `merger-model` | Modelos de fusión: pro-forma P&L, sinergias, EPS impact |
| `pptx-author` | Decks PowerPoint headless con python-pptx. Parea con excel-author |
| `stocks` | Cotizaciones, historial, búsqueda, comparación, crypto vía Yahoo |

**HEALTH (2)**
| Skill | Función |
|-------|---------|
| `fitness-nutrition` | Planes de gym: 690+ ejercicios (wger), 380K+ comidas (USDA). BMI, TDEE |
| `neuroskill-bci` | NeuroSkill BCI: estado cognitivo/emocional en tiempo real (focus, HRV, sleep staging) |

**MCP (2)**
| Skill | Función |
|-------|---------|
| `fastmcp` | Build/test/inspect/deploy de servidores MCP con FastMCP |
| `mcporter` | Listar, configurar, autenticar, llamar servidores MCP vía mcporter CLI |

**MIGRATION (1)**
| Skill | Función |
|-------|---------|
| `openclaw-migration` | Migración de footprint OpenClaw → Hermes Agent |

**MLOPS (28 habilidades adicionales resumidas):** accelerate, chroma, clip, faiss, flash-attention, guidance, huggingface-tokenizers, instructor, lambda-labs, llava, modal, nemo-curator, peft, pinecone, + 14 más

**PRODUCTIVITY (6):** google-photos, linkedin, microsoft-office, todoist, zapier, zoom

**RESEARCH (6):** google-scholar, pubmed, semantic-scholar, web-scraping, wikipedia, wolfram-alpha

**SECURITY (4):** nmap, sqlmap, wireshark, metasploit

**WEB DEVELOPMENT (7):** bootstrap, django, flask, nextjs, react, svelte, vue

---

### MODELO DE INTEGRACIÓN DE SKILLS EN v3.0

```
┌──────────────────────────────────────────────────┐
│              SKILL MANAGER v3.0                   │
│  Progressive Disclosure: list → view → edit       │
├──────────────────────────────────────────────────┤
│  Fuentes de skills:                               │
│  1. Bundled (skills/ en repo v3.0)                │
│  2. Enterprise (config/skills/ por dominio)       │
│  3. User (custom por cliente)                     │
│  4. Community (marketplace vía clawhub)           │
├──────────────────────────────────────────────────┤
│  Activación:                                      │
│  • Trigger phrases → auto-load skill              │
│  • Agent decide cuándo cargar (on-demand)         │
│  • System prompt inyecta top-5 más usadas         │
│  • Curator auto-maintenance (active→stale→archived)│
├──────────────────────────────────────────────────┤
│  Ejecución:                                       │
│  • Skill = instrucciones + tools permitidas +     │
│    constraints + ejemplos + referencias           │
│  • Reemplaza prompts/*.txt actuales               │
│  • Compatible con Skill Matrix existente          │
└──────────────────────────────────────────────────┘
```

---

## XII. OPENCLAW — CATÁLOGO COMPLETO DE TOOLS (87 tools, 14 providers MCP + 1 REST client)

> Las tools de OpenClaw se integran como **MCP providers** bajo el MCPHub unificado de v3.0. Los 14 providers actuales del Vigilador se expanden con los providers adicionales de OpenClaw + Hermes.

### PROVIDER 1: TAVILY (4 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 1 | `tavily_search` | Búsqueda web optimizada para AI agents | AVANCES, COMERCIAL, OPORTUNIDADES |
| 2 | `tavily_extract` | Extracción de contenido desde URLs | COMERCIAL |
| 3 | `tavily_map` | Mapeo de estructura de sitio | AVANCES, COMERCIAL, OPORTUNIDADES |
| 4 | `tavily_crawl` | Crawling profundo con max_pages | _(nuevo)_ |

### PROVIDER 2: EXA (3 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 5 | `web_search_exa` | Búsqueda semántica empresarial | AVANCES, COMERCIAL, COMPETITIVO, OPORTUNIDADES |
| 6 | `web_fetch_exa` | Fetch de URL |
| 7 | `web_search_advanced_exa` | Búsqueda avanzada con filtros empresa/personas | COMERCIAL, COMPETITIVO |

### PROVIDER 3: JINA (5 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 8 | `read_url` | Extracción single URL → texto | AVANCES, PI_NORMATIVA, RIESGO |
| 9 | `parallel_read_url` | Extracción multi-URL en paralelo |
| 10 | `capture_screenshot_url` | Screenshot de URL |
| 11 | `search_web` | Búsqueda web |
| 12 | `guess_datetime_url` | Estimación de datetime para URL | RIESGO |

### PROVIDER 4: BRAVE (3 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 13 | `brave_web_search` | Búsqueda web vía Brave | RIESGO, COMPETITIVO, OPORTUNIDADES |
| 14 | `brave_news_search` | Búsqueda de noticias | COMERCIAL, COMPETITIVO |
| 15 | `brave_summarizer` | Resumen de resultados de búsqueda |

### PROVIDER 5: FIRECRAWL (7 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 16 | `firecrawl_scrape` | Scraping single-page | RIESGO |
| 17 | `firecrawl_search` | Búsqueda + scrape combinados | AVANCES, COMERCIAL, RIESGO, COMPETITIVO |
| 18 | `firecrawl_map` | Descubrimiento de URLs de sitio | COMPETITIVO |
| 19 | `firecrawl_crawl` | Crawling profundo | RIESGO |
| 20 | `firecrawl_extract` | Extracción estructurada (LLM-powered, con schema) | _(nuevo — clave para datos empresariales)_ |
| 21 | `firecrawl_batch_scrape` | Batch scraping |
| 22 | `firecrawl_check_crawl_status` | Status de job de crawling |

### PROVIDER 6: GOOGLE SCHOLAR (3 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 23 | `search_google_scholar_key_words` | Búsqueda académica por keywords | PI_NORMATIVA |
| 24 | `search_google_scholar_advanced` | Búsqueda avanzada con filtros año |
| 25 | `get_author_info` | Perfil de autor académico |

### PROVIDER 7: ARXIV (6 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 26 | `search_papers` | Búsqueda de papers en arXiv | PI_NORMATIVA |
| 27 | `download_paper` | Descarga de PDF |
| 28 | `read_paper` | Lectura/extracción de texto |
| 29 | `list_papers` | Lista de papers descargados |
| 30 | `summarize_paper` | Resumen de paper |
| 31 | `compare_papers` | Comparación de dos papers |

### PROVIDER 8: FETCH (1 tool)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 32 | `fetch` | Extracción HTML estática (sin JS) | COMERCIAL, RIESGO, COMPETITIVO, OPORTUNIDADES |

### PROVIDER 9: SERPER / GOOGLE (13 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 33 | `google_search` | Búsqueda web Google | AVANCES, PI_NORMATIVA, COMPETITIVO, OPORTUNIDADES |
| 34 | `google_search_news` | Google News |
| 35 | `google_search_scholar` | Google Scholar | PI_NORMATIVA |
| 36 | `google_search_patents` | Google Patents | AVANCES, PI_NORMATIVA, COMPETITIVO, OPORTUNIDADES |
| 37 | `google_search_images` | Google Images |
| 38 | `google_search_videos` | Google Videos |
| 39 | `google_search_maps` | Google Maps |
| 40 | `google_search_places` | Google Places |
| 41 | `google_search_reviews` | Google Reviews |
| 42 | `google_search_shopping` | Google Shopping |
| 43 | `google_search_lens` | Google Lens |
| 44 | `google_search_autocomplete` | Autocompletado de queries |
| 45 | `webpage_scrape` | Scraping de página vía Serper |

### PROVIDER 10: SANDBOX (3 tools — built-in)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 46 | `execute_code` | Ejecuta Python en subproceso aislado (timeout 120s) | TODAS LAS RAMAS |
| 47 | `list_libraries` | Lista librerías pre-instaladas con versiones |
| 48 | `visualize` | Genera visualizaciones: line, bar, scatter, histogram, heatmap, pie. PNG/SVG/PDF |

### PROVIDER 11: MARKITDOWN (1 tool)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 49 | `convert_to_markdown` | Conversión de documentos a Markdown. Soporta PDF, DOCX, PPTX, XLSX, HTML, CSV, JSON, XML, PNG, JPG | _(nuevo — procesamiento universal de documentos)_ |

### PROVIDER 12: MINIMAX IMAGE (1 tool)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 50 | `understand_image` | Análisis de imágenes vía MiniMax vision API (JPEG, PNG, GIF, WebP ≤20MB) | TODAS LAS RAMAS |

### PROVIDER 13: OPENALEX (21 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 51 | `search_works` | Búsqueda de trabajos académicos | AVANCES, PI_NORMATIVA, COMPETITIVO |
| 52 | `get_work` | Obtener trabajo por ID |
| 53 | `get_related_works` | Trabajos relacionados |
| 54 | `search_by_topic` | Búsqueda por tópico |
| 55 | `get_work_citations` | Citas de un trabajo |
| 56 | `get_work_references` | Referencias de un trabajo |
| 57 | `get_citation_network` | Red de citación completa |
| 58 | `get_top_cited_works` | Trabajos más citados en un dominio |
| 59 | `search_authors` | Búsqueda de autores |
| 60 | `search_authors_by_expertise` | Expertos por área |
| 61 | `get_author_profile` | Perfil de autor |
| 62 | `get_author_collaborators` | Red de colaboración |
| 63 | `search_institutions` | Búsqueda de instituciones |
| 64 | `find_review_articles` | Artículos de revisión |
| 65 | `find_seminal_papers` | Papers seminales/landmark |
| 66 | `analyze_topic_trends` | Análisis de tendencias en el tiempo |
| 67 | `compare_research_areas` | Comparación de áreas de investigación |
| 68 | `get_trending_topics` | Tópicos trending actuales |
| 69 | `analyze_geographic_distribution` | Distribución geográfica de investigación |
| 70 | `search_sources` | Búsqueda de venues/publicaciones |
| 71 | `autocomplete_search` | Autocompletado de términos |

### PROVIDER 14: PLAYWRIGHT (16 tools)
| # | Tool | Descripción | Rama v3.0 |
|---|------|-------------|-----------|
| 72 | `browser_navigate` | Navega a URL + snapshot de accesibilidad | COMERCIAL, RIESGO, COMPETITIVO |
| 73 | `browser_navigate_back` | Volver atrás |
| 74 | `browser_snapshot` | Snapshot de accesibilidad de la página |
| 75 | `browser_take_screenshot` | Screenshot (full page opcional) |
| 76 | `browser_pdf_save` | Guardar página como PDF |
| 77 | `browser_click` | Click en elemento por selector |
| 78 | `browser_type` | Escribir texto en elemento |
| 79 | `browser_select_option` | Seleccionar opción de dropdown |
| 80 | `browser_hover` | Hover sobre elemento |
| 81 | `browser_press_key` | Presionar tecla |
| 82 | `browser_wait_for` | Esperar por elemento |
| 83 | `browser_evaluate` | Ejecutar JavaScript en la página |
| 84 | `browser_console_messages` | Ver mensajes de consola |
| 85 | `browser_tabs` | Gestionar pestañas |
| 86 | `browser_network_requests` | Listar todas las requests de red |
| 87 | `browser_network_request` | Detalle de request específica |
| — | **Blocked-access detection** | Detecta HTTP 403/429/503 + CAPTCHA + "access denied"/"blocked" | Built-in en Playwright provider |

### DIRECT REST CLIENT: OPENALEX (non-MCP)
| Método | Descripción |
|--------|-------------|
| `search_works(query, per_page)` | REST directo de OpenAlex ordenado por citation count. Expuesto vía `ScholarlyWorksGateway` |

---

### SKILL MATRIX — Distribución de tools por rama de vigilancia

| Rama | # Tools | Tools clave |
|------|---------|-------------|
| **AVANCES** | 15 | tavily_search, web_search_exa, firecrawl_search, read_url, tavily_map, search_works, analyze_topic_trends, get_citation_network, get_trending_topics, summarize_paper, sandbox(3), understand_image, google_search_patents |
| **COMERCIAL** | 12 | web_search_advanced_exa, brave_news_search, firecrawl_search, fetch, browser_navigate, browser_snapshot, tavily_map, tavily_extract, sandbox(3), understand_image |
| **RIESGO** | 13 | brave_web_search, fetch, browser(4), firecrawl_scrape, firecrawl_crawl, guess_datetime_url, sandbox(3), understand_image |
| **PI_NORMATIVA** | 16 | google_scholar(3), arxiv(6), read_url, search_works, find_seminal_papers, sandbox(3), understand_image, google_search_patents, google_search_scholar |
| **COMPETITIVO** | 16 | web_search_advanced_exa, brave_news_search, firecrawl_search, fetch, browser(3), firecrawl_map, read_url, search_authors_by_expertise, get_author_info, sandbox(3), understand_image, google_search_patents |
| **OPORTUNIDADES** | 11 | tavily_search, web_search_exa, brave_web_search, firecrawl_search, fetch, tavily_map, sandbox(3), understand_image, google_search_patents |

---

## XIII. OPENCLAW — CATÁLOGO COMPLETO DE SKILLS (71 skills)

> Las skills de OpenClaw complementan el catálogo de Hermes con herramientas específicas para productividad personal y niches que Hermes no cubre.

### BUNDLED SKILLS (57)

**APPLE & macOS (7)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `1password` | Gestión de secretos vía 1Password CLI. Nunca secrets en logs | **SecretManager** — alternativa a .env |
| `apple-notes` | CRUD de Apple Notes vía memo CLI | DesktopAutomation |
| `apple-reminders` | Recordatorios vía remindctl | DesktopAutomation |
| `bear-notes` | Bear app notes vía grizzly CLI | Knowledge |
| `imsg` | iMessage/SMS vía terminal | Communications |
| `things-mac` | Things 3: todos, inbox, today, projects, areas, tags | Productivity |
| `peekaboo` | Automatización completa de UI macOS: capture, click, type, drag, scroll, vision (`see`), app/window/menu | **DesktopAutomation** — más completo que computer_use para macOS |

**COMMUNICATION & MESSAGING (5)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `discord` | Message-tool ops: send/read/edit/delete, react, poll, pin, thread, search, presence | **DiscordChannel** |
| `slack` | Slack tool: send/read/edit/delete, react, pin/unpin, list reactions/emoji, member info | **SlackChannel** |
| `wacli` | WhatsApp third-party vía wacli | **WhatsAppChannel** |
| `voice-call` | Voice calls vía plugin (Twilio, Telnyx, Plivo, mock) | **VoiceGateway** |
| `himalaya` | IMAP/SMTP email: list, read, search, compose, reply, forward | **EmailChannel** |

**PRODUCTIVITY & KNOWLEDGE (7)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `notion` | Notion CLI/API: páginas, markdown, BD, comentarios, búsqueda | **KnowledgeBase** |
| `obsidian` | Obsidian vault: CRUD de notas, tasks, links, propiedades, plugins | **KnowledgeBase** |
| `trello` | Gestión de boards, listas, tarjetas vía REST API | **ProjectManagement** |
| `gog` | Google Workspace CLI: Gmail, Calendar, Drive, Contacts, Sheets, Docs | **GoogleWorkspace** |
| `taskflow` | Jobs multi-step durables con owner context, state, waits, child tasks | **WorkflowEngine** — reemplaza Cron básico |
| `taskflow-inbox-triage` | Patrón de triage de inbox con TaskFlow | **WorkflowEngine** |
| `canvas` | Presenta HTML en nodos conectados (Mac/iOS/Android), navega/evalúa/snapshot | **VisualDashboard** |

**SOFTWARE DEVELOPMENT (8)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `coding-agent` | Coding vía Codex, Claude Code, OpenCode, Pi como workers | **CodeGeneration** |
| `github` | GitHub CLI: issues, PRs, CI/check logs, comments, reviews, releases | **DevOps** |
| `gh-issues` | Pipeline issue→PR automatizado: fetch→fix agents→PR→review handling | **DevOps** |
| `spike` | Prototipos throwaway: VALIDATED/PARTIAL/INVALIDATED verdict | **Prototyping** |
| `python-debugpy` | Debug Python: pdb, breakpoint(), post-mortem, debugpy remote | **DevTools** |
| `node-inspect-debugger` | Debug Node.js: inspect, breakpoints, CDP, heap/CPU profiles | **DevTools** |
| `oracle` | Review/debug/refactor con segundo modelo vía oracle CLI | **CodeReview** |
| `skill-creator` | Authoring de AgentSkills: estructura, frontmatter, validación | **SkillManager** |

**SEARCH & RESEARCH (5)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `blogwatcher` | Monitoreo de blogs y feeds RSS/Atom | **DeepResearch** |
| `goplaces` | Google Places API: text search, place details, reviews | **LocationIntel** |
| `weather` | Clima vía wttr.in con formato personalizable | **ContextAwareness** |
| `summarize` | Resumen/transcripción de URLs, YouTube, podcasts, PDFs | **ContentPipeline** |
| `session-logs` | Búsqueda/análisis de logs de sesiones propias vía jq | **SessionHistory** |

**MEDIA & AUDIO (10)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `openai-whisper` | STT local vía Whisper CLI (offline, sin API key) | **AudioPipeline** |
| `openai-whisper-api` | STT cloud vía OpenAI transcriptions API con diarización | **AudioPipeline** |
| `sherpa-onnx-tts` | TTS local offline vía sherpa-onnx (cross-platform) | **AudioNotifier** |
| `sag` | TTS ElevenLabs vía sag CLI con voice character tags | **AudioNotifier** |
| `songsee` | Espectrogramas y visualizaciones de audio | **MediaAnalysis** |
| `spotify-player` | Control Spotify terminal vía spogo/spotify_player | _(wellness/ambient)_ |
| `video-frames` | Extracción de frames/clips de video vía ffmpeg | **MediaProcessing** |
| `meme-maker` | Generación de memes: SVG/PNG con registro de 20 templates | _(engagement)_ |
| `gifgrep` | Búsqueda de GIFs: Tenor/Giphy, TUI browsing, download | _(engagement)_ |
| `diagram-maker` | Diagramas SVG/HTML o Excalidraw: conceptos, arquitectura, flujos | **VisualCommunication** |

**SOCIAL MEDIA (1)**
| Skill | Función |
|-------|---------|
| `xurl` | X/Twitter vía xurl CLI: posts, replies, search, DMs, media, API v2 |

**SMART HOME & IoT (5)**
| Skill | Función |
|-------|---------|
| `openhue` | Luces Philips Hue vía OpenHue CLI |
| `blucli` | Bluesound/NAD audio vía blu CLI |
| `sonoscli` | Sonos speakers vía sonos CLI |
| `eightctl` | Eight Sleep pod vía eightctl CLI |
| `camsnap` | Captura RTSP/ONVIF de cámaras vía camsnap CLI |

**AI/LLM TOOLS (2)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `gemini` | Gemini CLI: prompts one-shot, resúmenes, generación, skills, hooks, MCP | **MultiProvider** — provider adicional |
| `model-usage` | Cost tracking local de Codex/Claude vía CodexBar | **CostMonitor** |

**UTILITIES & DEVOPS (7)**
| Skill | Función | Integración v3.0 |
|-------|---------|-----------------|
| `tmux` | Control de sesiones/panes tmux para CLIs interactivas | **TerminalManager** |
| `nano-pdf` | Edición de PDFs con lenguaje natural | **DocumentEditor** |
| `mcporter` | Gestión de servidores MCP: list, config, auth, call, inspect | **MCPHub** |
| `ordercli` | Foodora CLI: pedidos y tracking | _(niche)_ |
| `healthcheck` | Auditoría de seguridad de hosts OpenClaw | **DevOps** |
| `node-connect` | Diagnóstico de pairing de nodos Android/iOS/macOS | **DevOps** |
| `clawhub` | Registry de skills: search, install, update, publish vía clawhub CLI | **SkillMarketplace** |

---

### EXTENSION SKILLS (14)

**BROWSER & WEB (2)**
| Skill | Función |
|-------|---------|
| `browser-automation` | Loop de operación de browser: multi-step flows, login checks, tab hygiene, stale ref recovery |
| `tavily` | Web search, content extraction con depth/topic/domain controls |

**ACP & ROUTING (1)**
| Skill | Función |
|-------|---------|
| `acp-router` | Ruteo de agentes: Pi, Claude Code, Cursor, Copilot, OpenClaw ACP, OpenCode, Gemini CLI, Qwen, Kiro, Kimi, iFlow, Kilocode |

**FEISHU SUITE (4)**
| Skill | Función |
|-------|---------|
| `feishu-doc` | CRUD de documentos Feishu (read, write, append, create, blocks, tables, images, files) |
| `feishu-drive` | Gestión de cloud storage: list, info, folders, move, delete |
| `feishu-perm` | Gestión de permisos: list, add, remove collaborators. Disabled by default |
| `feishu-wiki` | Navegación de knowledge base: spaces, nodes, create, move, rename |

**QQ BOT SUITE (3)**
| Skill | Función |
|-------|---------|
| `qqbot-channel` | Gestión de canales QQ: guilds, channels, members, announcements, forum posts, schedules |
| `qqbot-media` | Envío/recepción de rich media vía `<qqmedia>` tags |
| `qqbot-remind` | Recordatorios one-time/recurring vía `qqbot_remind` tool |

**MEMORY & WIKI (2)**
| Skill | Función |
|-------|---------|
| `wiki-maintainer` | Mantenimiento de wiki de memoria: search, ingest, compile, lint, bridge import |
| `obsidian-vault-maintainer` | Wiki Obsidian-friendly: wikilinks, frontmatter, CLI commands |

**WORKFLOW & DSL (2)**
| Skill | Función |
|-------|---------|
| `lobster` | Pipeline multi-step determinístico con approval checkpoints |
| `prose` | OpenProse VM: lenguaje de programación para sesiones AI. Multi-agente, state management, compilación |

**DIFFS (1)**
| Skill | Función |
|-------|---------|
| `diffs` | Renderizado de diffs reales (viewer URL, PNG/PDF artifacts) vía `diffs` tool |

---

## XIV. ESTRATEGIA DE INTEGRACIÓN — DE EXTRACCIÓN A IMPLEMENTACIÓN

### Arquitectura de Tool Registry Unificado

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL REGISTRY UNIFICADO v3.0                  │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────────────┐   │
│  │  HERMES TOOLS (64+)  │    │  OPENCLAW MCP TOOLS (87)     │   │
│  │  • Nativas Python    │    │  • Tavily, Exa, Jina, Brave  │   │
│  │  • registry.register │    │  • FireCrawl, Scholar, arXiv │   │
│  │  • Toolset composition│   │  • Serper, Fetch, Markitdown │   │
│  │  • check_fn gating   │    │  • Sandbox, MiniMax, OpenAlex│   │
│  └──────────┬───────────┘    │  • Playwright (16 browser)   │   │
│             │                └──────────────┬───────────────┘   │
│             └───────────────┬───────────────┘                    │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │           AGENT ORCHESTRATOR (delegate_task)             │    │
│  │  • AgentFactory: spawn ANY agent type                    │    │
│  │  • Toolset composition: recursive includes               │    │
│  │  • ContextCompressor: multi-phase summarization          │    │
│  │  • Skill Manager: progressive disclosure 3-tier          │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │         MCP HUB — 100+ servers, 15 categorías            │    │
│  │  Search | DB | Code Exec | Browser | Computer Use        │    │
│  │  Office/Excel/PowerBI | Finance | Legal | CRM            │    │
│  │  CAD/Engineering | Design | Cloud/K8s | Healthcare       │    │
│  │  Documents/Media | Supply Chain | HR | Support           │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Mapeo de Skills → Módulos de Dominio v3.0

| Dominio v3.0 | Skills Hermes | Skills OpenClaw | MCP Servers |
|-------------|---------------|-----------------|-------------|
| **Deep Research** | arxiv, blogwatcher, llm-wiki, polymarket, research-paper-writing, youtube-content | blogwatcher, summarize, session-logs | Tavily, Exa, Jina, Brave, Scholar, arXiv, Serper, OpenAlex |
| **Code Generation** | claude-code, codex, opencode, kanban-codex-lane | coding-agent, github, gh-issues | Sandbox, E2B, Dagger, Piston, MATLAB |
| **Visual Communication** | architecture-diagram, excalidraw, manim-video, p5js, baoyu-*, comfyui, touchdesigner | diagram-maker, canvas | Excalidraw, Mermaid, Figma(×7), ECharts |
| **Office Automation** | powerpoint, excel-author, google-workspace, notion, airtable, linear | gog, notion, trello | Excel MCP, PowerBI, Google Workspace, MS 365 |
| **Communications** | send_message, discord, discord_admin, feishu_*, teams-meeting-pipeline | discord, slack, wacli, voice-call, himalaya | Telephony, CallCenter, AI Call Assistant |
| **Finance** | 3-statement-model, dcf-model, lbo-model, merger-model, stocks, evm, solana | — | Alpha Vantage, EquiVault, DebtStack, MetaTrader 5 |
| **Desktop Automation** | computer_use, macos-computer-use, apple-notes, apple-reminders, findmy, imessage | peekaboo, things-mac, 1password | Computer Use MCP, DesktopCommander, ScreenPilot |
| **DevOps** | docker-management, pinggy-tunnel, watchers, webhook-subscriptions | tmux, healthcheck, node-connect | K8s(×24), Cloudflare, Terraform, Pulumi |
| **AI/ML** | weights-and-biases, lm-eval-harness, huggingface-hub, llama-cpp, vllm, dspy, chroma, pinecone | gemini, model-usage | MCPFlux, ComfyUI Pilot, Fal.ai |
| **Knowledge Management** | obsidian, ocr-and-documents | obsidian, wiki-maintainer, obsidian-vault-maintainer | Markitdown, MinerU, PDFMux |
| **Security** | nmap, sqlmap, wireshark, metasploit | — | AWS Security, pfSense, OpenGrep |
| **IoT/Smart Home** | openhue, modbus, opc-ua | openhue, sonoscli, blucli, eightctl, camsnap | Arduino, ESP RainMaker, MQTT |
| **Media Processing** | gif-search, songsee, heartmula, songwriting | video-frames, meme-maker, gifgrep, openai-whisper, sherpa-onnx-tts, sag, songsee | Whipscribe, Transcribe, Suno, MIDI |

### Flujo de Integración: Tool Call en v3.0

```
Usuario/Agente → ToolRegistry.dispatch("web_search", {query: "AI trends 2026"})
  │
  ├─ 1. Buscar en tools nativas Python (Hermes)
  │     └─ tools/web_tools.py::web_search() → Brave/DDGS/Exa/Tavily
  │
  ├─ 2. Si no encontrada, buscar en MCP servers (OpenClaw providers)
  │     └─ MCPHub.call("tavily_search", {query: "AI trends 2026"})
  │
  ├─ 3. Skill Manager: ¿hay skill activa que modifique el comportamiento?
  │     └─ "deep-research-tech" → añade search_depth=advanced, max_results=20
  │
  ├─ 4. ContextCompressor: ¿contexto cerca del límite?
  │     └─ Sí → prune outputs viejas antes de ejecutar
  │
  └─ 5. Retornar resultado unificado al agente
```

### Referencia cruzada: Hermes ↔ OpenClaw ↔ Vigilador 2.0

| Funcionalidad | Vigilador 2.0 actual | → Hermes | → OpenClaw |
|--------------|---------------------|----------|------------|
| **Búsqueda web** | Tavily, Exa, Jina, Brave, Serper | web_search (8 backends) | tavily_search, brave_web_search, fetch |
| **Scraping** | FireCrawl (7 tools) | web_extract (5 URLs paralelo) | firecrawl_*, read_url, parallel_read_url |
| **Browser** | Playwright (16 tools) | browser_* (12 tools, 3 capas, CDP nativo) | browser_* (16 tools, blocked-access detection) |
| **Code Execution** | Sandbox (3 tools) | execute_code (RPC dual-transport) | execute_code, list_libraries, visualize |
| **Memoria** | CrossSessionService (pgvector) | Memory providers (8 backends, FTS5, frozen snapshot) | wiki-maintainer, session-logs |
| **Orquestación** | BranchCoordinator (6 ramas fijas) | delegate_task + Kanban (9 tools) | taskflow, lobster, prose |
| **Skills** | prompts/*.txt estáticos | Skill system (170 skills, progressive disclosure) | Skill system (71 skills, extension-based) |
| **Multi-canal** | SSE frontend | Gateway (22+ platforms, 6 auth methods) | ChannelPlugin (~30 adapters, multi-auth) |
| **Académico** | OpenAlex (21 tools) | arxiv (búsqueda) | Google Scholar, arXiv (6 tools), OpenAlex REST |
| **Documentos** | Markitdown (1 tool) | ocr-and-documents, nano-pdf | summarize, nano-pdf, convert_to_markdown |
