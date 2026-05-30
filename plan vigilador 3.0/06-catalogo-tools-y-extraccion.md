# 06 — Catálogo de Tools y Extracción

> **SSOT operacional** del set: catálogo definitivo de las 79 capacidades del Vigilador 3.0 + estrategia de extracción (COPY-HERMES / CLONE-UPSTREAM / WRAP-SDK). Cumple decisión #47 del plan maestro original. Es el documento al que apunta cualquier otro del set cuando referencia tools concretas.

> **Corrección vigente**: este catalogo debe alinearse con [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md). Se mantiene como inventario operativo, pero quedan reformuladas las decisiones de persistencia/vectorizacion, quotas, copia monolitica de Hermes/OpenClaw y carga completa de catalogos en contexto.

> **Evolución de `extraction-inventory.md`**: este archivo era `extraction-inventory.md` en el plan original; se renombró a `06-catalogo-tools-y-extraccion.md` para encajar en el set numerado 01-08. Contenido preservado en lo sustancial — solo se refinaron header y referencias cruzadas (decisión D5 esta sesión).

> Cumple constitución del proyecto (`.specify/memory/constitution.md` v1.2.0): DRY (no reescribir lo que existe), Cambios Quirúrgicos (trazabilidad fuente → destino), Pensar Antes de Codificar (validación previa).

> **Conteo oficial** (decisión #77 del plan original): **79 capacidades total** = 40 Tier 1 (Python internalizadas) + 23 Tier 2 (MCPs externos STDIO) + 6 Tier 3 (TS traducidas) + 10 sub-tools `*_local.py`.

> **Fix CQS aplicado** (decisión #81): el `ToolRegistry.list_tools_for_role` solo LEE de `tool_health` table. El circuit breaker y alertas son responsabilidad de `enterprise/observability/health_monitor.py` (proceso separado cada 30s). Cumple CQS + SRP.

> **Stack de persistencia vigente**: PostgreSQL existente para metadata/auditoria/config operacional + **TurboVecIndex como indice vectorial unico del 3.0** + JSONL/YAML/Markdown. SQLite FTS5 queda opcional para busqueda textual de sesiones. pgvector ya no es backup obligatorio ni hay A/B permanente.

> **Integración con el resto del set**: este doc DETALLA las tools. Las **Skills** que las invocan se definen en [04-skills-y-capacidades.md](04-skills-y-capacidades.md). Los **Modos** que filtran qué tools están permitidas se definen en [02-modos-y-personalidades.md](02-modos-y-personalidades.md). Los **Playbooks** que orquestan agentes que usan estas tools en [03-playbooks-y-orquestacion.md](03-playbooks-y-orquestacion.md). Las **políticas** de tool-gating, capability tokens y MCPProcessSupervisor en [08-gobernanza-seguridad-y-operaciones.md](08-gobernanza-seguridad-y-operaciones.md).

---

## Alcance MVP vs roadmap completo (C1)

> **Decisión C1 esta sesión**: el catálogo de 79 capacidades es el **roadmap completo**, pero el **MVP implementa solo ~20 capacidades**. El resto queda documentado en este archivo como roadmap accesible pero **bloqueado** para implementación hasta validar el MVP. Detalle de scope, cronograma y criterios de salida en [00b-mvp-scope-y-cronograma.md](00b-mvp-scope-y-cronograma.md).

### MVP — 20 capacidades activas (F3a)

**Tier 1 Python interno — 4 tools nuevas**:

| Tool | Dominio | Estrategia | Razón MVP |
|---|---|---|---|
| `file_system` | documents | COPY-HERMES `tools/file_tools.py` + `file_operations.py` + `file_state.py` + `file_safety.py` + `redact.py` | Imprescindible para playbooks que generan artefactos |
| `template_render` | documents | NUEVO Python (Jinja2 sobre MD/HTML/DOCX) | Habilita informes/propuestas/contratos |
| `docx_generate` | documents | NUEVO Python (python-docx) | Entregables empresariales |
| `pdf_generate` | documents | NUEVO Python (WeasyPrint) | Entregables empresariales |

**Tier 2 MCPs externos STDIO — 16 MCPs** (15 preservados del 2.0 + 1 nuevo):

| MCP | Dominio | Estado | Origen |
|---|---|---|---|
| tavily, exa, brave, serper | search | Preservado del 2.0 | `infra/mcp/mcp-providers.json` existente |
| jina, firecrawl, fetch, playwright | web | Preservado del 2.0 | `infra/mcp/mcp-providers.json` existente |
| google_scholar, arxiv, openalex, serper_patents | research | Preservado del 2.0 | `infra/mcp/mcp-providers.json` existente |
| markitdown | documents | Preservado del 2.0 | `infra/mcp/mcp-providers.json` existente |
| sandbox | code (dominio diferido pero MCP activo) | Preservado del 2.0 | `infra/mcp/mcp-providers.json` existente |
| minimax-image | media (dominio diferido pero MCP activo) | Preservado del 2.0 | `infra/mcp/mcp-providers.json` existente |
| **`google-workspace-mcp`** | productivity (dominio diferido pero MCP activo) | **NUEVO MVP** | Tier 2 STDIO. Gmail + Calendar + Drive + Docs + Sheets + Forms en un solo MCP. Declarar en `config/mcp/external.yaml` |

**Dominios MVP activos** (con tools nuevas implementadas):
- ✅ `search` — núcleo del 2.0
- ✅ `web` — núcleo del 2.0
- ✅ `research` — núcleo del 2.0
- ✅ `documents` — 4 tools nuevas Tier 1

**Dominios con MCPs activos pero sin tools nuevas Tier 1 en MVP**:
- 🟡 `productivity` — Google Workspace MCP cubre lo esencial
- 🟡 `code` — `sandbox` del 2.0 sigue activo

**Dominios diferidos a roadmap** (documentación conservada en este archivo, NO implementar en MVP): `desktop`, `crm`, `communication`, `finance`, `meetings`, `people`, `personalization`, `design`, `engineering`, `media`, `analytics`.

### Tiers diferidos a roadmap completo

| Tier | Estado MVP | Razón |
|---|---|---|
| Tier 1 (otras ~36 tools de los 13 dominios diferidos) | ⏸ Roadmap | Esperar validación MVP |
| Tier 2 (resto de ~7 MCPs externos) | ⏸ Roadmap | Solo google-workspace-mcp se añade en MVP |
| **Tier 3** (6 TS traducidos) | ⏸ Roadmap | Documentación conservada, archivos placeholder no se crean |
| **Sub-tools `*_local.py`** (10 wrappers Win COM) | ⏸ Roadmap | Documentación conservada, archivos placeholder no se crean |

### Lo que NO se elimina del documento (C1.2)

Aunque sólo se implementan 20 capacidades en MVP, **este archivo conserva toda la documentación** de las 79 capacidades originales. Razones:
1. Cumple constitución principio 5 (trazabilidad).
2. Facilita activar dominios post-MVP sin tener que re-descubrir decisiones.
3. Permite al `skill_curator` (post-MVP) referenciar el catálogo completo aunque no esté implementado.
4. Los marketplaces externos (`K-Dense-AI`, `agency-agents`) pueden referenciar tools del roadmap completo desde día 1.

**Regla de implementación**: las secciones marcadas con badge ⏸ "Roadmap (post-MVP)" en este archivo NO se materializan en código durante F3a. Sus sprints (en §5 más abajo) se reprograman para F3b.

---

## Propósito

Listar qué código se puede **copiar/clonar/instalar** desde fuentes externas para no reimplementar lo que ya existe. Cada entrada declara: origen, destino, estrategia, esfuerzo, ownership, estado, licencia, healthcheck, credenciales, modo de actualizacion y adaptaciones requeridas.

**Fuentes auditadas**:
- Hermes Agent — `documentation/hermes agent/hermes-agent/` (repo Python completo).
- OpenClaw — `documentation/openclaw/openclaw/` (repo TypeScript completo).
- READMEs MCP individuales en `documentation/<mcp>/`.
- Catálogos masivos `documentation/README_mcp_6.md` (737 KB) y `README_mcp_7.md` (284 KB).
- `v3-enterprise-toolkit-extraction.md` (clasificación previa, deprecada en raíz del set).

**Convención de estrategias** (del [01-vision-y-arquitectura.md](01-vision-y-arquitectura.md) §Stack tecnológico):
- **COPY-HERMES**: copiar el archivo `.py` de Hermes a `enterprise/tooling/builtin/<dominio>/` adaptando imports y namespaces.
- **CLONE-UPSTREAM**: clonar el repo upstream (TS/JS/otro), traducir a Python si aplica, encapsular en clase `BuiltinTool`.
- **WRAP-SDK**: usar el SDK oficial Python del proveedor desde PyPI; solo escribir clase `BuiltinTool` que envuelve.

**Regla C0**: COPY-HERMES no significa pegar monolitos. Antes de entrar al core, cada archivo externo se divide en cliente, schemas, normalizadores, politicas, cache y wrapper. Preferencia: modulos de 300-400 LOC o menos, con tests unitarios por modulo y atribucion/licencia.

---

## 0. Contrato SSOT para tools y MCPs

Cada tool/MCP del catalogo debe tener un registro unico con estos campos:

| Campo | Uso |
|---|---|
| `id` | Nombre estable del tool/MCP/capability namespace. |
| `domain` | Dominio funcional: search, documents, analytics, optimization, artifacts, etc. |
| `source` | Hermes, OpenClaw, SDK, MCP upstream, nuevo, Claude local. |
| `strategy` | WRAP-SDK, COPY-MODULARIZED, MCP-EXTERNO, TRANSLATE-THIN, NUEVO. |
| `runtime` | Python local, process STDIO MCP, REST SDK, local app bridge. |
| `status` | proposed, active, deprecated, blocked, maintenance_pending. |
| `owner` | Quien mantiene el wrapper/adaptador. |
| `license` | Licencia y atribucion. |
| `capabilities` | Lista corta de verbs expuestos. |
| `requires_key` / `env_var` | Gating por credenciales. |
| `requires_local_app` | App/binario requerido si aplica. |
| `healthcheck` | Prueba barata para saber si aparece en discovery. |
| `update_policy` | pinned, weekly-check, manual-only, upstream-watch. |

El `ToolRegistry` expone primero solo metadata corta. La ficha completa y docs largos se cargan solo para candidatos top-k.

---

## 1. Hermes — código copiable (validado leyendo headers reales)

### 1.1 Archivos validados directamente

| Archivo origen | LOC | Validación | Adaptación crítica |
|---|---|---|---|
| `tools/web_tools.py` | 1561 | ✅ Multi-backend (Exa, Firecrawl, Parallel, Tavily) confirmado. Usa OpenRouter + Gemini 3 Flash para LLM processing | Reemplazar OpenRouter→MiniMax. Traer también `plugins/web/firecrawl/provider.py` y resto de `plugins/web/*` |
| `tools/file_tools.py` | 1177 | ✅ File ops con cap de chars (100k default), paginación, safety guards | Traer `agent/file_safety.py` + `agent/redact.py`. Reemplazar `hermes_cli.config` por `config/settings.py` propio |
| `tools/computer_use_tool.py` | 40 | ⚠️ **Solo shim**. El código real está en `tools/computer_use/` (schema.py, tool.py, backend.py, cua_backend.py). **Solo soporta macOS via `cua-driver`** | Reescribir `backend.py` con `pyautogui` + `pygetwindow` + `mss` para Windows 11. Conservar schema. Cambiar `cua_backend.py` → `windows_backend.py` |
| `tools/memory_tool.py` | ~400 | ✅ Frozen snapshot pattern explícito. **Ya soporta Windows** (msvcrt fallback en lugar de fcntl) | Reemplazar `hermes_constants.get_hermes_home()` por path config propio `~/.vigilador/memories/` |
| `tools/mixture_of_agents_tool.py` | ~250 | ✅ MoA basado en paper arXiv:2406.04692. **Hardcoded** a OpenRouter + claude-opus-4.6 + gemini-3-pro + gpt-5.4 + deepseek-v3.2 | **Reescritura sustancial**: catálogo de modelos → solo MiniMax M-2.7 (3-4 instancias con temperaturas distintas) + agregador M-2.7. Reemplazar `openrouter_client` por `minimax_client` |
| `tools/terminal_tool.py` | ~600 | ✅ 7 backends confirmados (local, docker, modal, vercel_sandbox, ssh, daytona, singularity) | Traer carpeta `tools/environments/` completa (10 archivos). Necesita `utils.env_var_enabled` |
| `tools/browser_tool.py` | ~800 | ⚠️ **Depende de CLI externa `agent-browser`** (no Python puro) + Browserbase/Browser Use cloud accounts | **Decisión pendiente**: (a) bundlear `agent-browser` CLI como dep, o (b) reescribir con `playwright-python` directo. Recomendado (b) — menos deps externas, ya tenemos Playwright en MCPs |
| `tools/mcp_tool.py` | ~600 | ✅ Cliente MCP completo: stdio + HTTP/StreamableHTTP + SSE, sampling, parallel tool calls | Solo cambiar config path: `~/.hermes/config.yaml` → `~/.vigilador/config.yaml` |
| `tools/session_search_tool.py` | ~200 | ✅ 3 modos sobre SQLite FTS5 (DISCOVERY/SCROLL/BROWSE). **Sin LLM cost** | **Decisión pendiente sobre el plan**: usar SQLite FTS5 (Hermes ready, más simple) en lugar de Postgres tsvector (lo que el plan §6 dice). Recomendado SQLite por DRY |
| `tools/credential_files.py` | ~180 | ⚠️ **NO es Fernet manager** — es registry de paths a montar en sandboxes remotos | Escribir Fernet manager propio para `~/.vigilador/credentials/`. Hermes usa AES-GCM solo en mensajería WeCom (no aplica) |

### 1.2 Archivos adicionales identificados (inventario inicial, no validados línea por línea)

Estos archivos están en `documentation/hermes agent/hermes-agent/tools/` y según el inventario inicial son copiables. **Antes de copiar cada uno, validar header + dependencias**, como hicimos con los 10 de §1.1.

#### Búsqueda + Web
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/x_search_tool.py` | ~300 | research/ | COPY-HERMES (depende de xAI key — opcional) |
| `tools/browser_cdp_tool.py` | ~400 | web/ | COPY-HERMES (raw CDP) |
| `tools/browser_camofox.py` | ~250 | web/ | Descartar (anti-bot premium, no necesario v3.0) |
| `tools/browser_dialog_tool.py` | ~200 | web/ | COPY-HERMES (dialog supervisor) |
| `tools/browser_supervisor.py` | ~300 | web/ | COPY-HERMES (WebSocket persistente CDP) |

#### Documentos
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/file_operations.py` | ~400 | desktop/ | COPY-HERMES (ShellFileOperations abstraction) |
| `tools/file_state.py` | ~150 | desktop/ | COPY-HERMES (state tracking) |
| `tools/binary_extensions.py` | ~80 | desktop/ | COPY-HERMES (utility) |
| `tools/feishu_doc_tool.py` | ~250 | productivity/ | Descartar (Feishu/Lark no es target LATAM) |
| `tools/feishu_drive_tool.py` | ~350 | productivity/ | Descartar |

#### Ejecución
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/code_execution_tool.py` | ~350 | code/ | COPY-HERMES (complementa e2b) |
| `tools/process_registry.py` | ~300 | infra/ | COPY-HERMES (process lifecycle = base para SubagentRegistry) |
| `tools/cronjob_tools.py` | ~200 | scheduling/ | COPY-HERMES (base del cron de Dreaming) |
| `tools/environments/*.py` | ~10 archivos | infra/environments/ | COPY-HERMES (multi-backend execution) |

#### Comunicación
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/discord_tool.py` | ~400 | communication/ | Descartar v3.0 (no en canales prioritarios) |
| `tools/send_message_tool.py` | ~250 | communication/ | COPY-HERMES (cross-channel routing — útil para `send_message` tool) |
| `tools/homeassistant_tool.py` | ~300 | Descartar v3.0 | IoT no es scope empresarial |
| `tools/voice_mode.py` | ~200 | Descartar v3.0 | Voice no es scope inicial |
| `tools/transcription_tools.py` | ~250 | meetings/ | COPY-HERMES (útil para Teams/Zoom transcripts custom) |
| `tools/tts_tool.py` | ~200 | Descartar v3.0 | TTS no requerido inicial |

#### Memoria + Skills
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/skills_tool.py` | ~350 | enterprise/skills/ | COPY-HERMES (sustituye SkillRegistry custom del plan) |
| `tools/skill_manager_tool.py` | ~300 | enterprise/skills/ | COPY-HERMES (lifecycle) |
| `tools/skills_hub.py` | ~250 | enterprise/skills/ | COPY-HERMES (discovery) |
| `tools/skill_provenance.py` | ~150 | enterprise/skills/ | COPY-HERMES (auditoría origen skill) |
| `tools/skill_usage.py` | ~200 | enterprise/skills/ | COPY-HERMES (tracking usado por skill_curator de Dreaming) |
| `tools/todo_tool.py` | ~250 | enterprise/skills/ | COPY-HERMES |

#### Seguridad
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/url_safety.py` | ~300 | enterprise/governance/ | COPY-HERMES (URL validator) |
| `tools/website_policy.py` | ~250 | enterprise/governance/ | COPY-HERMES (robots.txt respector) |
| `tools/path_security.py` | ~200 | enterprise/governance/ | COPY-HERMES (path traversal) |
| `tools/osv_check.py` | ~200 | enterprise/governance/ | COPY-HERMES (vuln scanner) |
| `tools/tirith_security.py` | ~250 | Opcional | Premium service, evaluar más tarde |
| `tools/schema_sanitizer.py` | ~200 | enterprise/tooling/ | COPY-HERMES (JSON schema utils) |
| `tools/path_security.py` | (ya listado) | | |

#### Approvals + Interrupts (clave para §16 del plan)
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/approval.py` | ~150 | enterprise/governance/ | COPY-HERMES (base del approval workflow) |
| `tools/interrupt.py` | ~180 | enterprise/governance/ | COPY-HERMES (graceful shutdown) |
| `tools/clarify_tool.py` | ~200 | code/ | COPY-HERMES (pregunta al usuario con opciones) |
| `tools/clarify_gateway.py` | ~150 | code/ | COPY-HERMES (gateway para clarify) |
| `tools/slash_confirm.py` | ~100 | enterprise/governance/ | COPY-HERMES |
| `tools/skills_guard.py` | ~150 | enterprise/governance/ | COPY-HERMES (guardrails de skills) |

#### Microsoft Graph (clave para ms365 + meetings/teams)
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/microsoft_graph_auth.py` | ~250 | productivity/ + meetings/ | COPY-HERMES (OAuth MS Graph completo) |
| `tools/microsoft_graph_client.py` | ~400 | productivity/ + meetings/ | COPY-HERMES (cliente HTTP MS Graph) |
| `tools/mcp_oauth.py` | ~200 | enterprise/auth/ | COPY-HERMES (OAuth flow para MCPs) |
| `tools/mcp_oauth_manager.py` | ~250 | enterprise/auth/ | COPY-HERMES (manager de tokens MCP) |

#### Misc útiles
| Archivo | Tamaño aprox | Categoría destino | Estrategia |
|---|---|---|---|
| `tools/lazy_deps.py` | ~150 | enterprise/tooling/ | COPY-HERMES (lazy import — útil para tool-gating §6.7) |
| `tools/debug_helpers.py` | ~200 | enterprise/observability/ | COPY-HERMES (debug utilities) |
| `tools/tool_output_limits.py` | ~180 | enterprise/tooling/ | COPY-HERMES (output truncation) |
| `tools/patch_parser.py` | ~400 | code/ + documents/ | COPY-HERMES (diff/patch parsing — útil para template_render diff) |
| `tools/fuzzy_match.py` | ~150 | desktop/ | COPY-HERMES (fuzzy text match — útil para file_system.patch con fuzzy_match) |
| `tools/budget_config.py` | ~120 | enterprise/observability/ | REFERENCIA para telemetria de costos; **no** quota manager por usuario en version de prueba |
| `tools/checkpoint_manager.py` | ~300 | enterprise/orchestration/ | COPY-HERMES (versionado tipo Git — útil para prompt_versions §12.9) |
| `tools/registry.py` | ~250 | enterprise/tooling/ | COPY-HERMES (tool registry pattern — base del ToolRegistry) |
| `tools/managed_tool_gateway.py` | ~300 | enterprise/tooling/ | COPY-HERMES (gateway pattern) |

#### Descartados explícitamente para v3.0
| Archivo | Razón |
|---|---|
| `tools/feishu_*` | Feishu/Lark no es target LATAM |
| `tools/yuanbao_tools.py` | Tencent Yuanbao no aplica |
| `tools/discord_tool.py` | No en canales prioritarios v3.0 |
| `tools/homeassistant_tool.py` | IoT fuera de scope |
| `tools/voice_mode.py`, `tts_tool.py` | Voice fuera de scope inicial |
| `tools/x_search_tool.py` | xAI no requerido (research suficiente con otros) |
| `tools/browser_camofox.py` | Anti-bot premium |
| `tools/openrouter_client.py`, `xai_http.py` | Reemplazados por `minimax_client.py` |

### 1.3 Archivos top-level Hermes (orchestration)

| Archivo | Tamaño | Reusable | Adaptación |
|---|---|---|---|
| `run_agent.py` | ~500 | **PARCIAL** — patrón de agent loop útil | Reescribir parcial: el `OrchestratorService` 2.0 ya cubre lifecycle |
| `toolsets.py` | ~200 | **SÍ** | COPY-HERMES (toolset composition) |
| `model_tools.py` | ~300 | **PARCIAL** | Plan dice solo MiniMax — no necesitamos multi-provider router |
| `batch_runner.py` | ~400 | **PARCIAL** | Útil para Dreaming `proactive_preparation` paralelo |
| `cli.py` | grande | **NO** | UI-heavy, plan descarta CLI pública |
| `hermes_constants.py` | ~100 | **NO** | Constantes hermes-específicas, escribir propias |

---

## 2. OpenClaw — código copiable

**Conclusión general**: prácticamente **nada vale la pena traducir** TS→Python. La mayoría de adapters tienen SDK Python oficial. OpenClaw sirve como **referencia conceptual** para 3 cosas:

| Componente | Uso | Estrategia |
|---|---|---|
| `extensions/codex/src/app-server/computer-use.ts` | Hard-blocks + vision routing | **REFERENCIA**. Base de implementación: Hermes |
| `extensions/active-memory/` + `memory-core/` + `memory-lancedb/` | Patrones de memoria con LanceDB | **REFERENCIA**. Plan usa TurboVecIndex + metadata relacional — no se traduce |
| Patrones de "Dreaming" / fases biológicas | Conceptos en docs | **REFERENCIA conceptual** ya incorporada en plan §10 |

**Adapters de OpenClaw que ya tienen SDK Python (NO traducir)**:

| OpenClaw extension | SDK Python | Acción |
|---|---|---|
| `brave/` | `python-brave` | Usar SDK directo |
| `exa/` | `exa-py` | Usar SDK directo |
| `firecrawl/` | `firecrawl-py` | Usar SDK directo |
| `discord/` | `discord.py` | (descartado v3.0) |
| `feishu/` | `lark-oapi` | (descartado v3.0) |
| `google/` | `google-api-python-client` | Usar SDK directo |
| `microsoft/` | `msgraph-sdk` | Usar SDK directo |
| `anthropic/`, `openai/`, `deepseek/`, `cerebras/`, `mistral/` | Respectivos SDKs | (no aplica — solo MiniMax) |
| `deepgram/`, `elevenlabs/`, `azure-speech/` | Respectivos SDKs | (descartado v3.0) |

---

## 3. MCPs upstream — matriz de adquisición

### 3.1 Search & Web (categoría más madura)

| Tool del plan | Hay SDK Python? | Repo upstream relevante | Estrategia final |
|---|---|---|---|
| tavily | ✅ `tavily-python` | `tavily-ai/tavily-python` | WRAP-SDK |
| exa | ✅ `exa-py` | `exa-labs/exa-py` | WRAP-SDK |
| brave | ❌ (solo TS MCP) | `brave/brave-search-mcp-server` (TS) | CLONE-UPSTREAM (traducir HTTP client a `httpx`) |
| firecrawl | ✅ `firecrawl-py` | `firecrawl-mendable/firecrawl-py` | WRAP-SDK |
| jina | ❌ (REST directa) | API `r.jina.ai`, `s.jina.ai` | WRAP-SDK (httpx contra REST) |
| fetch | ✅ `mcp-server-fetch` o httpx puro | — | WRAP-SDK |
| playwright | ✅ `playwright` Python | `microsoft/playwright-python` | WRAP-SDK |
| markitdown | ✅ `markitdown` PyPI | `microsoft/markitdown` | WRAP-SDK |
| mineru | ✅ es Python | `opendatalab/MinerU` | WRAP-SDK (no CLONE — Python directo) |
| arxiv | ✅ `arxiv` PyPI | `lukasschwab/arxiv.py` | WRAP-SDK |
| openalex | ✅ `pyalex` | `J535D165/pyalex` | WRAP-SDK |

**Cambio importante respecto al plan**: `mineru` pasa de CLONE-UPSTREAM a WRAP-SDK porque ya es Python puro.

### 3.2 Productivity + Office

| Tool del plan | SDK Python | Notas |
|---|---|---|
| google_workspace | ✅ `google-api-python-client` + `google-auth` | WRAP-SDK. Incluye Gmail/Calendar/Docs/Sheets/Drive/Forms con la misma librería |
| ms365 | ✅ `msgraph-sdk` (Microsoft official) | WRAP-SDK. Cubre Outlook/Teams/OneDrive/OneNote |
| notion | ✅ `notion-client` | WRAP-SDK |
| linear | ❌ (GraphQL directo) | WRAP-SDK con `gql` |

### 3.3 CRM + Communication + Marketing

| Tool del plan | SDK Python | Notas |
|---|---|---|
| hubspot | ✅ `hubspot-api-client` (oficial) | WRAP-SDK |
| salesforce | ✅ `simple-salesforce` | WRAP-SDK |
| apollo | ❌ (REST) | WRAP-SDK con `httpx` |
| slack | ✅ `slack-sdk` (Slack Bolt) | WRAP-SDK |
| telegram_tool | ✅ `python-telegram-bot` | WRAP-SDK + reuso del adapter §9 |
| whatsapp_tool | ❌ (Cloud API REST de Meta) | WRAP-SDK con `httpx` |
| mailchimp | ✅ `mailchimp-marketing` | WRAP-SDK |

### 3.4 Finance

| Tool del plan | SDK Python | Notas |
|---|---|---|
| excel | ✅ `openpyxl` + `pandas` (no necesita MCP externo) | WRAP-SDK |
| power_bi | ❌ (REST + Azure auth) | WRAP-SDK con `azure-identity` + httpx contra Power BI REST API |
| quickbooks | ✅ `python-quickbooks` | WRAP-SDK |
| plaid | ✅ `plaid-python` | WRAP-SDK |

### 3.5 Meetings

| Tool del plan | SDK Python | Notas |
|---|---|---|
| teams.py | ✅ `msgraph-sdk` (extensión sobre ms365) | WRAP-SDK. Online Meetings + Transcripts API |
| zoom.py | ✅ `pyzoom` o REST API directo | WRAP-SDK |

### 3.6 People + Research + Code + Desktop + Personalization

| Tool | SDK Python | Notas |
|---|---|---|
| bamboohr | ❌ (REST) | WRAP-SDK con `httpx` |
| zendesk | ✅ `zenpy` | WRAP-SDK |
| arxiv | ✅ `arxiv` | WRAP-SDK |
| openalex | ✅ `pyalex` | WRAP-SDK |
| e2b_sandbox | ✅ `e2b` | WRAP-SDK |
| kanban | (Hermes) | COPY-HERMES (`tools/kanban_tools.py`) |
| delegate | (Hermes) | COPY-HERMES (`tools/delegate_tool.py`) |
| clarify | (Hermes) | COPY-HERMES (`tools/clarify_tool.py` + `clarify_gateway.py`) |
| computer_use | (Hermes + adaptación Windows) | COPY-HERMES (carpeta `tools/computer_use/`) |
| file_system | (Hermes) | COPY-HERMES (`tools/file_tools.py` + deps) |
| writing_style | (Nuevo, no existe en Hermes/OpenClaw) | NUEVO (no hay base) |

### 3.7 Documents (templates) — todos WRAP-SDK Python puro

| Tool | SDK Python |
|---|---|
| template_render | `jinja2` + `docxtpl` |
| pdf_generate | `weasyprint` + `reportlab` |
| docx_generate | `python-docx` + `docxtpl` |
| pptx_generate | `python-pptx` |

---

## 4. Conteo final por estrategia

| Estrategia | Cantidad | Trabajo estimado |
|---|---|---|
| **COPY-HERMES** | ~30 archivos | Bajo: 1-2 días por archivo (copiar + ajustar imports + tests). Total ~6 sem |
| **CLONE-UPSTREAM** | 1 (solo brave) | Medio: traducir TS HTTP client a `httpx` Python. ~3 días |
| **WRAP-SDK** | ~32 tools | Bajo: instalar PyPI + escribir wrapper `BuiltinTool`. 1-2 días por tool. Total ~7 sem |
| **NUEVO** (sin base reusable) | 4 (writing_style, COMPANY parser, dreaming proactive_preparation, complexity_classifier) | Medio: requieren diseño + implementación + tests. ~4 sem |

**Total estimado de F3 (catálogo de tools)** con esta estrategia: **~17-20 semanas** vs estimación previa del plan de 8 semanas para F3.

**Recomendación**: revisar el plan principal y ampliar F3 a 4-5 meses. La buena noticia es que el plan asumía construir desde cero muchos componentes que ya existen — el reuso reduce trabajo neto en ~40% comparado con escribir todo, pero el catálogo es más grande de lo que parecía.

---

## 5. Orden sugerido de extracción (por dependencias)

### Sprint A (primero — base mínima sin dependencias externas)
1. `tools/registry.py` → `enterprise/tooling/tool_registry.py` (base del catálogo)
2. `tools/lazy_deps.py` → `enterprise/tooling/lazy_deps.py` (requerido por tool-gating)
3. `tools/schema_sanitizer.py` → `enterprise/tooling/schema_sanitizer.py`
4. `tools/tool_output_limits.py` → `enterprise/tooling/output_limits.py`
5. `tools/debug_helpers.py` → `enterprise/observability/debug.py`

### Sprint B (file ops + security)
6. `tools/binary_extensions.py` → `enterprise/tooling/builtin/desktop/_binary_extensions.py`
7. `tools/path_security.py` → `enterprise/governance/path_security.py`
8. `tools/url_safety.py` → `enterprise/governance/url_safety.py`
9. `tools/website_policy.py` → `enterprise/governance/website_policy.py`
10. `tools/file_state.py` + `file_operations.py` + `file_tools.py` → `enterprise/tooling/builtin/desktop/file_system.py` (con `agent/file_safety.py` + `agent/redact.py`)
11. `tools/fuzzy_match.py` → `enterprise/tooling/builtin/desktop/_fuzzy_match.py`
12. `tools/patch_parser.py` → `enterprise/tooling/builtin/code/_patch_parser.py`

### Sprint C (memory + sessions + skills + cron)
13. `tools/memory_tool.py` → `enterprise/memory/frozen_snapshot.py`
14. `tools/session_search_tool.py` → `enterprise/memory/fts_search.py` (opcional con SQLite FTS5 si aporta valor a busqueda textual)
15. `tools/skills_tool.py` + `skill_manager_tool.py` + `skills_hub.py` + `skill_provenance.py` + `skill_usage.py` + `skills_guard.py` → `enterprise/skills/`
16. `tools/todo_tool.py` → `enterprise/skills/todo.py`
17. `tools/cronjob_tools.py` → `enterprise/dreaming/scheduler.py` (base)

### Sprint D (orchestration + approvals)
18. `tools/process_registry.py` → `enterprise/orchestration/subagent_registry.py`
19. `tools/checkpoint_manager.py` → `enterprise/orchestration/checkpoint_manager.py` (base de prompt_versions)
20. `tools/approval.py` + `interrupt.py` + `slash_confirm.py` + `clarify_gateway.py` → `enterprise/governance/approvals/`
21. `tools/clarify_tool.py` → `enterprise/tooling/builtin/code/clarify.py`
22. `tools/budget_config.py` → `enterprise/observability/cost_limits.py` (referencia para telemetria/costos; sin quotas por usuario)
23. `tools/managed_tool_gateway.py` → `enterprise/tooling/gateway.py`
24. `tools/toolsets.py` → `enterprise/tooling/toolsets.py`

### Sprint E (auth + MCP client)
25. `tools/mcp_tool.py` → `enterprise/tooling/mcp_client.py` (coexiste; **no reemplaza** el `infra/mcp/execution_client.py` del 2.0)
26. `tools/mcp_oauth.py` + `mcp_oauth_manager.py` → `enterprise/auth/oauth/`
27. `tools/microsoft_graph_auth.py` + `microsoft_graph_client.py` → `enterprise/auth/microsoft/`

### Sprint F (terminal + execution)
28. `tools/environments/*.py` (10 archivos) → `enterprise/infra/environments/`
29. `tools/terminal_tool.py` → `enterprise/tooling/builtin/code/terminal.py`
30. `tools/code_execution_tool.py` → `enterprise/tooling/builtin/code/sandbox.py`

### Sprint G (browser + computer use)
31. `tools/browser_supervisor.py` + `browser_dialog_tool.py` + `browser_cdp_tool.py` → `enterprise/tooling/builtin/web/_browser_infra/`
32. **Decisión**: traer `browser_tool.py` con `agent-browser` CLI dep, **O** reescribir con `playwright-python` directo
33. `tools/computer_use/` (4 archivos) → `enterprise/tooling/builtin/desktop/computer_use/` + reescribir `backend.py` para Windows

### Sprint H (web search multi-backend)
34. Traer `plugins/web/*` (firecrawl provider, exa provider, tavily provider, parallel provider) → `enterprise/tooling/builtin/search/_providers/`
35. `tools/web_tools.py` → `enterprise/tooling/builtin/search/web_tools.py` (con MiniMax en lugar de OpenRouter+Gemini)

### Sprint I (advanced + MoA + send_message)
36. `tools/mixture_of_agents_tool.py` → `enterprise/tooling/mixture_of_agents.py` (reescritura sustancial: solo MiniMax)
37. `tools/send_message_tool.py` → `enterprise/tooling/builtin/communication/send_message.py`
38. `tools/transcription_tools.py` → `enterprise/tooling/builtin/meetings/_transcription.py` (opcional)

### Sprint J (WRAP-SDK del catálogo)
39-70. Escribir wrappers `BuiltinTool` para los ~32 tools WRAP-SDK (tavily, exa, firecrawl, jina, fetch, markitdown, playwright, mineru, arxiv, openalex, google_workspace, ms365, notion, linear, hubspot, salesforce, apollo, slack, telegram, whatsapp, mailchimp, excel, power_bi, quickbooks, plaid, teams, zoom, e2b, bamboohr, zendesk).

### Sprint K (nuevos sin base)
71. `enterprise/orchestration/complexity_classifier.py`
72. `enterprise/tooling/builtin/personalization/writing_style.py`
73. `enterprise/dreaming/tasks/proactive_preparation.py`
74. Wrappers de COMPANY/*.md parser
75. `enterprise/tooling/builtin/desktop/skill_learning.py` (extensión sobre computer_use)

---

## 6. Cambios al plan principal que este inventario motiva

### 6.1 Decisiones a re-confirmar con el usuario

1. **Browser tool**: ¿bundlear CLI `agent-browser` (Node) o reescribir con `playwright-python`? Recomendado (b) por cero deps Node.
2. **Session search**: SQLite FTS5 queda opcional; no se introduce Postgres tsvector como pilar nuevo.
3. **MCP client**: coexisten. 2.0 sigue con `infra/mcp/execution_client.py`; 3.0 puede usar `enterprise/tooling/mcp_client.py` si aporta capacidades.
4. **`run_agent.py`**: ¿usar como base del nuevo orquestador, o `OrchestratorService` 2.0 sigue siendo el orchestrator? Recomendado: el 2.0 sigue; Hermes solo aporta patrones puntuales (loop, batching).

### 6.2 Reducción de scope detectada

| Plan original | Hermes ya lo tiene | Reescribir solo |
|---|---|---|
| §10 Dreaming `scheduler.py` desde cero | `cronjob_tools.py` | Trigger idle + orquestación de tareas |
| §6 ContextCompressor desde cero | `checkpoint_manager.py` | Template 13 secciones específico |
| §3.3 SubagentRegistry desde cero | `process_registry.py` | Schema SQL + depth limit |
| §12.4 Quotas por usuario | `budget_config.py` | **Obsoleto en version de prueba**; conservar solo telemetria de costo y circuit breakers tecnicos |
| §12.9 Versionado prompts desde cero | `checkpoint_manager.py` | Watcher + integración con SOUL/COMPANY |
| §4.5 ToolRegistry desde cero | `registry.py` + `lazy_deps.py` | Tool-gating logic |
| §6 MoA desde cero | `mixture_of_agents_tool.py` | Reemplazar catálogo modelos por MiniMax |
| §16 Approvals desde cero | `approval.py` + `interrupt.py` + `slash_confirm.py` | Workflow específico para envíos masivos / CRM masivo |
| §15 Skills Registry desde cero | `skills_tool.py` + `skill_manager_tool.py` + `skills_hub.py` + `skill_provenance.py` + `skill_usage.py` | Adaptación a playbooks YAML |

Esto reduce trabajo de F1+F3+F5+§12 en ~30%, pero **no acorta** el cronograma porque añade trabajo de adaptación y validación.

### 6.3 Decisiones nuevas que el inventario obliga

- **TurboVecIndex unico** para vectores. PostgreSQL queda para metadata/audit; SQLite FTS5 solo opcional para texto de sesiones.
- **LlamaIndex opcional** para loaders/chunking/retrieval si reduce codigo propio sin ocultar los ports del dominio.
- **Reemplazar `agent-browser` CLI por `playwright-python`** en browser tool. Cero deps Node.
- **Bundle `agent/file_safety.py` y `agent/redact.py` de Hermes** como parte de `enterprise/governance/`. Son requeridos por `file_tools.py`.
- **MCP client coexiste**: 2.0 mantiene `infra/mcp/execution_client.py`. 3.0 usa `enterprise/tooling/mcp_client.py` (copy de Hermes). Sin migrar el 2.0.

---

## 7. Licencias

Hermes Agent — verificar licencia en `documentation/hermes agent/hermes-agent/LICENSE`. Si MIT/Apache 2.0, copiar libremente con atribución en cada archivo copiado:

```python
# Adapted from Hermes Agent (https://github.com/NousResearch/hermes-agent)
# Original file: tools/<filename>.py
# License: <MIT|Apache-2.0>
```

OpenClaw — verificar licencia. Si solo se usa como referencia conceptual, sin copia de código, **no aplica restricción** (las ideas no son copyrightables).

SDKs PyPI — verificar licencia de cada uno antes de F3 (asumido MIT/Apache 2.0 — verificar las 32 entradas WRAP-SDK).

**Tarea pendiente al inicio de F0**: auditoría de licencias de los ~30 archivos COPY-HERMES + 32 paquetes PyPI.

---

## 8. Catálogo MCPs externos (regla "Python internalizar, otros MCP externo")

Tras pasada exhaustiva sobre `README_mcp_6.md` + `README_mcp_7.md` (4,124 líneas, ~450 MCPs analizados), aplicamos la regla del usuario:

- **MCP en Python** → INTERNALIZAR (cuenta como `WRAP-SDK` o `CLONE-UPSTREAM` Python)
- **MCP en TS/JS/Go/Rust muy completo** → CONSUMIR como MCP externo (STDIO o HTTP)
- **MCP en TS con ≤5 tools simples** → considerar traducir solo las funciones

### 8.1 Tier 1 — Python a internalizar (10 nuevos, suman a los ya identificados)

| MCP | Repo upstream | Dominio | Tools clave | Justificación vs alternativa |
|---|---|---|---|---|
| **open-webSearch** | `Aas-ee/open-webSearch` | search | Bing, Baidu, DDG, Brave, Exa multi-engine | Sin API key, broker libre — útil como fallback |
| **SerpApi (Python)** | `serpapi/serpapi-mcp` | search | Google, Bing, Yahoo, YouTube, eBay | Multi-motor con una sola key |
| **arxiv-mcp** | `andybrandt/mcp-simple-arxiv` | research | Search, fetch papers | Más simple que arxiv PyPI lib |
| **pubmed-mcp** | `andybrandt/mcp-simple-pubmed` | research | Medical literature search | Útil para empresarios sector salud |
| **DuckDuckGo MCP** | `nickclyde/duckduckgo-mcp-server` | search | DDG search sin API key | Sin auth, simple |
| **markcrawl** | `AIMLPM/markcrawl` | documents | Crawl → Markdown + structured data | Útil para indexar sitios completos |
| **MinerU Python** | `opendatalab/MinerU` + `mineru-open-mcp` PyPI | documents | PDF/DOCX/PPTX → Markdown, OCR 109 idiomas | Ya estaba en plan; confirmado Python puro |
| **pdfmux** | `NameetP/pdfmux` | documents | PDF router (PyMuPDF, Docling, OCR) | Complementa MinerU para PDFs problemáticos |
| **WhatsApp Python** | `nakulben/whatsapp-mcp` o `lharries/whatsapp-mcp` | communication | Meta Cloud API básico | Más simple que el TS completo de wazionapps (244 tools) |
| **Teams Python** | `InditexTech/mcp-teams-server` | communication / meetings | Teams messaging + threads | Complementa el WRAP-SDK msgraph que ya estaba |
| **Joinly** | `joinly-ai/joinly` | meetings | Zoom + Teams + Meet bots + transcripts | Cross-platform meetings, Python |
| **ScraperAPI** | `scraperapi/scraperapi-mcp` | web | JS rendering, geotargeting, proxies | Fallback robusto para sitios con anti-bot |
| **YouTube transcripts** | `format37/youtube_mcp` o `zlatkoc/youtube-summarize` | search | Get transcripts + summarize | Útil para análisis de canales sector |
| **Hacker News** | `erithwik/mcp-hn` | search | HN search + top stories | Tech intelligence |
| **biomcp** | `genomoncology/biomcp` | research | PubMed + ClinicalTrials + MyVariant unificado | Para empresarios sector salud/farma |

### 8.2 Tier 2 — MCPs externos via STDIO (mantener como están, no traducir)

Estos son TS/JS muy completos. Consumirlos via `MCPExecutionClient` (ya existe en el 2.0 — reusable).

| MCP | Repo | Lenguaje | Tools | Dominio | Por qué no traducir |
|---|---|---|---|---|---|
| **Gmail completo** | `codefuturist/email-mcp` | TS | 42 | productivity | IMAP/SMTP + state complejo |
| **MS365 oficial** | `softeria/ms-365-mcp-server` | TS | 50+ | productivity | Microsoft Graph completo |
| **Slack oficial** | `jtalk22/slack-mcp-server` | TS | 11 | communication | Real-time + OAuth |
| **Discord** | `PaSympa/discord-mcp` | TS | 60+ | communication | Multi-guild, roles, webhooks |
| **Telegram Bot full** | `FantomaSkaRus1/telegram-bot-mcp` | TS | 174 | communication | Full Bot API surface |
| **WhatsApp Business** | `wazionapps/mcp-server` | TS | 244 | communication | Meta API + workflows + CRM |
| **Brave Search** | `brave/brave-search-mcp-server` | TS | 5 | search | Mantenido oficialmente por Brave |
| **Tavily** | `kshern/mcp-tavily` | TS | 4 | search | Mantenido por Tavily |
| **Exa** | `exa-labs/exa-mcp-server` | TS | 4 | search | Mantenido por Exa |
| **GitHub** | (oficial) | TS | — | code | MCP oficial, mantenido por GH |
| **Linear** | (oficial) | TS | — | code | MCP oficial |
| **Notion** | (oficial) | TS | — | productivity | MCP oficial |
| **Asana** | (oficial) | TS | — | code | MCP oficial |
| **Atlassian/Jira** | (oficial) | TS | — | code | MCP oficial |
| **local-mcp (macOS)** | `lanchuske/local-mcp-releases` | TS | 82 | desktop | macOS nativo, no aplica Windows v3.0 |

### 8.3 Tier 3 — Candidatos a traducir solo las tools (≤5 funciones simples)

| MCP | Repo | Lenguaje | Tools | Esfuerzo traducción | Decisión |
|---|---|---|---|---|---|
| **Google Tasks** | `arpitbatra123/mcp-googletasks` | TS | 3 | Bajo (1 día) | Traducir |
| **CZK FX (banca central)** | `martinhavel/cz-agents-mcp` | TS | 3 | Bajo (1 día) | Patrón: replicar para Banco República (Colombia) |
| **Kagi search** | `ac3xx/mcp-servers-kagi` | TS | 3 | Bajo (1 día) | Opcional (Kagi es de pago) |

### 8.4 LATAM-específicos (oportunidad: construir desde cero)

Detectado en el análisis: **no existen MCPs nativos para entidades LATAM**. Oportunidad de construir:

| MCP propuesto | País | Dominio | Tools | Esfuerzo |
|---|---|---|---|---|
| `vigilador-dian-mcp` | Colombia | finance + compliance | RUT lookup, facturación electrónica status, tarifa IVA | Medio |
| `vigilador-rues-mcp` | Colombia | compliance | Consulta empresarial (Cámara de Comercio) | Bajo |
| `vigilador-sunat-mcp` | Perú | finance + compliance | RUC, comprobantes | Medio |
| `vigilador-sii-mcp` | Chile | finance | RUT, facturación | Medio |
| `vigilador-banrep-mcp` | Colombia | finance | Tasas, TRM, indicadores | Bajo |

**Estos NO son urgentes**. Se construyen bajo demanda de un usuario real (YAGNI).

### 8.5 Catálogo final consolidado del plan v3.0

| Tipo | Cantidad | Mantenimiento |
|---|---|---|
| COPY-HERMES (Python) | ~30 archivos | Mediano: adaptar imports + tests propios |
| WRAP-SDK Python (SDKs PyPI oficiales) | ~25 tools | Bajo: SDK mantenido por proveedor, nosotros solo el wrapper |
| MCP externo STDIO/HTTP (TS/JS oficiales) | ~15 MCPs | Mínimo: consumir, ellos mantienen |
| Tools nuevas sin base | 4 (writing_style, COMPANY parser, complexity_classifier, skill_learning extensión) | Alto: diseñar + implementar desde cero |
| Tools LATAM-específicas | 0 inicial (futuro) | A definir |

**Total tools disponibles al agente en v3.0**: ~40 internalizadas + ~15 externas = **~55 capacidades**, pero **solo 25-30 son código que mantenemos directamente**.

### 8.6 Observabilidad uniforme (clave para que esto sea sostenible)

Independientemente de si una tool es interna o MCP externo, el contrato observacional es **el mismo**:

```python
class ToolWrapper(Protocol):
    name: str
    domain: str
    is_external_mcp: bool                    # nuevo flag
    requires_auth: bool

    async def healthcheck(self) -> HealthStatus:
        # interna: importa + ping al SDK
        # externa: ping al MCP server (initialize + list_tools)
        ...

    async def execute(self, tool_name: str, args: dict) -> ToolResult: ...
```

**Logs estructurados** con prefijo:
- Internas: `vigilador.tools.<dominio>.<tool>`
- Externas: `vigilador.mcp_ext.<provider>.<tool>`

**Test E2E mínimo por tool** (~50 LOC):
- Import sin error
- `healthcheck()` devuelve OK con credenciales de prueba
- 1 llamada real al SDK/MCP con mock-friendly args
- Schema JSON válido

**Circuit breaker uniforme**:
- 3 fallos en 60s → tool marca DOWN durante 5 min
- Mientras DOWN: `ToolRegistry.list_tools_for_role` la excluye automáticamente (gating-out por health)
- Alerta al canal preferido del usuario
- Recuperación automática tras cooldown

Esto resuelve el problema de "debuguear 30+ tools": **el flujo de debug es uno solo**, sea interna o externa. Cuando algo falla, el dashboard te dice cuál, el log te dice por qué, y el circuit breaker lo aísla sin que tumbe el harness.

### 8.7 Descubrimiento semantico de tools

El agente no recibe este catalogo completo en prompt. `ToolRegistry` funciona en tres niveles:

| Nivel | Contenido | Uso |
|---|---|---|
| `ToolCard` | id, dominio, descripcion corta, capabilities, permisos, costo, health | Siempre indexado y disponible |
| `ToolSummary` | schema de inputs/outputs, ejemplos cortos, errores comunes | Solo top-k tras busqueda semantica |
| `ToolDocs` | README, docs largas, guias de proveedor, payloads extensos | Solo cuando el tool ya fue seleccionado |

Ranking:
1. Filtro por Mode, Playbook, capability tokens, credenciales y health.
2. Busqueda semantica sobre descripcion/capabilities/tags/historico.
3. Reranking por costo, latencia, privacidad, disponibilidad local/cloud y exito historico.

### 8.8 Automantenimiento admin de tools/MCPs

Cada entrada con `update_policy: upstream-watch` queda bajo Dreaming admin:

- Revisa releases, commits, CVEs, cambios de schema y nuevas capabilities.
- Compara hash/version local vs upstream.
- Ejecuta tests en sandbox o rama temporal.
- Genera propuesta con diff, impacto, riesgo y pruebas.
- Requiere aprobacion admin para promover cambios.

Estado especial: `maintenance_pending` significa que hay update detectado, pero el runtime estable sigue usando la version anterior.

---

## 9. Dominios nuevos (segunda iteración del catálogo)

Tras detectar gaps por feedback del usuario, se agregan **4 dominios nuevos** (legal queda como skills, no MCP):

### 9.1 design (nuevo)

| Tool | Origen | Lenguaje | Estrategia | requires_key | env_var | signup_url | pricing | tools clave | nota |
|---|---|---|---|---|---|---|---|---|---|
| `figma` | `figma-mcp` oficial | TS | MCP-EXTERNO | true | FIGMA_API_TOKEN | figma.com/developers | freemium | get_file, get_styles, get_components, export, comments | Lee diseños, no edita |
| `excalidraw_architect` | `BV-Venky/excalidraw-architect-mcp` | Python | WRAP-SDK | false | — | local | free | generate_diagram (50+ tech mappings), auto_layout, export_svg | Sin API key, ready Tier 1 |
| `mermaid` | `Narasimhaponnada/mermaid-mcp` | TS | TRADUCIR-TOOLS | false | — | local | free | generate_diagram (22+ tipos), validate, export_svg/png/pdf | Solo 3-5 tools simples → traducir |
| `photopea` | `attalla1/photopea-mcp-server` | TS | MCP-EXTERNO | false | — | photopea.com | freemium | edit_image, layers, text, filters, export (34 tools) | Editor online Photoshop-like |

**Alternativas descartadas (dedup)**: Adobe XD (sin MCP público), Sketch (sin MCP público), Canva (API cerrada).

### 9.2 engineering (nuevo)

| Tool | Origen | Lenguaje | Estrategia | requires_key | env_var | signup_url | pricing | tools clave | nota |
|---|---|---|---|---|---|---|---|---|---|
| `blender` | `ahujasid/blender-mcp` | Python | WRAP-SDK | false | — | local (instalar Blender) | free | render, compose, animate, modify_scene | Control Blender local, sin API key |
| `jupytercad` | `asmith26/jupytercad-mcp` | Python | WRAP-SDK | false | — | local | free | create_model, edit_geometry, export | CAD OpenSource en Jupyter |
| `fusion_360` | `mikan-atomoki/text-to-model` | Python | WRAP-SDK | true | FUSION_API_KEY | autodesk.com | paid ($55-680/año) | extrude, sketch, fillet, 60+ CAD ops | NL → 3D, paid — descartado v3.0 inicial |

**Descartados (sin MCP público disponible)**: AutoCAD (Autodesk API cerrada), SolidWorks, Rhino, QGIS (PyQGIS existe pero sin MCP), ArcGIS, Revit/BIM.

**Recomendación v3.0 inicial**: solo `blender` + `jupytercad` (Tier 1 free). Fusion 360 bajo demanda explícita.

### 9.3 media (nuevo) — image/video/audio gen

| Tool | Origen | Lenguaje | Estrategia | requires_key | env_var | signup_url | pricing | tools clave | nota |
|---|---|---|---|---|---|---|---|---|---|
| `fal_media` | `raveenb/fal-mcp-server` | Python | WRAP-SDK | true | FAL_API_KEY | fal.ai | freemium | generate_image_flux, generate_video, generate_music | FLUX, SD, MusicGen unified |
| `comfyui` | `ConstantineB6/comfy-pilot` | Python | WRAP-SDK | false | — | local | free | execute_workflow, view, edit_nodes | Local Stable Diffusion, sin key |
| `imagen_google` | `mordor-forge/gemini-media-mcp` | Go | TRADUCIR-TOOLS | true | GOOGLE_API_KEY | ai.google.dev | freemium | generate_image_imagen4, edit, generate_video_veo, tts | Gemini multimodal unified |
| `elevenlabs_tts` | `gaudiolab-jp/gaudio-developers-mcp` | TS | MCP-EXTERNO | true | ELEVENLABS_API_KEY | elevenlabs.io | freemium (10K chars/mes) | text_to_speech, voice_clone, stem_separate | TTS 29 voces |
| `dalle_unified` | `MohamedAbdallah-14/prompt-to-asset` | TS | TRADUCIR-TOOLS | true | OPENAI_API_KEY | openai.com/api | paid | generate_icon, logo, favicon, og_image | Multimodal, 30+ modelos via Cloudflare |
| `suno_music` | `AceDataCloud/MCPSuno` | Python | WRAP-SDK | true | SUNO_API_KEY | suno.ai | freemium (3 songs/día) | generate_music, lyrics, vocal_extract | Música con IA |
| `davinci_resolve` | `samuelgursky/davinci-resolve-mcp` | Python | WRAP-SDK | false | — | local (instalar Resolve) | free tier | edit_video, color_grade, transcode | Pro video editing local |

**Premium descartados v3.0 inicial**: Runway ($12.99/mes), Pika ($15-45/mes), Sora (acceso cerrado), Midjourney (sin MCP estable).

**Tier 1 recomendado**: `fal_media` (freemium) + `comfyui` (free local) + `imagen_google` (freemium).

### 9.4 analytics (nuevo) — BI + Data Warehouses

| Tool | Origen | Lenguaje | Estrategia | requires_key | env_var | signup_url | pricing | tools clave | nota |
|---|---|---|---|---|---|---|---|---|---|
| `powerbi` | `mbrummerstedt/powerbi-analyst-mcp` | Python | WRAP-SDK | true | POWERBI_API_KEY | app.powerbi.com | paid ($10-30/usuario/mes) | query_dax, browse_workspaces, query_semantic_model | Semantic models + DAX |
| `metabase` | `1luvc0d3/metabase-mcp` | TS | MCP-EXTERNO | true | METABASE_API_KEY | metabase.com | freemium | natural_language_query, create_dashboard, sql_guardrails (28 tools) | Rate limit + audit logging |
| `csvglow` | `Ratnaditya-J/csvglow` | Python | WRAP-SDK | false | — | local | free | generate_html_dashboard, interactive_charts | CSV → dashboard HTML, 20 temas |
| `mcp_dashboards` | `KyuRish/mcp-dashboards` | TS | MCP-EXTERNO | false | — | local | free | interactive_charts_45plus, kpi_cards, export_png_ppt | 45+ chart types |
| `snowflake` | `isaacwasserman/mcp-snowflake-server` | Python | WRAP-SDK | true | SNOWFLAKE_ACCOUNT + USER + PASSWORD | snowflake.com | paid (consumption-based) | execute_sql, read_write, insight_tracking | RBAC + fine-grained |
| `bigquery` | `ergut/mcp-bigquery-server` | TS | TRADUCIR-TOOLS | true | GOOGLE_CLOUD_PROJECT + GOOGLE_APPLICATION_CREDENTIALS | cloud.google.com/bigquery | paid (consumption-based) | query, schema_inspection, dataset_create | Requiere GCP credentials JSON |
| `clickhouse` | `ClickHouse/mcp-clickhouse` (oficial) | Python | WRAP-SDK | true | CLICKHOUSE_HOST + USER + PASSWORD | clickhouse.com | freemium | query_sql, schema_inspect, streaming | Mantenido por ClickHouse oficial |
| `tableau` | `subhatta123/twilize` | Python | TRADUCIR-TOOLS | true | TABLEAU_API_KEY | tableau.com/developer | paid ($70/usuario/mes) | generate_workbook, create_dashboard, export (47 tools) | Workbook gen desde CSV |

**Sin MCP confirmado v3.0**: Mixpanel, Amplitude, Looker (verificar en F3, saltar si no aparecen).

**Tier 1 recomendado**: `csvglow` + `mcp_dashboards` (free locales) + `metabase` (freemium) + `powerbi`/`snowflake` bajo demanda.

### 9.5 optimization (nuevo C0) — normas tecnicas y mejora empresarial

No es un MCP unico; es un dominio de skills/tools que reutiliza busqueda, documentos, indexacion empresarial y artefactos.

| Tool/Skill | Estrategia | Capabilities clave | Nota |
|---|---|---|---|
| `standard_gap_analysis` | NUEVO | map_standard, extract_requirements, compare_evidence, generate_gap_matrix | ISO, NTC, SST, calidad, seguridad, gestion documental |
| `official_sources_search` | WRAP-SDK sobre search/web existentes | search_official_sources, cite_current_requirement | Usa `company_geo`; prioriza fuentes oficiales |
| `evidence_matrix_builder` | NUEVO | build_evidence_matrix, assign_owner, set_due_date | Conecta documentos indexados con requisitos |
| `improvement_plan_generator` | NUEVO | generate_action_plan, export_checklist, schedule_review | Produce plan de mejora y seguimiento |

### 9.6 artifacts (nuevo C0) — dashboards y pipelines

Extiende lo existente en `application/artifacts/` y se integra con `artifact-development`.

| Tool/Skill | Estrategia | Capabilities clave | Nota |
|---|---|---|---|
| `dashboard_generate` | WRAP-SDK/NUEVO | generate_html_dashboard, generate_streamlit_dashboard, export_png_ppt | Puede usar csvglow/mcp_dashboards si conviene |
| `pipeline_generate` | NUEVO | infer_schema, build_etl_script, schedule_refresh | Pipelines locales o cloud simples |
| `metric_contract` | NUEVO | define_kpis, validate_metric_formula, version_metric | Evita dashboards sin definicion estable |
| `artifact_registry` | NUEVO | register_artifact, link_sources, track_refresh | Relaciona artefacto con fuentes y audit trail |

### 9.7 legal — NO ES DOMINIO MCP, ES SKILLS

Por decisión del usuario, legal NO tiene MCPs dedicados. Se cubre con:

- **Skills aprendidos** (`config/skills/learned/legal-*.yaml`): generación de contratos, revisión de cláusulas, compliance checklists.
- **Templates** (`config/templates/contratos/`): contrato_laboral.docx, contrato_servicios.docx, nda.docx (ya en plan §4.6).
- **Tools existentes reutilizadas**: `docx_generate`, `template_render`, `markitdown` (lee contratos PDF), `firecrawl` (consulta regulaciones online).

DocuSign queda como SDK Python opcional via `docusign-esign` WRAP-SDK si surge demanda, NO como dominio.

---

## 10. MCP Process Supervisor (decisión #64)

Decisión del usuario: "para facilitar el debug, ¿no se pueden implementar dos o más MCPs studio?". Sí, y se hace explícito ahora.

### 10.1 Arquitectura

Cada MCP externo Tier 2 corre en **proceso STDIO dedicado y aislado**. Beneficios:

| Beneficio | Implicación |
|---|---|
| Fallos aislados | Si `discord-mcp` crashea, no afecta `gmail-mcp` ni el harness Python |
| Debug por proceso | PID + stderr propios → `tail -f ~/.vigilador/mcp-logs/<name>.jsonl` |
| Reinicio independiente | Reiniciar 1 MCP sin tocar los otros |
| Versionado independiente | Actualizar Gmail MCP a v2 sin tocar Slack MCP |

### 10.2 Componente nuevo: `MCPProcessSupervisor`

`enterprise/mcp/process_supervisor.py` (~150 LOC). Responsabilidades:

```python
class MCPProcessSupervisor:
    """Gestiona pool de procesos STDIO de los MCPs externos Tier 2."""

    async def start_all(self) -> None:
        """Arranca todos los MCPs definidos en config/mcp/external.yaml al boot."""

    async def restart(self, mcp_name: str) -> None:
        """Reinicio manual de un MCP específico (CLI admin)."""

    async def get_status(self, mcp_name: str) -> ProcessStatus:
        """PID, uptime, último error, % CPU, RSS memoria — para dashboard."""

    async def stop_all(self) -> None:
        """Shutdown limpio al apagar el harness."""

    # Auto-restart con backoff exponencial al fallar (1s → 2s → 4s → 8s → 16s → 32s, max 5 retries)
    # Tras 5 fallos consecutivos: marca MCP como STUCK, alerta al canal del usuario, NO retry hasta intervención manual.
```

### 10.3 Configuración

`config/mcp/external.yaml`:

```yaml
mcps:
  - name: gmail
    command: npx
    args: ["-y", "@codefuturist/email-mcp"]
    env:
      GMAIL_OAUTH_CREDENTIALS: "${GMAIL_OAUTH_CREDENTIALS}"
    healthcheck_interval_sec: 60
    restart_policy: on-failure
    log_file: ~/.vigilador/mcp-logs/gmail.jsonl

  - name: slack
    command: npx
    args: ["-y", "@modelcontextprotocol/server-slack"]
    env:
      SLACK_BOT_TOKEN: "${SLACK_BOT_TOKEN}"
    healthcheck_interval_sec: 60
    restart_policy: on-failure
    log_file: ~/.vigilador/mcp-logs/slack.jsonl

  # ... 15 MCPs Tier 2 totales
```

### 10.4 CLI admin

```bash
vigilador-admin mcp list                # estado de todos los MCPs
vigilador-admin mcp restart slack       # reinicia 1 MCP
vigilador-admin mcp logs gmail --tail 100  # ver logs recientes
vigilador-admin mcp stop discord        # detiene 1 MCP (sale del catálogo)
vigilador-admin mcp start discord       # lo vuelve a arrancar
```

### 10.5 Integración con observabilidad

- **Métricas Prometheus**: `vigilador_mcp_process_status{name=...}` (1=UP, 0=DOWN), `vigilador_mcp_process_restarts_total{name=...}`, `vigilador_mcp_process_uptime_seconds{name=...}`.
- **Dashboard** (§12.2): card por MCP con PID, uptime, restarts, último error, botón restart.
- **Circuit breaker** (decisión #61) aplica igual que a tools internas: si el supervisor reporta DOWN, `ToolRegistry` gating-out automático.

### 10.6 Total procesos al boot

15 MCPs Tier 2 = 15 procesos STDIO + el proceso principal Python = **16 procesos**. Memoria estimada: ~50MB cada MCP Node + ~500MB harness Python = ~1.25 GB RAM total. Aceptable para servidor empresarial estándar.

---

## 11. Resumen consolidado del catálogo final v3.0

### 11.1 Conteo por dominio

| Dominio | Tier 1 (Python) | Tier 2 (MCP ext) | Tier 3 (traducir) | Total |
|---|---|---|---|---|
| search | 4 + 5 nuevos (open-webSearch, SerpApi, DuckDuckGo, HackerNews, YouTube) | 3 (Tavily, Exa, Brave) | — | 12 |
| web | 3 + 1 (ScraperAPI) | — | — | 4 |
| documents (incluye templates) | 6 + 3 (markcrawl, MinerU, pdfmux) | — | — | 9 |
| productivity | 4 (con Forms) | 3 (Gmail, MS365, Notion) | 1 (Google Tasks) | 8 |
| **design** ⭐ | 1 (excalidraw_architect) | 2 (Figma, Photopea) | 1 (mermaid) | 4 |
| **engineering** ⭐ | 2 (blender, jupytercad) | — | — | 2 |
| **media** ⭐ | 3 (fal, comfyui, suno, davinci) | 2 (elevenlabs, dalle_unified) | 1 (imagen_google) | 7 |
| **analytics** ⭐ | 4 (powerbi, csvglow, snowflake, clickhouse) | 2 (metabase, mcp_dashboards) | 2 (bigquery, tableau) | 8 |
| **optimization** | 4 (standard_gap_analysis, official_sources_search, evidence_matrix_builder, improvement_plan_generator) | — | — | 4 |
| **artifacts** | 4 (dashboard_generate, pipeline_generate, metric_contract, artifact_registry) | — | — | 4 |
| crm | 3 | 1 (HubSpot ofic si existe) | — | 4 |
| communication | 4 | 5 (Slack, Discord, Telegram Bot, WhatsApp Business, Mattermost) | — | 9 |
| finance | 4 | — | 1 (CZK FX → patrón LATAM) | 5 |
| meetings | 2 + 1 (Joinly) | — | — | 3 |
| desktop | 2 (computer_use, file_system) | 1 (local-mcp macOS si target) | — | 3 |
| code | 4 (e2b, kanban, delegate, clarify) | 4 (GitHub, Linear, Jira, Asana) | — | 8 |
| research | 2 + 4 (arxiv, pubmed, biomcp, PapersWithCode) | — | — | 6 |
| people/HR | 2 | — | — | 2 |
| personalization | 1 (writing_style) | — | — | 1 |
| **legal** (skills, no MCP) | 0 tools dedicadas | 0 | 0 | 0 (cubierto por templates + skills) |

**TOTAL operativo**: el numero exacto vive en el inventario SSOT. Tras C0, optimization/artifacts agregan capacidades, pero el criterio de inclusion es utilidad real + mantenimiento claro, no inflar el conteo.

### 11.2 Tools FREE recomendadas para Tier 1 desde día 1 (sin onboarding)

**17 tools sin API key, producción-ready:**

1. excalidraw_architect — diagramas arquitectura (50+ tech mappings)
2. mermaid — 22+ tipos de diagrama
3. blender — 3D modeling local
4. jupytercad — CAD OpenSource
5. comfyui — Stable Diffusion local
6. csvglow — CSV → dashboard HTML
7. mcp_dashboards — 45+ chart types
8. davinci_resolve (free tier) — video editing pro
9. open-webSearch — web search broker libre
10. DuckDuckGo MCP — search sin API key
11. arxiv MCP — papers académicos
12. pubmed MCP — literatura médica
13. Hacker News MCP — tech intelligence
14. markcrawl — crawl → Markdown
15. mineru — PDF OCR 109 idiomas (Python directo)
16. pdfmux — PDF router
17. fetch (MCP oficial) — HTML estático

Estas 17 cubren ~40% de casos de uso empresariales **sin que el usuario tenga que conseguir una sola API key**. Ideal para onboarding rápido.

### 11.3 Tools con API key gratuita o freemium (Tier 1 con onboarding mínimo)

| Tool | Tier free | Cuándo upgrade |
|---|---|---|
| FAL.ai | $5 USD crédito | >100 imágenes/mes |
| ElevenLabs | 10K caracteres/mes | >10 minutos TTS/día |
| Suno | 3 canciones/día | uso comercial |
| Google AI (Gemini/Imagen/Veo) | rate-limited free | producción |
| Figma | personal free | equipos > 3 personas |
| Metabase | self-hosted free | cloud >50 users |
| ClickHouse | self-hosted free | managed >$300/mes |

### 11.4 Tools paid premium descartadas v3.0 inicial

**11 servicios >$50/mes** marcados como "agregar bajo demanda explícita":

Fusion 360, Tableau, Power BI Enterprise, Snowflake, BigQuery (consumption), Runway, Pika, Sora, DaVinci Resolve Studio, Mixpanel, Amplitude.

---

## 12. Apps locales — sub-tools `*_local.py` por dominio (nueva categoría)

**Pregunta del usuario**: "Los MCPs como Tableau y PowerBI no funcionan manejando la propia PC si uno tiene las apps?"

**Respuesta honesta**: los MCPs del catálogo previo son **cloud-based** (Power BI Service, Tableau Online). NO automatizan Power BI Desktop ni Tableau Desktop locales. Para PYMEs que no migraron al cloud (60-70% de LATAM), el catálogo queda ciego.

### 12.1 Estrategia adoptada

**Sub-tools `*_local.py` dentro de cada dominio relevante**. El agente elige según disponibilidad:
- Si `<TOOL>_API_KEY` está configurada → versión cloud
- Si la app local está instalada (detectado por presencia del binario) → versión local
- Si ambas → preferencia configurable en `config/settings.yaml`

### 12.2 Sub-tools locales nuevas (10 tools)

| Tool | Dominio | Tecnología subyacente | Plataformas | requires_key | Capacidad |
|---|---|---|---|---|---|
| `excel_local.py` | finance/ | `xlwings` (COM Windows / AppleScript macOS) | Win + macOS | false | Interactúa con Excel ABIERTO: ejecuta macros, refresca pivot tables, ejecuta fórmulas en vivo. Complementa `excel.py` (lee/escribe `.xlsx` sin abrir). |
| `powerbi_file_reader.py` | analytics/ | `pbi-tools` (CLI .NET dev tool) + parser propio | Win + Linux + macOS | false | Lee archivos `.pbix` extrae modelo + queries M + DAX measures + referencias a fuentes. No ejecuta queries — solo introspección. |
| `tableau_file_reader.py` | analytics/ | `tableauhyperapi` (oficial Tableau) | Win + Linux + macOS | false | Lee archivos `.twbx` / `.hyper` (formato columnar). Extrae schema, datos y workbook XML. |
| `outlook_local.py` | productivity/ | `pywin32` (COM Outlook) | Win only | false | Lee correos del Outlook local **sin OAuth** (usa cuenta ya configurada por el usuario). Búsqueda, filtros, attachments. Complementa `ms365.py` (cloud Graph API). |
| `powerpoint_local.py` | documents/ | `pywin32` (COM PowerPoint) o `python-pptx` (read/write sin abrir) | Win (COM) + cualquier OS (python-pptx) | false | Lee/edita `.pptx` directamente. Refresca data from external sources. Complementa `pptx_generate.py`. |
| `word_local.py` | documents/ | `pywin32` (COM Word) o `python-docx` (read/write sin abrir) | Win (COM) + cualquier OS (python-docx) | false | Lee/edita `.docx`. Track changes, comments, mail merge. Complementa `docx_generate.py`. |
| `autocad_local.py` | engineering/ | `pyautocad` (COM AutoCAD) | Win only | false | Control AutoCAD ABIERTO: lee entidades, modifica capas, exporta a DWG/DXF/PDF. Requiere AutoCAD instalado (cualquier versión). |
| `solidworks_local.py` | engineering/ | `pywin32` + SolidWorks COM API | Win only | false | Lee modelos `.sldprt`, `.sldasm`, `.slddrw`. Extrae propiedades, dimensiones, BOMs. Requiere SolidWorks instalado. |
| `imessage_local.py` | communication/ | `imessage-query` (lee SQLite local) | macOS only | false | Lee historial iMessage sin API. Complementa el `imessage` MCP descartado por ser macOS-only. |
| `outlook_calendar_local.py` | productivity/ | `pywin32` (COM Outlook Calendar) | Win only | false | Lee/escribe calendario Outlook local sin OAuth. Útil para agendamientos rápidos sin tocar Graph API. |

### 12.3 Detección automática de apps instaladas

`enterprise/tooling/local_app_detector.py` (nuevo, ~80 LOC):

```python
class LocalAppDetector:
    """Detecta qué apps locales están instaladas en el sistema."""

    @cached_property
    def has_excel(self) -> bool:
        """Win: check HKLM\\Software\\Microsoft\\Office\\<ver>\\Excel. macOS: /Applications/Microsoft Excel.app"""

    @cached_property
    def has_powerbi_desktop(self) -> bool:
        """Win: HKLM\\Software\\Microsoft\\Microsoft Power BI Desktop. (No macOS — PBI Desktop solo Win)"""

    @cached_property
    def has_tableau_desktop(self) -> bool:
        """Win: HKLM\\Software\\Tableau. macOS: /Applications/Tableau Desktop*.app"""

    # ... excel, outlook, word, powerpoint, autocad, solidworks
```

El `ToolRegistry` consulta esto al boot:
- App instalada → tool `*_local` se registra y aparece en Tier 1
- App NO instalada → tool `*_local` gating-out automático (mismo mecanismo que falta-de-API-key, decisión #18)

### 12.4 Resolución de conflicto cloud vs local

Cuando el agente quiere "analizar mi dashboard de ventas Q3" y el usuario tiene ambos disponibles:

| Estado | Comportamiento |
|---|---|
| Solo cloud configurado | Usa cloud |
| Solo local detectado | Usa local |
| Ambos | Lee `config/settings.yaml > tools.<tool_name>.prefer: local \| cloud` (default: `local` por privacidad) |
| Ninguno | Tool no aparece en Tier 1 (gating-out) |

### 12.5 Trade-offs honestos

| Pro | Con |
|---|---|
| Datos jamás salen del PC del usuario (privacidad máxima) | Windows-only para varios (COM/pywin32) |
| Cero API key, cero cuotas, cero cuenta cloud | macOS via AppleScript (más limitado) |
| Lectura instantánea de archivos (no requiere instalación de SDK) | Linux: solo `*_file_reader.py` funciona (lee archivos sin app) |
| Funciona offline | Si la app no está instalada, tool no disponible |
| Cubre PYMEs no-cloud (60-70% LATAM) | Versiones de app distintas pueden romper COM bindings |

### 12.6 Lista FINAL de tools (con sub-tools locales)

| Dominio | Cloud (Tier 1/2) | Local (`*_local`) | Total dominio |
|---|---|---|---|
| analytics | 8 (powerbi/metabase/csvglow/snowflake/clickhouse/bigquery/tableau/mcp_dashboards) | 2 (powerbi_file_reader, tableau_file_reader) | 10 |
| finance | 4 (excel/power_bi/quickbooks/plaid) | 1 (excel_local con xlwings) | 5 |
| documents | 6 | 2 (powerpoint_local, word_local) | 8 |
| productivity | 4 + Forms | 2 (outlook_local, outlook_calendar_local) | 8 |
| engineering | 2 (blender, jupytercad) | 2 (autocad_local, solidworks_local) | 4 |
| communication | 9 | 1 (imessage_local) | 10 |
| (otros sin cambios) | — | — | — |

**Total final**: ~79 capacidades (10 sub-tools locales nuevas), pero los `*_local.py` son **wrappers thin** sobre `xlwings`/`pywin32`/`tableauhyperapi`/`pbi-tools` — esfuerzo de mantenimiento similar a un WRAP-SDK.

---

## 13. Próximo paso (re-actualizado)

1. **Plan principal actualizado** con decisiones 64-72 (MCP supervisor + dominios nuevos + API keys + dedup + apps locales).
2. **Comenzar F0** con auditoría de licencias + creación de estructura `enterprise/tooling/builtin/{design,engineering,media,analytics}/` además de los 13 anteriores.
3. **Sprint A** (5 archivos base de Hermes) como primera implementación tangible.
4. **Diseñar el contrato `ToolWrapper` unificado** (interna + externa + local con misma observabilidad) como parte de Sprint A.
5. **Diseñar `MCPProcessSupervisor`** (Sprint A.2, ~150 LOC) para arrancar los 23 procesos Tier 2 al boot.
6. **Diseñar `LocalAppDetector`** (Sprint A.3, ~80 LOC) para gating-out automático de `*_local.py` cuando la app no está instalada.
