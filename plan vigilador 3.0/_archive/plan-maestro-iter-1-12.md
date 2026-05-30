# Plan: Diseño del Vigilador Tecnológico 3.0 — Harness Empresarial MiniMax

## Contexto

El usuario quiere evolucionar el **Vigilador Tecnológico 2.0** hacia un **3.0 totalmente empresarial centrado en MiniMax** que ayude al empresario en **cualquier área** de la empresa. El entregable es **un único documento Markdown** consolidando arquitectura, herramientas, metodologías y cambios al sistema actual.

**Decisiones validadas con el usuario en esta sesión** (todas vinculantes para el documento final):

1. **TurboVec**: integrar el paquete real `pip install turbovec` (https://github.com/RyanCodrai/turbovec, Rust+Python, basado en TurboQuant de Google Research, 16× compresión, integraciones LangChain/LlamaIndex/Haystack/Agno).
2. **6 ramas actuales** → playbook `technology-watch` del nuevo orquestador (preservado, no reescrito).
3. **Estructura**: subpaquete `src/vigilancia_multiagente/enterprise/` paralelo. Cero breaking changes en 2.0.
4. **Canales prioritarios**: Web/SSE (existe) + Telegram + WhatsApp Cloud API.
5. **MCPs**: ~~20 MCPs internalizados~~ **[OBSOLETA — sobreescrita por decisión #58 (Tier 1/2/3) y #75 (~79 capacidades). Conservar entrada por trazabilidad — principio 5 constitución.]**
6. **Combos de agentes**: **CrewAI** para combos nuevos + `BranchCoordinator` actual para technology-watch.
7. **LLMs**: **solo MiniMax**. M-2.7 principal, M-2.5 para diversidad en debates. Sin Claude/Gemini/DeepSeek.
8. **Orquestador complejidad-aware**: step `ComplexityClassifier` clasifica la tarea, despliega 1–N agentes especializados. **Sin límite de llamadas**. **Sub-agentes pueden invocar más sub-agentes** (recursivo, depth-aware con guardrails).
9. **Especialización**: rol + tools restringidas. **Tool discovery progresivo**: cada agente descubre sus tools en runtime (no se cargan todos los schemas al inicio).
10. **Debate**: multi-agente con moderador (3–5 agentes M-2.7/M-2.5 + sintetizador M-2.7).
11. **Origen explícito por tool**: cada tool del catálogo declara su estrategia (COPY-HERMES / CLONE-UPSTREAM / WRAP-SDK). Detalle en §4.1–§4.2.
12. **Computer Use**: agregado al catálogo como tool #21, copiada de Hermes (`tools/computer_use_tool.py`), adaptada a Windows 11.
13. **`COMPANY.md`**: nuevo archivo declarativo de contexto empresarial (estructura, cargos, áreas, procesos, sistemas, políticas). Complementa a `SOUL.md` (personalidad). Detalle en §8.1.
14. ~~35 tools sub-carpetizadas por dominio funcional~~ **[OBSOLETA — sobreescrita por decisión #65 (17 dominios, +design/engineering/media/analytics) y #75 (~79 capacidades). Conservar entrada por trazabilidad.]**
15. **Computer Use con Skill Learning**: el agente aprende a usar sitios/apps por demostración y guarda el procedimiento como skill reutilizable. Auto-corrección por vision + AX tree. Detalle en §4.4.
16. **`COMPANY.md` partido en 5 archivos** en `config/company/`: `identity.md`, `organization.md`, `processes.md`, `systems.md`, `policies.md`. Detalle en §8.1.
17. **Modo Dreaming**: auto-mantenimiento del harness (consolidación memoria, curador de skills, refresh de SOUL/COMPANY, vacuum de índices, revalidación de skills aprendidos). Triggers: cron nocturno 3 AM + idle > 10 min. Detalle en §10. **Extensión proactiva**: Dreaming también prepara borradores de correos y agenda tareas pendientes basándose en bandeja y calendar (§10.7).
18. **Tool-gating por API key**: si la API key requerida por una tool no está configurada en `.env`, la tool **no aparece** en el listing Tier 1 del ToolRegistry. El agente nunca puede intentar invocarla. Detalle en §6/§11.
19. **File system tool**: agregada como tool #36, COPY-HERMES de `tools/file_tools.py` + `file_operations.py` + `file_state.py`. Detalle en §4.2 sub-carpeta `desktop/`.
20. **Writing style learning**: módulo que analiza correos previos del usuario, infiere estilo personal (tono, longitud, formalidad, vocativos, firma), y lo aplica al redactar correos. Detalle en §10.6 (extensión del Dreaming) y §4.2 sub-carpeta `personalization/`.
21. **Deep research como playbook explícito**: el patrón de research del 2.0 (Clarify → Plan → Approve → Execute paralelo → Fuse → Report) se preserva y expone como playbook `deep-research` activable desde cualquier canal. Detalle en §7.2.
22. **Módulo de Templates** (sub-carpeta `documents/` ampliada): generación de informes, propuestas, contratos, presentaciones desde plantillas reutilizables. Tools: `template_render` (Jinja2 sobre MD/DOCX/HTML), `pdf_generate` (Markdown→PDF vía WeasyPrint), `docx_generate` (python-docx con placeholders), `pptx_generate` (python-pptx). Plantillas en `config/templates/`. Detalle en §4.6.
23. **Indexación automatizada en Dreaming**: los connectors (Google Drive, OneDrive, WhatsApp, chatbot, local_fs) ya no requieren scheduling separado — se ejecutan como tarea `ingestion_sync` dentro del ciclo Dreaming nocturno + opcionalmente en idle. Detalle en §10.3 ampliado.
24. **Módulo de reuniones** (nueva sub-carpeta `meetings/`): integración con Teams y Zoom para crear/listar reuniones, obtener grabaciones, generar minutas automáticas. Tools: `teams_meeting`, `zoom_meeting`. Detalle en §4.2 sub-carpeta `meetings/`.
25. **Google Forms**: ampliación de `google_workspace.py` para crear formularios, listar respuestas, exportar a Sheets, analizar resultados. Detalle en §4.2 productivity ampliado.

### Decisiones de enterprise foundation (segunda iteración con el usuario)

26. **Multi-tenancy desde día 1**: `tenant_id UUID NOT NULL` en TODAS las tablas nuevas. v3.0 inicial single-tenant pero el schema lo soporta. Detalle en §16.
27. **Observability (Prometheus + OpenTelemetry traces)**: métricas estructuradas (tokens por playbook, latencia p50/p95/p99, costo $ por sesión, error rate por tool), tracing distribuido por sesión, dashboard de salud. Detalle en §17.
28. **Disaster Recovery + Backup**: backup automatizado (pgvector, TurboVec, `~/.vigilador/credentials/`, `config/*`) con restore probado. RTO 1h / RPO 24h declarados. Detalle en §18.
29. **Quotas por usuario**: tokens/día, sesiones/día, $ máximo por sesión. Circuit breaker per-user además del per-MCP. Detalle en §19.
30. **SSO/SAML/OIDC**: Azure AD, Google Workspace SSO, Okta via SAML 2.0 / OIDC. Reemplaza el password auth como método primario para tenants empresariales. Detalle en §20.
31. **Compliance evidence**: data residency declarada, right to be forgotten (tool `forget_user(user_id)`), DPA template, SOC 2 readiness checklist. Detalle en §21.
32. **Encryption at rest + in transit declarado**: TDE en pgvector, TLS obligatorio SSE/webhooks/MCPs, key rotation policy 90 días. Detalle en §22.
33. **PII detection + redaction**: Presidio (Microsoft) opt-in. Antes de indexar y/o antes de pasar al LLM. Detalle en §23.
34. **Conversational analytics + Metrics Dashboard**: módulo de inspección de metadata (qué se indexó, con qué scopes, qué tools accedieron a qué docs, traces de queries). Unifica audit + analytics + observability. Detalle en §17 ampliado.
35. **Versionado de prompts/playbooks**: tabla `prompt_versions(id, file, content_hash, activated_at, rollback_to)` para A/B testing y rollback de SOUL.md, COMPANY.md, playbook YAMLs. Detalle en §24.

### Decisiones de la tercera iteración

36. **Sin transacciones bancarias**: descartado el módulo de inversiones estilo OpenClaw/Hermes. Cero capacidad de mover dinero. **Roadmap futuro**: condicionado a "cuenta bancaria aislada del patrimonio principal". Hasta entonces, las tools de finance (Plaid, QuickBooks) son **read-only** o limitadas a generar borradores/reportes, nunca ejecución.
37. **Sin CLI pública**: descartada. Toda interacción del usuario por canales (Web/SSE, Telegram, WhatsApp). Mantener CLI **mínima interna** solo para operaciones de admin del propio harness (start, stop, backup, restore, migración), no expuesta al usuario final.
38. **Sin multi-modelo (descartado)**: solo MiniMax. Sin abstracción `multiprovider_router.py`. Si MiniMax cae, el harness queda inservible (riesgo aceptado).
39. **Sin plan de continuidad si MiniMax cae**: descartado. No hay modo degradado offline.
40. **Idioma: interno en inglés, externo en idioma del usuario**: TODO lo que ve el LLM en sistema (system prompts, BranchOverlay, AgentRole, tool descriptions, schemas, **SOUL.md, COMPANY.md, playbooks YAML**) va en inglés. Solo lo que sale al usuario (respuesta final, correos, informes, mensajes en canales, entregables de Templates) va en idioma detectado (default español, autodetectado por turno). Implica `LanguageRouter` en `PromptComposer`. Detalle en §25.
41. **Embeddings + reranker locales (con switch)**: nuevo `infra/embeddings/local_embeddings.py` (sentence-transformers + `BAAI/bge-m3` multilingüe + `BAAI/bge-reranker-v2-m3` cross-encoder). Coexiste con `gemini_gateway.py` actual; switch en `config/settings.yaml`. El 2.0 sigue con Gemini por defecto; el 3.0 default a local. Detalle en §5.7.
42. **Onboarding wizard**: primer arranque guía al usuario por (a) crear COMPANY/*.md vía formulario conversacional, (b) conectar primer OAuth (Drive o OneDrive), (c) lanzar primera ingestión, (d) probar primer playbook. Detalle en §26.
43. **Update mechanism + migration runner**: auto-update de tools internalizadas cuando upstream publica fix de seguridad (sólo `WRAP-SDK` y `CLONE-UPSTREAM`, no `COPY-HERMES`). Alembic para schema migrations versionadas. Detalle en §27.
44. **Approval workflows acotados** (no transacciones, sí estos casos):
   - Envío masivo de emails (> 10 destinatarios): aprobación humana en canal preferido antes de ejecutar.
   - Mutaciones masivas de CRM (> 5 registros): aprobación antes de ejecutar.
   - **Cambios a `config/soul.md`, `config/company/*.md`, políticas, `config/templates/*`**: **el agente NUNCA los modifica directamente**. Solo propone cambios en mensaje al usuario, quien edita manualmente. Esto es más estricto que approval — es prohibición.
   - Skills aprendidos en primera ejecución autónoma (ya cubierto §4.4).
   Detalle en §28.
45. **Cuentas separadas vs cuentas del usuario**: el agente debe poder operar con (a) cuentas propias (bot accounts) cuando estén disponibles, o (b) cuentas del usuario via OAuth — pero **sin permiso de eliminar nada** (read + create + update, nunca delete). Implementa OAuth scopes restrictivos + filtro a nivel de tool (cualquier método `delete_*` se gating-out automáticamente). Detalle en §28.
46. **Knowledge Graph dual (investigación + empresarial)**:
   - **Grafo de investigación** (preservado del 2.0, `application/graph/`): entidades extraídas de research público.
   - **Grafo de conocimiento empresarial** (nuevo `enterprise/graph/`): 4 tipos de entidades desde corpus indexado: (i) personas + cargos (de COMPANY/organization.md, correos, WhatsApp), (ii) documentos + tipo + autor + fecha, (iii) procesos + sistemas (de COMPANY/processes.md y systems.md), (iv) clientes/proveedores/competidores (extraídos de correos, docs, CRM). PII redaction se aplica antes de poblar nodos.
   - Tablas con namespace separado, mismo backend (pgvector + NetworkX). Detalle en §29.

**Alineación con la constitución del proyecto** (`.specify/memory/constitution.md` v1.2.0):

| Principio | Cómo lo aplica este plan |
|---|---|
| 1. Pensar antes de codificar | Supuestos explícitos en §0; preguntas confirmadas con usuario antes de redactar. |
| 2. Simplicidad obligatoria (KISS, YAGNI, AHA) | **79 capacidades total** (40 Tier 1 + 23 Tier 2 + 6 Tier 3 + 10 sub-tools locales) — número confirmado en decisión #77 como fuente única. Sin abstracciones especulativas. Multi-tenancy en schema desde día 1 (no se construye UI ni billing aún — eso es YAGNI), pero `tenant_id` evita refactor masivo después. Sin multi-LLM (decisión #38, aclarada en #79: solo MiniMax para LLM generativo), sin CLI pública, sin transacciones bancarias. **Nota auditoría #82**: el alcance asume equipo 2-3 ingenieros o cronograma extendido. |
| 3. Modularidad primero (SRP, SoC) | Subpaquete `enterprise/` con subcarpetas por concern (orchestration, ingestion, tooling, memory). Cada módulo una responsabilidad. |
| 4. Manejo de errores estricto | Sin try/except defensivos. Errores propagan con contexto. Circuit breakers solo en boundaries (MCPs externos). |
| 5. Cambios quirúrgicos | Plan describe exactamente qué archivos se crean vs preservan vs amplían. Cero refactor lateral en 2.0. |
| 6. Entrega verificable | §10 define criterios verificables por fase. |
| DRY | TurboVec como nuevo backend del port `VectorIndex` ya existente (no se duplica abstracción). DomainProfile hereda de BranchOverlay (no se reinventa). |
| WET | Tolerar duplicación temporal en F1 (playbook YAML duplica algo de matrix YAML) antes de abstraer. |
| LoD | Cada agente solo conoce su rol, sus tools y el moderador. No alcanza estado de hermanos. |
| Bajo Acoplamiento + DIP | Connectors implementan port `IngestionConnector`. ChannelAdapters implementan `ChannelAdapter`. Reuso de DIP del 2.0. |
| OCP | Nuevos playbooks se añaden por YAML sin tocar `PlaybookRunner`. Nuevos connectors implementan el port sin tocar el `IngestionOrchestrator`. |
| ISP | Tool discovery progresivo: agentes ven solo el subset de tools que necesitan, no la interfaz global. |
| CQS | `IngestionOrchestrator` y `PlaybookRunner` separan commands (sync, run) de queries (status, list). |
| POLA | ComplexityClassifier transparente: log de su decisión por sesión. YAML declarativo. |
| Convención sobre Configuración | Playbooks YAML con defaults sensatos; configuración solo cuando se sobreescribe. |

**Supuestos explícitos** (principio 1):

- A1. MiniMax M-2.5 está disponible vía la misma API que M-2.7 (mismo `infra/llm/minimax_client.py` con `model` parametrizable). **Verificar antes de F3.**
- A2. CrewAI 0.x soporta clientes OpenAI-compatible custom (MiniMax base_url). **Verificar antes de F3.**
- A3. TurboVec `pip install turbovec` funciona en Windows 11 (target del usuario). En caso negativo, build desde fuente con Rust toolchain. **Verificar al inicio de F2.**
- A4. Los MCPs a internalizar tienen licencias compatibles (MIT/Apache 2.0). **Verificar para cada uno antes de F5.**
- A5. Las tools de Hermes en `documentation/hermes agent/hermes-agent/tools/` (computer_use_tool.py, browser_tool.py, browser_cdp_tool.py, browser_dialog_tool.py, browser_supervisor.py) son MIT-compatibles y portables a Windows 11 reemplazando solo la capa de captura/eventos macOS (`pyobjc`/AppleScript → `pyautogui`/`pygetwindow`). **Verificar licencia y prueba de portabilidad básica al inicio de F3.**
- A6. `BAAI/bge-m3` (~2.3GB) corre en CPU del usuario con latencia aceptable (< 200ms por batch de 32 chunks de 512 tok). Si no, fallback a GPU local o switch a Gemini. **Verificar al inicio de F0.**
- A7. Presidio para PII detection soporta español + inglés (sí lo hace, con `es_core_news_md` de spaCy). **Verificar al inicio de F0 (sección §23).**
- A8. Los proveedores OAuth de Drive/OneDrive permiten scopes restrictivos sin `delete` (Drive: `drive.file` + `drive.readonly`, MS Graph: `Files.ReadWrite` sin `Files.ReadWrite.All` y sin permisos delete específicos). **Verificar antes de F2.**
- A9. La constitución del proyecto exige cambios quirúrgicos. Cualquier renombre de `vigilancia_multiagente` → `vigilador` se rechaza en este plan; el paquete Python mantiene su nombre, solo la marca/docs externas pueden hablar de "Vigilador 3.0".
- A10. **Capacidad de ejecución asumida**: el catálogo de 79 capacidades distribuidas en 6 fases (28 semanas) asume equipo mínimo de 2-3 ingenieros senior O cronograma extendido a 9-12 meses si el equipo es 1 persona. Decisión consciente del usuario en auditoría #82. Si en F0 se valida que la capacidad real es menor, re-evaluar reducción a MVP (10-15 capacidades core: tools FREE + ingestion + 1 playbook + Channels mínimos). **Verificar al cierre de F0.**
- A11. **Alembic gestiona migraciones Postgres incluyendo columnas pgvector y UUIDv7**: las migraciones que añaden columnas `vector(768)` o crean índices `USING ivfflat`/`USING hnsw` o usan `DEFAULT uuidv7()` deben ejecutarse correctamente en PG 18. TurboVec y SQLite FTS5 NO usan Alembic (formatos estables). **Verificar en F0 con migración de prueba que crea tabla con columna vector + columna `id UUID DEFAULT uuidv7()`.**
- A12. **TurboVec funciona en Windows 11** (mismo como A3 reforzado): si en F2 el `pip install turbovec` o el build desde fuente con Rust toolchain fallan, pgvector queda como **único** índice vectorial. Plan B documentado en decisión #85: el A/B test puede no pasar y eso se acepta. Sin downgrade catastrófico.
- A13. **pgvector 0.8+ está instalado y funcionando en la PG 18 del usuario**: confirmado por el usuario en iteración 10. **Verificar al inicio de F0** con `SELECT extversion FROM pg_extension WHERE extname='vector'` (debe devolver ≥ 0.8.0). Si la versión es 0.7.x, upgrade trivial: `ALTER EXTENSION vector UPDATE TO '0.8.0'`.
- A14. **`uuidv7()` está disponible nativamente en PG 18**: feature core de la versión. Solo aplica si la BD es ≥ 18. **Validar al inicio de F0** con `SELECT uuidv7()` — debe devolver UUID válido sin error.

### Decisiones de la cuarta iteración — Inventario de extracción

Tras producir `docs/extraction-inventory.md` (validando 10 archivos de Hermes leyendo headers reales), se agregaron las siguientes decisiones:

47. **Inventario de extracción formal**: existe `docs/extraction-inventory.md` como **fuente única de verdad** para qué copiar/clonar/instalar. Cualquier implementación debe consultarlo antes de codificar desde cero. Cumple DRY de la constitución.
48. **Catálogo de COPY-HERMES ampliado a ~30 archivos** (era 6 en plan original): más allá de computer_use, browser, file_system, kanban, delegate, clarify — se confirmaron como copiables `memory_tool`, `mixture_of_agents_tool` (con reescritura para MiniMax), `terminal_tool`, `mcp_tool`, `session_search_tool`, `skills_tool` + 5 archivos asociados, `process_registry`, `cronjob_tools`, `checkpoint_manager`, `approval`, `interrupt`, `clarify_gateway`, `microsoft_graph_*`, `mcp_oauth*`, `registry`, `toolsets`, `managed_tool_gateway`, `url_safety`, `website_policy`, `path_security`, `osv_check`, `schema_sanitizer`, `lazy_deps`, `debug_helpers`, `tool_output_limits`, `patch_parser`, `fuzzy_match`, `budget_config`, `send_message_tool`, `transcription_tools`, `code_execution_tool`, `file_operations`, `file_state`, `binary_extensions`, carpeta `tools/environments/*` (10 archivos), carpeta `tools/computer_use/*` (4 archivos), carpeta `plugins/web/*`. Total real ~45 archivos copiables.
49. **OpenClaw NO se traduce**: confirmado tras inventario. Sirve solo como referencia conceptual. Cero CLONE-UPSTREAM desde OpenClaw.
50. **Browser tool: reescribir con `playwright-python`**, NO bundlear CLI `agent-browser`. Cero dependencias Node en el runtime. Se conserva COPY-HERMES de los tres archivos infra de browser (`browser_supervisor`, `browser_dialog_tool`, `browser_cdp_tool`) que sí son Python puro y útiles.
51. **Session search: SQLite FTS5**, NO Postgres tsvector como decía el plan §6. Razón: `tools/session_search_tool.py` de Hermes ya implementa 3 modos (DISCOVERY/SCROLL/BROWSE) en SQLite FTS5, copiable y sin LLM cost. Postgres sigue para vectores (TurboVec backup) + audit. SQLite solo para FTS5 de transcripts.
52. **MCP client de Hermes coexiste con el del 2.0**: NO se reemplaza `infra/mcp/execution_client.py`. El 2.0 sigue intacto. El 3.0 usa `enterprise/tooling/mcp_client.py` (COPY-HERMES). Cero refactor lateral del 2.0.
53. **`agent/file_safety.py` y `agent/redact.py` de Hermes son dependencias obligatorias** de `file_tools.py`. Se copian a `enterprise/governance/file_safety.py` y `enterprise/governance/redact.py`.
54. **Reducción de scope detectada**: 9 componentes que el plan iba a construir desde cero ya existen en Hermes (Dreaming scheduler base, ContextCompressor checkpoint base, SubagentRegistry process_registry base, QuotaManager budget_config base, Versionado checkpoint_manager base, ToolRegistry registry+lazy_deps base, MoA reescritura para MiniMax, Approvals 3 archivos base, Skills 5 archivos base). Esto reduce trabajo neto ~30% pero NO acorta cronograma — añade trabajo de adaptación y validación. F3 sube de 8 sem a ~12-15 sem realistas.
55. **Auditoría de licencias obligatoria al inicio de F0**: ~30 archivos COPY-HERMES + 32 paquetes PyPI WRAP-SDK. Atribución en cada archivo copiado: `# Adapted from Hermes Agent — original: tools/<filename>.py — License: <MIT|Apache-2.0>`.
56. **Orden de extracción**: 11 sprints (A→K) definidos en `docs/extraction-inventory.md §5`. Sprint A es base sin deps (registry, lazy_deps, schema_sanitizer, output_limits, debug_helpers).

### Decisiones de la quinta iteración — Política Python/MCP externo + observabilidad uniforme

Tras pasada exhaustiva sobre catálogos `README_mcp_6.md` + `README_mcp_7.md` (~450 MCPs analizados):

57. **Regla de oro**: si un MCP existe en Python → INTERNALIZAR. Si está en TS/JS/Go/Rust y es muy completo → CONSUMIR como MCP externo. Si es TS/JS con ≤5 tools simples → traducir solo las funciones. Resuelve el problema de mantener 43 wrappers (decisión del usuario: "debuguear 20/30 mcps sería muy difícil").
58. **Catálogo final 3-tier**:
   - **Tier 1 (internalizadas Python)**: ~30 tools = ~30 archivos COPY-HERMES + 25 WRAP-SDK (SDKs PyPI oficiales) + 15 Python MCPs identificados (open-webSearch, SerpApi, arxiv, pubmed, DuckDuckGo, markcrawl, MinerU, pdfmux, WhatsApp Python, Teams Python, Joinly, ScraperAPI, YouTube transcripts, Hacker News, biomcp).
   - **Tier 2 (MCPs externos via STDIO)**: ~15 MCPs TS/JS muy completos consumidos sin traducir (Gmail completo, MS365 oficial, Slack oficial, Discord, Telegram Bot full, WhatsApp Business 244 tools, Brave/Tavily/Exa search, GitHub/Linear/Notion/Asana/Atlassian oficiales).
   - **Tier 3 (traducir tools simples)**: 3 candidatos (Google Tasks 3 tools, CZK FX 3 tools, Kagi 3 tools).
59. **MCPs LATAM oportunidad futura**: no existen MCPs nativos para DIAN/RUES/SUNAT/SII/Banco República. Se construyen bajo demanda real (YAGNI estricto). Documentado como roadmap en `docs/extraction-inventory.md §8.4`.
60. **`MCPExecutionClient` del 2.0 se reutiliza** para Tier 2: ya está implementado en `infra/mcp/execution_client.py` + caché smart. Cero código nuevo para consumir los 15 MCPs externos.
61. **Contrato `ToolWrapper` unificado** (clave para sostenibilidad):
   - **Mismo Protocol** para internas y externas: `name`, `domain`, `is_external_mcp: bool`, `requires_auth`, `healthcheck()`, `execute(tool_name, args)`.
   - **Logs estructurados con prefijo común**: internas `vigilador.tools.<dominio>.<tool>`, externas `vigilador.mcp_ext.<provider>.<tool>`.
   - **Test E2E mínimo (~50 LOC) obligatorio por tool**: import sin error, healthcheck OK con mock-creds, 1 llamada real con args mock-friendly, schema JSON válido.
   - **Circuit breaker uniforme**: 3 fallos en 60s → DOWN 5 min, `ToolRegistry` la excluye automáticamente del listing Tier 1 del agente, alerta al canal del usuario, recuperación automática tras cooldown.
   - Resultado: **flujo de debug ÚNICO** para 55+ capacidades. El dashboard dice cuál falló, el log por qué, el circuit breaker la aísla.
62. **Total de capacidades**: ~55 (40 internas + 15 externas), pero **solo 25-30 son código que mantenemos directamente**. El resto lo mantienen Microsoft/Google/Slack/Brave/Tavily/Exa/Anthropic.
63. **Reducción de F3 confirmada**: el catálogo internalizado pasa de 43 a ~30 archivos efectivamente nuestros + ~25 wrappers thin sobre SDKs PyPI. F3 baja de 12-15 sem realistas a ~8-10 sem (más MCPs externos, menos código propio).

### Decisiones de la sexta iteración — Supervisor MCP + dominios nuevos + API keys + dedup

Tras pregunta del usuario sobre cómo manejar múltiples MCPs y gaps detectados (faltan diseño/ingeniería/media/analytics; duplicados; falta info API keys):

64. **`MCPProcessSupervisor` (nuevo)**: cada MCP externo Tier 2 corre en su propio proceso STDIO aislado, gestionado por `enterprise/mcp/process_supervisor.py` (~150 LOC). Auto-restart con backoff exponencial (1s→2s→4s→8s→16s→32s, max 5 retries). Logs separados por MCP en `~/.vigilador/mcp-logs/<name>.jsonl`. Tras 5 fallos consecutivos → STUCK + alerta al usuario, sin retry hasta intervención manual. Config en `config/mcp/external.yaml`. CLI admin: `vigilador-admin mcp <list|restart|stop|start|logs> <name>`. Métricas Prometheus por MCP. Resuelve la pregunta "¿cómo debuguear 20-30 MCPs?": fallos aislados, debug por proceso, restart independiente. Detalle en `docs/extraction-inventory.md §10`.
65. **4 dominios nuevos**: `design` (Figma, excalidraw_architect, mermaid, photopea), `engineering` (blender, jupytercad), `media` (fal_media, comfyui, imagen_google, elevenlabs_tts, suno_music, davinci_resolve, dalle_unified), `analytics` (powerbi, metabase, csvglow, mcp_dashboards, snowflake, bigquery, clickhouse, tableau). Total dominios sube de 13 a **17**. Detalle en `docs/extraction-inventory.md §9`.
66. **Legal no es dominio MCP**: se cubre con `enterprise/skills/learned/legal-*.yaml` + templates en `config/templates/contratos/` (ya en plan §4.6). DocuSign queda como SDK Python opcional bajo demanda, no dominio. Decisión del usuario explícita.
67. **API keys declaradas por cada tool**: el contrato `BuiltinTool` (§4.3) se amplía con 4 campos obligatorios:
   - `requires_key: bool`
   - `env_var: str | None` (ej. `TAVILY_API_KEY`)
   - `signup_url: str | None` (dónde obtenerla)
   - `pricing: Literal["free", "freemium", "paid", "enterprise"]`
   El **onboarding wizard** (§17.1) usa estos campos para guiar al usuario en qué keys conseguir. El **tool-gating** (#18) usa `requires_key` + presencia de env_var. Detalle en `docs/extraction-inventory.md §11.3`.
68. **Deduplicación estricta**: una entrada por función en el catálogo. Si hay múltiples implementaciones (ej. 3 DuckDuckGo MCPs), elegir una y listar el resto en "Alternativas conocidas" del inventario. Total catálogo final: **~69 capacidades** (40 Tier 1 + 23 Tier 2 + 6 Tier 3), pero solo ~46 son código que mantenemos directamente.
69. **17 tools FREE sin API key identificadas para Tier 1**: excalidraw_architect, mermaid, blender, jupytercad, comfyui, csvglow, mcp_dashboards, davinci_resolve (free tier), open-webSearch, DuckDuckGo MCP, arxiv MCP, pubmed MCP, Hacker News MCP, markcrawl, mineru, pdfmux, fetch oficial. Estas cubren ~40% de casos de uso empresariales sin que el usuario tenga que conseguir una sola API key. Ideal para onboarding rápido del wizard.
70. **11 tools paid premium descartadas v3.0 inicial**: Fusion 360, Tableau, Power BI Enterprise, Snowflake, BigQuery (consumption), Runway, Pika, Sora, DaVinci Resolve Studio, Mixpanel, Amplitude. Marcadas como "agregar bajo demanda explícita" en `docs/extraction-inventory.md §11.4`.

### Decisiones de la séptima iteración — Apps locales (gap PYMEs no-cloud)

Tras pregunta del usuario "¿los MCPs como Tableau y PowerBI no funcionan manejando la propia PC si uno tiene las apps?":

71. **Sub-tools `*_local.py` por dominio (nuevo)**: el catálogo cloud no cubría el 60-70% de PYMEs LATAM que tienen Power BI Desktop, Tableau Desktop, Excel local, Outlook local SIN cloud Business. Se agregan **10 sub-tools locales**:
   - `analytics/powerbi_file_reader.py` (lee `.pbix` via pbi-tools — extrae modelo + queries + DAX)
   - `analytics/tableau_file_reader.py` (lee `.twbx`/`.hyper` via tableauhyperapi oficial)
   - `finance/excel_local.py` (xlwings — interactúa con Excel abierto, macros, pivot refresh)
   - `documents/powerpoint_local.py` (pywin32 COM o python-pptx)
   - `documents/word_local.py` (pywin32 COM o python-docx)
   - `productivity/outlook_local.py` (pywin32 COM — lee correos local sin OAuth)
   - `productivity/outlook_calendar_local.py` (pywin32 COM — calendario sin OAuth)
   - `engineering/autocad_local.py` (pyautocad COM Win)
   - `engineering/solidworks_local.py` (pywin32 + SolidWorks COM API)
   - `communication/imessage_local.py` (SQLite local macOS)
   Detalle completo en `docs/extraction-inventory.md §12`.
72. **`LocalAppDetector` (nuevo)**: `enterprise/tooling/local_app_detector.py` (~80 LOC) detecta apps instaladas al boot via registry Windows (HKLM\Software\...) y `/Applications/` macOS. `ToolRegistry` consulta esto: si app instalada → tool `*_local` aparece en Tier 1, si no → gating-out automático (mismo mecanismo que falta-de-API-key, decisión #18). Tools `*_file_reader.py` (lectura pura de archivos) NO requieren app instalada y siempre están disponibles.
73. **Resolución cloud vs local**: si el usuario tiene ambos disponibles, `config/settings.yaml > tools.<tool>.prefer: local | cloud` define preferencia. Default `local` por privacidad (datos nunca salen del PC). Documentado en §12.4 del inventario.
74. **Plataformas soportadas por sub-tools locales**:
   - Win+macOS: excel_local (xlwings), powerpoint_local (python-pptx fallback), word_local (python-docx fallback)
   - Win only: outlook_local, outlook_calendar_local, autocad_local, solidworks_local (COM)
   - macOS only: imessage_local
   - Cross-platform (Win+macOS+Linux): powerbi_file_reader, tableau_file_reader (lectura pura de archivos)
75. **Total catálogo final**: pasa de ~69 a **~79 capacidades** (10 sub-tools locales nuevas). Mantenibilidad: los `*_local.py` son wrappers thin sobre xlwings/pywin32/tableauhyperapi/pbi-tools — esfuerzo similar a un WRAP-SDK estándar.
76. **Beneficio clave**: cobertura de PYMEs no-cloud + privacidad máxima (datos jamás salen del PC para análisis local) + cero API key + cero cuotas. Resuelve el gap detectado por el usuario.

### Decisiones de la octava iteración — Auditoría de coherencia + fix CQS

Tras revisión sistemática del plan contra la constitución v1.2.0 (principio Gobernanza: "Revisión de cumplimiento MUST ejecutarse en cada ciclo de especificación y planificación"):

77. **Fuente única de verdad sobre número de tools**: **~79 capacidades total** desglosadas como **40 Tier 1 (Python internalizadas) + 23 Tier 2 (MCPs externos STDIO) + 6 Tier 3 (TS traducidas) + 10 sub-tools `*_local.py`**. Toda mención previa a 20/30/35/41/43/55/69 está obsoleta y debe leerse como histórico. Cuando se referencie un número en otras secciones, usar este desglose.
78. **Decisiones #5 y #14 marcadas como OBSOLETAS** (preservadas por trazabilidad — principio 5 constitución). Conservar en lista por auditabilidad fuente→decisión→resultado.
79. **Aclaración embeddings vs LLM (cierra ambigüedad en decisión #38)**: "Solo MiniMax" aplica al **LLM generativo** (chat completion + tool calling). NO aplica a embeddings ni reranker, que son: local `bge-m3` + `bge-reranker-v2-m3` por defecto en 3.0, con switch opcional a Gemini para compatibilidad 2.0. Esto NO viola la decisión "solo MiniMax" porque embedding/reranker son funcionalmente distintos de LLM generativo.
80. **Aclaración ContextCompressor (cierra ambigüedad en decisión #54)**: lo copiado de Hermes son `checkpoint_manager.py` (versionado) y `memory_tool.py` (frozen snapshot). El **template de 13 secciones es diseño propio inspirado en Hermes**, NO copia directa. Esto evita decir "ContextCompressor de Hermes" cuando lo que existe es la infraestructura subyacente.
81. **Fix CQS — health monitor como proceso aparte (decisión del usuario)**: `enterprise/observability/health_monitor.py` corre cada 30s pingueando tools/MCPs vía `healthcheck()`. Actualiza tabla `tool_health(name, status, last_check, fail_count, last_error)`. `ToolRegistry.list_tools_for_role` solo **LEE** esa tabla (query pura sin side-effects). Circuit breaker y alertas son responsabilidad del health_monitor (commands). Cumple CQS + SRP + cierra violación detectada en auditoría.
82. **Supuesto A10 — capacidad de ejecución**: el usuario asume el cronograma de ~28 semanas (F0-F5) con el catálogo completo de 79 capacidades. Esto implica equipo mínimo de 2-3 ingenieros senior O cronograma extendido a 9-12 meses si es 1 persona. **Decisión consciente del usuario**. Si el cronograma se incumple, NO es por fallo del plan sino por capacidad asumida — re-evaluar entonces si reducir scope a MVP (10-15 capacidades) o sumar gente.
83. **Estructura del plan acumula 8 iteraciones**: futuras revisiones deberían consolidar en secciones temáticas en lugar de cronológicas. Conservar la cronología solo en un apéndice "Historial de decisiones" para auditabilidad. Esta consolidación es trabajo de F0.

### Decisiones de la novena iteración — Arquitectura de persistencia oficial

Pregunta del usuario: "¿qué base de datos vamos a utilizar?". Auditoría reveló 5 motores mencionados sin arquitectura unificada. Decisiones formales:

84. **Arquitectura de persistencia: 5 motores, cada uno con rol único** (decisión consciente del usuario tras evaluar alternativas):

| Motor | Versión exigida | Rol único | Tablas/archivos típicos |
|---|---|---|---|
| **PostgreSQL** | **18+** (instalado por el usuario, decisión #91) con asyncpg **0.30+** + SQLAlchemy **2.0.36+** | Datos transaccionales: metadata, multi-tenancy, audit estructurado SQL, prompt_versions, oauth_credentials, ingested_documents, document_chunks (metadata + embedding backup), subagents, usage_quotas, kg_nodes/edges, tool_health, pending_approvals | 12+ tablas |
| **pgvector** | **0.8+** (extensión de PostgreSQL 18, ya instalada por el usuario) | Columna `embedding vector(768)` en `document_chunks` como **backup vectorial + JOINs SQL** (consultas mixtas vector + filtro WHERE acl_scopes). NO es el índice primario de búsqueda (ése es TurboVec). | `document_chunks.embedding` |
| **TurboVec** | `pip install turbovec` (Rust+Python, 4-bit PQ) | **Índice vectorial primario** para búsqueda semántica. 16× menos memoria. Soporta `allowlist` para ACL a nivel kernel SIMD. Persiste en `~/.vigilador/turbovec/<tenant>.tq` | Archivos `.tq` por tenant |
| **SQLite + FTS5** | Built-in Python 3.11+ stdlib | **Cross-session full-text search** sobre transcripts (DISCOVERY/SCROLL/BROWSE modes). COPY-HERMES de `session_search_tool.py`. Sin LLM cost. `~/.vigilador/sessions/<tenant>.db` | Tabla `sessions_fts` con FTS5 virtual |
| **JSONL files** | Plain text + rotación diaria | **Logs operacionales** sin necesidad de query SQL: audit estructurado (`~/.vigilador/audit/<fecha>.jsonl`), dream-log (`~/.vigilador/dream-log/<fecha>.md`), mcp-logs por MCP (`~/.vigilador/mcp-logs/<name>.jsonl`), healthcheck.log | Archivos rotados por fecha |
| **YAML files** | Versionable en git | **Configuración declarativa**: SOUL.md, COMPANY/*.md (5 archivos), playbooks/*.yaml, templates/**, skills/learned/*.yaml, settings.yaml, mcp/external.yaml | `config/` directory |

85. **TurboVec primario + pgvector backup** (validación A/B):
   - Fase 1 (semanas 4-6 de F2): **doble write** a TurboVec **y** pgvector. Lectura sigue pgvector.
   - Fase 2 (semanas 6-7): A/B test con `recall@10` métrica. Criterio de éxito: TurboVec ≥ 0.92 vs pgvector baseline.
   - Fase 3 (semana 7+): si pasa, **TurboVec se vuelve lectura primaria**. pgvector se mantiene como **backup + JOINs SQL** (la columna `embedding` sigue ahí para queries mixtas `WHERE tenant_id=X AND acl_scopes @> ARRAY[...]` con ranking vectorial).
   - Si A/B test falla: pgvector sigue como primario, TurboVec se descarta para v3.0 (supuesto A3 desmentido).
   - **Garantía de no-corrupción**: pgvector siempre tiene el vector original `float32`, así que aún si TurboVec corrompe su índice `.tq`, podemos re-construirlo desde pgvector.

86. **Multi-tenancy aplica a TODAS las capas**:
   - Postgres: `tenant_id UUID NOT NULL` en todas las tablas (decisión #26 confirmada).
   - TurboVec: 1 archivo `.tq` por tenant (`~/.vigilador/turbovec/<tenant_uuid>.tq`). Aislamiento físico.
   - SQLite FTS5: 1 archivo `.db` por tenant (`~/.vigilador/sessions/<tenant_uuid>.db`). Aislamiento físico.
   - JSONL audit: prefijo `tenant_id` en cada línea (filtro `grep` o jq).
   - YAML config: opcionalmente `config/tenants/<tenant>/` para configs per-tenant (v3.0 inicial single-tenant, esto se activa en v3.1).

87. **Backup unifica 3 fuentes vivas** (extensión de decisión #28):
   - `pg_dump --format=custom` de Postgres (incluye pgvector como blob binary)
   - `tar -czf turbovec-<tenant>-<fecha>.tar.gz ~/.vigilador/turbovec/<tenant>.tq` por tenant
   - `tar -czf sessions-<tenant>-<fecha>.tar.gz ~/.vigilador/sessions/<tenant>.db` por tenant
   - Logs JSONL **NO se backupean** (efímeros, rotan a 30 días). Si se requiere retención SOC 2, migrar a tabla SQL (post-v3.0).
   - YAML se versiona en git separadamente (responsabilidad del usuario, no del harness).
   - Restore probado semanal en Dreaming (decisión #28).

88. **Migraciones**:
   - Postgres: **Alembic** (ya decidido en #43). Schema versionado, auto-run en boot.
   - TurboVec: NO requiere migraciones (formato `.tq` es estable, upstream mantiene retrocompatibilidad).
   - SQLite FTS5: NO requiere migraciones (schema fijo de `sessions_fts` virtual table).
   - JSONL/YAML: sin migraciones (formato libre).
   - **Supuesto nuevo A11**: Alembic gestiona TODAS las tablas Postgres incluyendo pgvector columns. **Verificar en F0** que las migraciones que añaden columnas `vector(768)` se ejecutan correctamente.

89. **Conexión y configuración en `config/settings.yaml`** (actualizada para PG 18):
```yaml
database:
  postgres:
    url: "postgresql+asyncpg://vigilador:${POSTGRES_PASSWORD}@localhost:5432/vigilador"
    pool_size: 10
    max_overflow: 20
    version_min: "18.0"                       # decisión #91
    pgvector_version_min: "0.8.0"             # decisión #91
  turbovec:
    base_path: "~/.vigilador/turbovec"
    bit_width: 4
    dimension: 768
  sqlite_fts:
    base_path: "~/.vigilador/sessions"
```

90. **Decisión #79 confirmada**: embeddings (Gemini o local bge-m3) producen vectores `float32` de 768 dimensiones. TurboVec los cuantiza a 4-bit PQ. pgvector los almacena nativos `float32`. SQLite NO almacena vectores. JSONL NO almacena vectores. Una sola convención de dimensionalidad en toda la pila.

### Decisiones de la décima iteración — PostgreSQL 18 instalado por el usuario

Tras confirmación del usuario: "tengo instalado la versión 18 de postgreSQL".

91. **PostgreSQL 18 como versión oficial mínima** (sustituye decisión #84 línea Postgres): el usuario ya tiene PG 18 instalado con pgvector funcionando. Versión mínima sube de "16+" a **"18+"**. asyncpg requiere **0.30+** para soporte oficial PG 18. SQLAlchemy **2.0.36+** (mejoras menores). Beneficio: ganamos features sin esfuerzo extra.

92. **UUIDv7 en tablas de alto volumen** (aprovechamiento PG 18): `document_chunks` y `audit_events_jsonl_index` usan `DEFAULT uuidv7()` en lugar de `uuid_generate_v4()`. Beneficios: IDs ordenados por timestamp → mejor locality en índices B-tree, menos fragmentación al escalar a millones de filas, queries por rango temporal más rápidas. Resto de tablas (oauth_credentials, subagents, pending_approvals, prompt_versions, etc. — todas con miles, no millones de filas) **mantienen uuid4** — no agregamos dependencia PG 18 donde no se justifica. Cumple AHA + KISS.

93. **Async I/O de PG 18 como tuning recomendado en F0**: se documenta en `docs/postgres-tuning.md` (nuevo):
   - Windows (target del usuario): `io_method = worker` en `postgresql.conf`
   - Linux production: `io_method = io_uring` cuando aplique
   - No requiere cambio de código en el harness (solo settings de Postgres)
   - Beneficio: mejor performance en queries paralelas del `BranchCoordinator` y en TurboVec backup writes
   - **Verificar mejora con benchmark básico en F0**: query de 100 chunks vectoriales con/sin async I/O.

94. **Features de PG 18 explícitamente descartados v3.0** (cumplir YAGNI):
   - **Virtual generated columns**: NO usar hasta detectar query lenta concreta que las justifique.
   - **OAUTHBEARER SASL para auth a la BD**: NO usar v3.0. Password auth tradicional sirve. El SSO de decisión #30 es para usuarios del harness, no para conectarse al Postgres.
   - **Logical replication mejorada**: NO usar v3.0. Multi-tenancy single-instance no la necesita. Se evaluará en v3.x si hay multi-region.
   - **Skip scan B-tree**: optimización automática sin acción requerida, "gratis" — sin entrada explícita.

95. **Sin downgrade-path declarado**: el plan asume PG 18+. Si alguien quiere desplegar en PG 16 o 17, tendría que: (a) cambiar `uuidv7()` a `uuid_generate_v4()` en 2 tablas, (b) cambiar `version_min` en settings. Es un porting trivial pero **no es objetivo del v3.0** soportar PG <18. Cumple constitución #2 (Simplicidad obligatoria: no agregar configurabilidad no pedida).

### Decisiones de la décimo-primera iteración — Capacidades avanzadas para "agente potente"

Pregunta del usuario: "¿qué otras implementaciones podríamos hacer para que sea un agente potente?". Tras evaluar 19 ideas en 5 categorías, el usuario seleccionó 4 categorías para v3.0 (Inteligencia + Autonomía + Calidad + Confianza), descartó Voice channel a v3.1.

#### Categoría Inteligencia (~1000 LOC) — F3 ampliada

96. **Self-correction loop** (`enterprise/intelligence/self_correction.py` ~200 LOC): patrón `generate → critique → revise → return` inspirado en Reflexion (arXiv:2303.11366). Tool interna `self_reflect(draft, criteria)`. **Solo aplica a outputs de alto valor** (reportes, correos, código, decisiones de debate) — NO en chitchat. 1 llamada LLM extra solo cuando vale la pena. Trigger configurable per-playbook.

97. **Chain-of-Verification (CoVe)** (`enterprise/intelligence/cove_verifier.py` ~300 LOC): antes de afirmar un hecho factual, el agente genera 3-5 preguntas de verificación, las responde con sus tools, y solo afirma si las respuestas son consistentes. Basado en paper Meta 2023 (reduce alucinaciones 40-60%). **Aplica a**: respuestas con números financieros, citas legales, datos de clientes, afirmaciones técnicas específicas. Detector trigger: regex sobre la respuesta del LLM busca patrones de afirmación factual.

98. **Confidence scoring + abstention** (`enterprise/intelligence/confidence_scorer.py` ~150 LOC): cada respuesta lleva score de confianza calibrado (0.0-1.0) basado en: (a) consistencia entre múltiples llamadas con misma query, (b) cantidad y calidad de citations recuperadas, (c) match con frozen snapshot de COMPANY.md. Si confianza < 0.5 → agente **se abstiene** ("no tengo información suficiente para responder con certeza") o pide aclaración. Métrica Prometheus `vigilador_response_confidence{playbook,domain}`. Cumple POLA (predecible) y manejo errores estricto (no inventar).

99. **Few-shot retrieval para outputs consistentes** (`enterprise/intelligence/fewshot_retriever.py` ~150 LOC): antes de generar reporte/correo/análisis, busca en TurboVec 3-5 ejemplos previos similares aprobados por el usuario y los inyecta como few-shot en el prompt. **Integra naturalmente con Writing Style Learning** (decisión #20) — los ejemplos aprobados por el usuario ya son la base del style profile. Mejora coherencia con estilo histórico del tenant.

#### Categoría Autonomía (~1200 LOC) — F4 ampliada con nuevo playbook prioritario

100. **Goal-driven mode** (`enterprise/orchestration/goal_pursuit/` ~500 LOC): nuevo playbook `goal-pursuit.yaml` que persigue objetivos durante horas/días. Componentes:
   - `GoalDecomposer`: descompone goal complejo en sub-goals con dependencias.
   - `StepDependencyResolver`: secuencia y paraleliza pasos según DAG.
   - `CheckpointReporter`: reporta progreso por canal cada N pasos o al detectar bloqueo.
   - `ApprovalGate`: pide aprobación humana en puntos críticos (reusa decisión #44 approval workflows).
   - Persistencia completa en `goal_pursuits` table (sub-table de `subagents` con `parent_goal_id`, `status: ACTIVE|PAUSED|COMPLETED|FAILED`).
   **Diferencia con orquestador actual**: plan reactivo responde a preguntas. Goal-driven **persigue objetivos**. Ejemplo: "consigue 10 leads B2B sector logística Colombia y agéndalos en HubSpot" → 4-8 horas de ejecución autónoma con 3-4 checkpoints de aprobación. **Es lo que distingue 'asistente' de 'colega'**.

101. **Long-running tasks con persistencia y pause/resume** (extensión de `SubagentRegistry`, ~200 LOC): sesiones que duran días, pausadas y reanudables. Estado completo en DB (no en memoria — sobrevive restart del harness). Nuevas columnas en `subagents`: `status: ACTIVE|PAUSED|COMPLETED|FAILED|WAITING_APPROVAL`, `pause_reason`, `resume_token`, `last_progress_at`. CLI admin: `vigilador-admin task <list|pause|resume|cancel> <id>`. Habilita goal-driven mode (#100) y skill learning ejecuciones complejas (#15).

102. **Proactive triggers event-driven** (`enterprise/triggers/event_listener.py` ~500 LOC) — distinto de Dreaming (cron periódico):
   - **Email triggers**: webhook Gmail push / IMAP IDLE → analiza nuevo email, prioriza, decide si requiere acción.
   - **Slack/Teams triggers**: webhook menciones del cliente importante → alerta + contexto.
   - **Metric anomaly triggers**: si Prometheus detecta caída > X% en métrica de negocio configurada → investiga causa automáticamente.
   - **Calendar/deadline triggers**: compromisos en `COMPANY/processes.md` con fecha próxima → recordatorio inteligente con contexto preparado.
   - **CRM triggers**: nuevo deal en HubSpot vía webhook → playbook `deal-research` (también cubre webhook bidireccional descartado antes — ahora se rescata como subset).
   Tabla `event_subscriptions(tenant_id, source, filter, playbook, enabled)`. Cada trigger pasa por approval workflow si su playbook lo requiere.

#### Categoría Calidad de outputs (~800 LOC) — F3 ampliada

103. **Tool result caching con TTL adaptativo** (extensión de `MCPSmartCache` del 2.0 + nuevo `enterprise/tooling/adaptive_cache.py` ~250 LOC):
   - TTL por tipo de query: búsqueda noticias = 1h, definición técnica = 30d, datos de cliente = 5min, dashboard analytics = 15min.
   - Volatilidad de fuente: APIs financieras tiempo real = no-cache; documentación estática = días.
   - **Cache invalidation por evento**: `ingestion_sync` detecta cambio en doc X → invalida entradas que lo referencian.
   - Estimación: -40% costos LLM + -90% latencia en queries repetidas (típicas en debates y goal-pursuit).
   - Métrica `vigilador_cache_hit_ratio{tool,domain}` para validar beneficio.

104. **Citations obligatorias verificables** (`enterprise/intelligence/citation_engine.py` ~250 LOC):
   - Toda afirmación factual lleva `[¹]` con tooltip clickeable → vista de chunk indexado o URL externa.
   - Formato structured: `{"text": "...", "claim_span": [12, 45], "citation_id": "chunk_uuid_xyz", "confidence": 0.87}`.
   - Trigger: aplica en outputs de research, informes, análisis. NO en chitchat.
   - Integración con dashboard (#12.2): usuario click → ve chunk original + fuente + acl_scopes.
   - Cumple compliance evidence (#31) y audit estructurado.

105. **Outputs duales structured + free-form** (extensión `enterprise/tooling/output_formatter.py` ~300 LOC):
   - Cada respuesta del agente tiene dos versiones:
     - **Free-form**: lo que se muestra al usuario en el canal (Telegram, WhatsApp, Web).
     - **Structured JSON**: consumible por programas/webhooks/integraciones.
   - Schema declarado en el `playbook.yaml > output_schema` (ya existía la sección, ahora se aprovecha).
   - Habilita pipelines: "respuesta de análisis de mercado → POST a webhook propio del usuario que dispara otro proceso interno".

#### Categoría Confianza/Seguridad (~750 LOC) — F0/F3 ampliadas

106. **Prompt injection defense con cuarentena** (`enterprise/governance/prompt_injection_detector.py` ~200 LOC) — decisión usuario:
   - Todo input externo (correos entrantes, PDFs indexados, contenido scrapeado, mensajes WhatsApp) pasa por detector ANTES de tocar el LLM.
   - Patrones detectados: heurísticas custom ("ignore previous instructions", "system:", "you are now"), dataset de Lakera (open-source), embeddings comparados contra corpus de ataques conocidos.
   - Si positivo: input se **cuarentena** (NO llega al LLM), alerta al usuario por canal preferido con detalle, audit log.
   - Falsos positivos: usuario puede aprobar explícitamente en dashboard ("este es un correo legítimo, despublicar de cuarentena").
   - Métrica `vigilador_pi_quarantined_total{source,severity}`.
   - **Crítico para enterprise serio**: sin esto, un PDF malicioso indexado puede secuestrar al agente.

107. **Capability tokens granulares por sesión** (`enterprise/auth/capability_tokens.py` ~300 LOC):
   - En lugar de "este agente tiene acceso a Slack", específicamente "este agente puede enviar mensajes a #ventas hasta las 18:00 hoy".
   - Tokens efímeros, revocables, con scope/TTL/rate-limit per-token.
   - Aplica a: skills aprendidos, delegate_task, sesiones de alto riesgo (goal-pursuit con acciones financieras o de comunicación externa).
   - Tabla `capability_tokens(id, parent_session_id, scopes, rate_limit, expires_at, revoked_at)`.
   - Integra con tool-gating (#18): si token expirado/revocado → tool NO aparece en Tier 1 para esa sesión.

108. **Anomaly detection en uso del agente** (`enterprise/governance/anomaly_detector.py` ~250 LOC):
   - Stats simples sobre `audit_events_jsonl_index`: baseline de patrones del usuario (qué tools usa, en qué horarios, sobre qué entidades).
   - Detección: si pide eliminar 1000 contactos cuando históricamente nunca elimina → alerta + bloquea acción.
   - Aplica especialmente a goal-driven mode (#100): cualquier desviación significativa del baseline durante ejecución autónoma → pausa + aprobación humana.
   - Cumple defensa contra cuentas comprometidas (cero conocimiento previo del atacante sobre patrones del usuario real).

#### Categoría Alcance — parcial

109. **Webhook bidireccional** (`enterprise/triggers/webhook_handler.py` ~300 LOC): **incluido como subset de #102** (proactive triggers CRM). Endpoint `/api/webhooks/<source>` con HMAC verification. Disparadores configurables en `event_subscriptions`.

110. **Scheduled outputs** (`enterprise/dreaming/tasks/scheduled_reports.py` ~150 LOC): "cada lunes 8 AM genera dashboard KPIs fin de semana y mándamelo a Telegram con Excel adjunto". Reusa cron de Dreaming (#10). Nueva tool interna `schedule_report(cron_expr, playbook, output_target)`. Persistencia en tabla `scheduled_reports(id, tenant_id, cron, playbook, output_target, enabled)`.

111. **Voice channel descartado v3.0** (decisión consciente): Whisper local + TTS para WhatsApp/Telegram voice queda como **roadmap v3.1**. Razón: ~400 LOC + Whisper local pesa 1.5GB. Mejor consolidar texto en v3.0, voice cuando esté estable. **Nota LATAM**: pierde diferenciador para PYMEs que usan voice notes, pero el riesgo de complejidad supera el beneficio inicial.

#### Resumen de impacto en el plan

112. **Nuevo total de LOC adicionales**: ~3700 LOC (1000 Inteligencia + 1200 Autonomía + 800 Calidad + 750 Confianza + 450 Alcance parcial) sumadas al plan previo. F3 y F4 se extienden:
   - F3: +Inteligencia +Calidad +PI defense + tokens granulares + anomaly → de 12-22 sem realistas a **16-26 sem**.
   - F4: +Goal-driven + long-running + proactive triggers → de 20-22 sem a **22-25 sem**.
   - F5: +scheduled outputs → sin cambio mayor.
113. **Catálogo de capacidades funcionales finales sube a ~85**: las 79 tools previas + 6 capacidades intelligence/autonomy (self-correction, CoVe, confidence, few-shot, goal-pursuit, proactive triggers). Estas NO son "tools del usuario" sino capacidades del orquestador.
114. **Supuesto A10 reforzado**: el plan ahora exige ~3700 LOC adicionales. Equipo 2-3 ingenieros senior necesario, o cronograma 12-14 meses si 1 persona. Si en F0 se detecta capacidad menor, **eliminar primero**: Voice (ya descartado), Anomaly detection (#108), Long-running pause/resume (#101), Few-shot retrieval (#99). El núcleo defendible es: Self-correction (#96) + CoVe (#97) + Citations (#104) + Caching (#103) + PI defense (#106).

| Eje | Decisión |
|---|---|
| Migración | Incremental: subpaquete `enterprise/` paralelo. 2.0 intacto. |
| Núcleo conceptual | Orquestador generalizado que **despliega N agentes según complejidad**. Cada agente es especializado por rol + tools restringidas + tool discovery progresivo. |
| LLM | **Solo MiniMax**. M-2.7 default; M-2.5 alterna en debates para diversidad cognitiva sin multiplicar dependencias. |
| Frameworks | CrewAI para combos nuevos (debate, decisión, market-research). `BranchCoordinator` actual sigue corriendo `technology-watch`. |
| MCPs | **Estrategia 3-tier** (decisión usuario): Tier 1 = ~40 tools Python internalizadas (COPY-HERMES + WRAP-SDK + Python MCPs). Tier 2 = ~23 MCPs TS/JS completos como externos STDIO. Tier 3 = ~6 MCPs TS simples traducidos. Sub-tools `*_local.py` = ~10 wrappers de apps locales (xlwings, pywin32, tableauhyperapi, pbi-tools). Detalle en `docs/extraction-inventory.md §§8-12`. |
| Apps locales | Sub-tools `*_local.py` por dominio para automatizar Excel, Power BI Desktop, Tableau Desktop, AutoCAD, SolidWorks, Outlook local, etc. `LocalAppDetector` gating-out automático si la app no está instalada. Preferencia `local` sobre cloud por privacidad (datos jamás salen del PC). Cubre el 60-70% de PYMEs LATAM no-cloud. Detalle en `docs/extraction-inventory.md §12`. |
| Indexación | TurboVec como nuevo backend de `VectorIndex` port. pgvector se mantiene para JOINs SQL. Doble write inicial, A/B test, recall@10 ≥ 0.92 antes de cortar lectura pgvector. |
| Embeddings + reranker | **Locales por defecto en 3.0** (`BAAI/bge-m3` multilingüe + `BAAI/bge-reranker-v2-m3` cross-encoder via `sentence-transformers`). Switch a Gemini en `config/settings.yaml`. El 2.0 sigue con Gemini sin tocar. |
| Idioma | **Interno (lo que ve el LLM) en inglés**: system prompts, BranchOverlay, AgentRole, tool descriptions, SOUL.md, COMPANY.md, playbooks YAML. **Externo (al usuario) en español o idioma detectado**: respuestas, correos, informes, mensajes en canales, entregables de Templates. `LanguageRouter` autodetecta por turno. |
| Multi-tenancy | `tenant_id` en TODAS las tablas nuevas desde día 1. v3.0 single-tenant, schema preparado. |
| Acciones financieras | **Cero capacidad de mover dinero**. Tools `finance/` son read-only o generan borradores/reportes. Módulo de inversiones queda como roadmap futuro (cuenta bancaria aislada). |
| Aprobaciones | Approval workflows en envíos masivos email (>10), mutaciones masivas CRM (>5), primera ejecución autónoma de skill aprendido. **El agente NUNCA modifica `config/soul.md`, `config/company/*.md`, `config/templates/*` ni políticas** — solo propone cambios al usuario. |
| Operación sobre cuentas | Bot accounts cuando estén disponibles + OAuth del usuario con scopes restrictivos. **Cero permiso de delete** en todas las tools (cualquier método `delete_*` se gating-out automáticamente). |
| Interfaz | Solo canales (Web/SSE, Telegram, WhatsApp). **Sin CLI pública**. CLI interna solo para ops del propio harness (admin, no usuario final). |
| Vigilancia tecnológica | Plugin `technology-watch`. API `/research/*` sigue funcionando idéntica. |

**Principio rector**: lo que ya funciona se preserva. Lo nuevo se construye al lado. Cada componente nuevo cumple SRP y se conecta vía port existente o nuevo (DIP).

---

## 2. Arquitectura técnica

### 2.1 Estructura de carpetas

```
src/vigilancia_multiagente/
├── api/
│   ├── routes/                              [EXISTENTE]
│   └── channels/             [NUEVO]
├── application/                             [EXISTENTE — preservado]
│   ├── orchestration/orchestrator_service.py
│   ├── execution/branch_coordinator.py
│   ├── agents/
│   └── governance/
├── enterprise/               [NUEVO — núcleo del 3.0]
│   ├── orchestration/
│   │   ├── complexity_classifier.py         clasifica SIMPLE/MODERADA/COMPLEJA
│   │   ├── playbook_runner.py               carga YAML, instancia agentes
│   │   ├── crewai_bridge.py                 wrapper sobre crewai.Crew/Agent/Task
│   │   ├── debate_coordinator.py            multi-agent debate con moderador
│   │   ├── subagent_registry.py             persiste tree de subagentes (depth-aware) + #101 pause/resume
│   │   └── goal_pursuit/    [NUEVO #100]
│   │       ├── decomposer.py                descompone goal en sub-goals con dependencias
│   │       ├── dependency_resolver.py       secuencia/paraleliza pasos según DAG
│   │       ├── checkpoint_reporter.py       reporta progreso por canal cada N pasos
│   │       └── approval_gate.py             reusa approval workflows (#44) en puntos críticos
│   ├── ingestion/
│   │   ├── orchestrator.py                  pipeline fetch→parse→chunk→embed→index
│   │   ├── connectors/
│   │   │   ├── google_drive.py
│   │   │   ├── onedrive.py
│   │   │   ├── whatsapp.py
│   │   │   ├── local_fs.py
│   │   │   └── chatbot.py
│   │   ├── chunking.py
│   │   ├── dedup.py
│   │   └── acl_resolver.py
│   ├── tooling/
│   │   ├── builtin/                         40 tools Tier 1 sub-carpetizadas por dominio funcional (+ 10 sub-tools *_local) — decisión #77
│   │   │   ├── search/                      tavily, exa, brave, jina
│   │   │   ├── web/                         firecrawl, fetch, playwright_browser
│   │   │   ├── documents/                   markitdown, mineru_ocr, template_render, pdf_generate, docx_generate, pptx_generate, **word_local, powerpoint_local** (Win COM o python-docx/pptx fallback)
│   │   │   ├── productivity/                google_workspace (Gmail+Calendar+Docs+Sheets+Drive+Forms), ms365, notion, linear, **outlook_local, outlook_calendar_local** (Win COM)
│   │   │   ├── meetings/                    teams, zoom
│   │   │   ├── crm/                         hubspot, salesforce, apollo
│   │   │   ├── communication/               slack, telegram_tool, whatsapp_tool, mailchimp
│   │   │   ├── finance/                     excel, power_bi, quickbooks, plaid
│   │   │   ├── desktop/                     computer_use (+ skill_learning.py), file_system
│   │   │   ├── code/                        e2b_sandbox, kanban, delegate, clarify
│   │   │   ├── research/                    arxiv, openalex
│   │   │   ├── people/                      bamboohr, zendesk
│   │   │   ├── personalization/             writing_style
│   │   │   ├── design/                      [NUEVO] excalidraw_architect, mermaid (figma + photopea como MCPs externos)
│   │   │   ├── engineering/                 [NUEVO] blender, jupytercad, **autocad_local, solidworks_local** (Win COM)
│   │   │   ├── media/                       [NUEVO] fal_media, comfyui, suno_music, davinci_resolve, imagen_google, dalle_unified
│   │   │   └── analytics/                   [NUEVO] powerbi, csvglow, snowflake, clickhouse, bigquery, tableau, **powerbi_file_reader (lee .pbix), tableau_file_reader (lee .twbx/.hyper)** (cross-platform)
│   │   ├── tool_registry.py                 catálogo + tool discovery progresivo
│   │   ├── tool_schema_loader.py            schema lazy-load (Tier 1/2/3)
│   │   ├── parallel_dispatcher.py           asyncio.gather de tool_calls
│   │   └── local_app_detector.py            [NUEVO ~80 LOC] detecta apps locales instaladas (Win registry + macOS /Applications), gating-out automático para *_local.py si no están
│   ├── memory/
│   │   ├── frozen_snapshot.py               MEMORY.md+USER.md+SOUL.md leídos 1 vez
│   │   ├── context_compressor.py            13 secciones de Hermes
│   │   └── fts_search.py                    SQLite FTS5 (COPY-HERMES de session_search_tool.py — decisión #51). NO Postgres tsvector.
│   ├── observability/         [NUEVO §12.2]
│   │   ├── metrics.py                       Prometheus counters/histograms/gauges
│   │   ├── dashboard.py                     vista web para inspección de metadata + analytics
│   │   └── health_monitor.py                [decisión #81 fix CQS] ping cada 30s, mutación de tool_health table; ToolRegistry solo LEE
│   ├── intelligence/          [NUEVO — decisiones #96-99]
│   │   ├── self_correction.py               #96 patrón generate→critique→revise (~200 LOC)
│   │   ├── cove_verifier.py                 #97 Chain-of-Verification, -40-60% alucinaciones (~300 LOC)
│   │   ├── confidence_scorer.py             #98 scoring + abstención si <0.5 (~150 LOC)
│   │   └── fewshot_retriever.py             #99 retrieval de ejemplos aprobados (~150 LOC)
│   ├── triggers/              [NUEVO — decisiones #102, #109]
│   │   ├── event_listener.py                #102 webhooks Gmail/Slack/CRM/metric/calendar (~500 LOC)
│   │   └── webhook_handler.py               #109 endpoint /api/webhooks/<source> con HMAC (~300 LOC, subset de #102)
│   ├── auth/
│   │   ├── oauth_manager.py                 Fernet-encrypted tokens
│   │   ├── token_auth.py                    API tokens HMAC
│   │   ├── device_token.py                  iOS/Android/web
│   │   └── capability_tokens.py             [#107 NUEVO ~300 LOC] tokens efímeros revocables por sesión, scope/TTL/rate-limit per-token
│   ├── governance/            [referenciado en decisiones #53, #44, #106, #108 — ahora explícito]
│   │   ├── file_safety.py                   COPY-HERMES — dependencia de file_tools.py
│   │   ├── redact.py                        COPY-HERMES — dependencia de file_tools.py
│   │   ├── path_security.py                 COPY-HERMES — path traversal prevention
│   │   ├── url_safety.py                    COPY-HERMES — URL validation
│   │   ├── website_policy.py                COPY-HERMES — robots.txt respector
│   │   ├── pii_redactor.py                  #33 Presidio opt-in (ES+EN)
│   │   ├── language_router.py               #40 detecta locale del usuario por turno
│   │   ├── version_tracker.py               #35 watcher fs sobre config/, escribe prompt_versions
│   │   ├── quota_manager.py                 #29 (base COPY-HERMES de budget_config.py)
│   │   ├── forget_user.py                   #31 right-to-be-forgotten, DELETE cascada, solo admin
│   │   ├── prompt_injection_detector.py     [#106 NUEVO ~200 LOC] cuarentena de inputs con patrones de inyección
│   │   └── anomaly_detector.py              [#108 NUEVO ~250 LOC] baseline + detección de desviaciones
│   ├── dreaming/             [NUEVO]
│   │   ├── scheduler.py                     APScheduler con cron + idle trigger
│   │   ├── phases.py                        orquesta las 4 fases en orden
│   │   ├── tasks/
│   │   │   ├── memory_consolidation.py
│   │   │   ├── skill_curator.py
│   │   │   ├── config_refresher.py
│   │   │   ├── index_maintenance.py
│   │   │   ├── learned_skill_revalidation.py
│   │   │   └── scheduled_reports.py         [#110 NUEVO ~150 LOC] informes que se generan solos según cron del usuario
│   │   └── reporter.py                      genera reporte breve
│   └── mcp/                  [NUEVO]
│       ├── process_supervisor.py            gestiona ~15 procesos STDIO de MCPs externos Tier 2 (~150 LOC)
│       ├── healthcheck.py                   ping MCPs cada N segundos
│       └── admin_cli.py                     `vigilador-admin mcp <list|restart|stop|start|logs> <name>`
├── domain/                                  [EXISTENTE — se amplía]
│   ├── system_base.py                       SystemBase + BranchOverlay (intactos)
│   ├── domain_profile.py     [NUEVO]        DomainProfile(BranchOverlay) — para playbooks
│   ├── agent_role.py         [NUEVO]        AgentRole declarativo (id, prompt, allowed_tools)
│   ├── soul.py               [NUEVO]        EnterpriseSoul cargado de config/soul.md
│   └── ports/
│       ├── channel_adapter.py [NUEVO]
│       ├── ingestion_connector.py [NUEVO]
│       └── vector_index.py                  [EXISTENTE — se extiende]
├── infra/
│   ├── mcp/                                 [EXISTENTE — preservado para 2.0]
│   ├── embeddings/
│   │   ├── gemini_gateway.py                [EXISTENTE]
│   │   └── turbovec_adapter.py [NUEVO]
│   ├── persistence/
│   │   ├── vector_index.py                  [EXISTENTE — pgvector]
│   │   ├── turbovec_index.py [NUEVO]
│   │   ├── ingestion_repository.py [NUEVO]
│   │   └── oauth_repository.py [NUEVO]
│   ├── channels/             [NUEVO]
│   │   ├── sse_adapter.py
│   │   ├── telegram_adapter.py
│   │   └── whatsapp_adapter.py
│   └── llm/
│       └── minimax_client.py                [EXISTENTE — añadir param `model`: M-2.7 | M-2.5]
plugins/                      [NUEVO — fuera de src/]
└── technology-watch/                        empaqueta las 6 ramas como playbook
config/
├── skills/skill_matrix_default.yaml         [EXISTENTE]
├── playbooks/                [NUEVO]
│   ├── technology-watch.yaml
│   ├── decision-debate.yaml
│   ├── market-research.yaml
│   ├── compliance-audit.yaml
│   └── general.yaml
├── soul.md                   [NUEVO]         personalidad del asistente
├── company/                  [NUEVO]         contexto empresarial dividido en 5 archivos
│   ├── identity.md
│   ├── organization.md
│   ├── processes.md
│   ├── systems.md
│   └── policies.md
├── templates/                [NUEVO]         plantillas de documentos versionadas en git
│   ├── informes/             reportes mensuales, KPIs, auditorías (MD)
│   ├── propuestas/           propuestas comerciales, cotizaciones (DOCX)
│   ├── contratos/            laboral, servicios, NDA (DOCX)
│   ├── presentaciones/       pitch inversor, updates trimestrales (PPTX)
│   └── correos/              followups, recordatorios (MD, pasan por writing_style)
└── mcp/                      [NUEVO]
    └── external.yaml         lista de ~15 MCPs externos Tier 2 con command/args/env/log_file
```

### 2.2 Componentes nuevos / refactorizados / preservados

| Categoría | Componente | Acción | Principio |
|---|---|---|---|
| Preservar | `OrchestratorService` ([orchestrator_service.py](src/vigilancia_multiagente/application/orchestration/orchestrator_service.py)) | Sin cambios | Cambios quirúrgicos |
| Preservar | `BranchCoordinator` ([branch_coordinator.py:47](src/vigilancia_multiagente/application/execution/branch_coordinator.py)) | Sin cambios. Playbook `technology-watch` lo invoca | DRY |
| Preservar | `MCPExecutionClient` + cache ([execution_client.py](src/vigilancia_multiagente/infra/mcp/execution_client.py)) | Sin cambios para 2.0. v3.0 NO depende de MCPs externos | DIP |
| Preservar | `PromptComposer`, `ContractLoader` | Sin cambios | DRY |
| Preservar | `BaseBranchAgent` ([base.py](src/vigilancia_multiagente/application/agents/base.py)) | Sin cambios | OCP |
| Extender | `BranchOverlay` ([system_base.py:28](src/vigilancia_multiagente/domain/system_base.py)) | Subclase `DomainProfile` añade `connectors_required`, `acl_default_scopes`, `playbook_id` | OCP, LSP |
| Extender | port `VectorIndex` | Nuevo backend `TurboVecIndex` además de pgvector | DIP, OCP |
| Extender | `MiniMaxClient` | Parámetro `model` (default M-2.7, opcional M-2.5) | OCP |
| Nuevo | Todo `enterprise/*` | Subsistema 3.0 | SRP |
| Nuevo | `plugins/technology-watch/` | Encapsular 2.0 como playbook | OCP, DRY |

### 2.3 Diagrama de flujo

```
Usuario por canal (Web/SSE | Telegram | WhatsApp)
    ↓
ChannelGateway (api/channels/gateway.py)
    ↓
OrchestratorService (router de intent → playbook)
    ↓
ComplexityClassifier (1 llamada MiniMax M-2.7 corta, sin límite de llamadas globales)
    ↓ SIMPLE | MODERADA | COMPLEJA
PlaybookRunner (enterprise/orchestration/playbook_runner.py)
    ↓
    ├─→ technology-watch  → BranchCoordinator 2.0 → 6 ramas paralelas
    ├─→ decision-debate   → DebateCoordinator → CrewAI Crew (N agentes según complejidad + moderador)
    ├─→ market-research   → CrewAI Crew
    ├─→ compliance-audit  → CrewAI Crew
    └─→ general           → 1 agente generalista con tool discovery progresivo
    ↓ (cada agente, recursivo: cualquier agente puede spawnear sub-agentes)
ToolRegistry.discover(role, intent)  ← descubrimiento progresivo, NO carga todo
    ↓
ParallelToolDispatcher → 20 builtin tools + TurboVec query
    ↓
ContextCompressor (auto cuando tokens > 70% context window)
    ↓
Response → ChannelAdapter → Usuario
```

---

## 3. Orquestador complejidad-aware con sub-agentes recursivos

### 3.1 ComplexityClassifier

`enterprise/orchestration/complexity_classifier.py`. Un step que precede a `PlaybookRunner`. Una llamada MiniMax M-2.7 con prompt corto. Devuelve `Complexity = SIMPLE | MODERADA | COMPLEJA` y `suggested_playbook`.

```python
class Complexity(StrEnum):
    SIMPLE = "simple"        # 1 agente
    MODERADA = "moderada"    # 2-3 agentes
    COMPLEJA = "compleja"    # 4-6 agentes

@dataclass(frozen=True)
class ClassificationResult:
    complexity: Complexity
    suggested_playbook: str
    rationale: str
```

Heurística del prompt: el LLM evalúa (i) número de dominios involucrados, (ii) horizonte temporal, (iii) reversibilidad de la decisión, (iv) necesidad de evidencia externa. **Log de la decisión** para POLA (auditable).

### 3.2 Sub-agentes recursivos

**Cualquier agente puede invocar la tool `spawn_subagent(role, task, allowed_tools)`**. No hay límite global de llamadas (decisión del usuario). Guardrails (alineados con principio 4 — manejo de errores estricto):

| Guardrail | Valor | Razón |
|---|---|---|
| Depth máxima por sesión | 5 | Evita stacks infinitos sin frenar profundidad legítima |
| Budget de tokens por sesión | configurable, default 500k | Acotamiento por presupuesto, no por número arbitrario |
| Heartbeat por sub-agente | 30s sin actividad → log warning | Detección de hangs |
| Tabla `subagents` persiste tree | parent_id, depth, status, allowed_tools | Orphan recovery en restart |

**Por qué no "sin límite total"**: la constitución pide error handling estricto y simplicidad. Cero límite es trampa: la trazabilidad muere. Lo que el usuario quiere — y esto interpreta su intención — es **no poner un número arbitrario pequeño** (como el `MAX_REPLANS_PER_SESSION = 5` actual de `branch_coordinator.py:44`). Sustituyo "máximo N llamadas" por "máximo profundidad + budget token + heartbeat". Eso da escalabilidad real sin permitir runaway.

### 3.3 SubagentRegistry

`enterprise/orchestration/subagent_registry.py`. Tabla:

```sql
CREATE TABLE subagents (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  parent_id UUID REFERENCES subagents(id),
  depth INT NOT NULL CHECK (depth <= 5),
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  allowed_tools TEXT[] NOT NULL,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  last_heartbeat_at TIMESTAMPTZ
);
CREATE INDEX ON subagents (session_id);
CREATE INDEX ON subagents (parent_id);
```

---

## 4. Catálogo de tools internalizadas (origen explícito por tool)

Decisión: **no consumir MCPs como `STDIO`/`HTTP` externos**. Cada tool se integra como módulo Python bajo `enterprise/tooling/builtin/*.py`. Beneficios: una convención, un deployment, debug directo, cero dependencias `npx`/`uvx`/`node`.

### 4.1 Tres estrategias de origen

Cada tool se origina de una de tres fuentes — esto es **explícito** para cada entrada de la tabla:

| Estrategia | Significado | Esfuerzo |
|---|---|---|
| **COPY-HERMES** | Copiar el archivo Python de `documentation/hermes agent/hermes-agent/tools/<archivo>.py` y adaptar imports/namespaces al paquete `enterprise/tooling/builtin/`. Hermes ya tiene tools en Python listas. | Bajo (1-2 días por tool) |
| **CLONE-UPSTREAM** | Clonar el repo upstream del MCP/SDK (no está en `documentation/`), traducir a Python si es JS/TS, encapsular en clase `BuiltinTool`. | Medio (3-7 días por tool) |
| **WRAP-SDK** | Usar el SDK oficial Python del proveedor desde PyPI (sin clonar repos). Solo escribir la clase `BuiltinTool` que envuelve el SDK. | Bajo (1-3 días por tool) |

### 4.2 Catálogo de 41 tools sub-carpetizadas por dominio funcional

Estructura modularizada en `enterprise/tooling/builtin/`:

```
enterprise/tooling/builtin/
├── search/                              [búsqueda web e investigación]
├── web/                                 [navegación, scraping, browser]
├── documents/                           [conversión, OCR]
├── productivity/                        [Gmail, Calendar, Outlook, Notion]
├── crm/                                 [HubSpot, Salesforce, Apollo]
├── communication/                       [Slack, Telegram, WhatsApp, Mailchimp]
├── finance/                             [Excel, Power BI, QuickBooks, Plaid]
├── desktop/                             [computer use + skill learning]
├── code/                                [e2b sandbox, kanban, delegate, clarify]
├── research/                            [arxiv, openalex]
└── people/                              [BambooHR, Zendesk]
```

**Tabla completa de 35 tools**:

#### `search/` (4 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `tavily.py` | PyPI `tavily-python` | WRAP-SDK | `tavily_search`, `tavily_extract` |
| `exa.py` | PyPI `exa-py` | WRAP-SDK | `web_search`, `web_fetch`, `advanced_search` |
| `brave.py` | upstream `brave-search-mcp-server` (TS) | CLONE-UPSTREAM | `web_search`, `news_search` |
| `jina.py` | API REST `r.jina.ai` / `s.jina.ai` | WRAP-SDK | `read_url`, `search_web`, `guess_datetime_url` |

#### `web/` (3 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `firecrawl.py` | PyPI `firecrawl-py` | WRAP-SDK | `scrape`, `crawl`, `search`, `map`, `extract` |
| `fetch.py` | PyPI `mcp_server_fetch` / `httpx` | WRAP-SDK | `fetch` (HTML estático) |
| `playwright_browser.py` | Hermes `tools/browser_tool.py` + `browser_cdp_tool.py` + `browser_dialog_tool.py` + `browser_supervisor.py` | COPY-HERMES | `navigate`, `snapshot`, `screenshot`, `click`, `type`, `eval`, `network_requests`, dialog supervisor |

#### `documents/` (6 tools: 2 lectura + 4 generación)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `markitdown.py` | PyPI `markitdown` (Microsoft) | WRAP-SDK | `convert_to_markdown` (PDF/DOCX/XLSX/HTML/CSV/etc.) |
| `mineru_ocr.py` | upstream `opendatalab/MinerU` (Python) + REST | CLONE-UPSTREAM | `pdf_to_markdown` (109 idiomas, fórmulas, tablas) |
| `template_render.py` | PyPI `jinja2` (sobre MD/HTML) + `docxtpl` (sobre DOCX) | WRAP-SDK | `template_list` (lista templates disponibles), `template_render(template_id, variables)`, `template_validate(template_id, variables)` |
| `pdf_generate.py` | PyPI `weasyprint` (Markdown+CSS→PDF) + `reportlab` (programático) | WRAP-SDK | `markdown_to_pdf(md, style)`, `compose_pdf(sections)`, `pdf_merge(paths)`, `pdf_split(path, ranges)` |
| `docx_generate.py` | PyPI `python-docx` + `docxtpl` | WRAP-SDK | `docx_create(content, style)`, `docx_from_template(template_id, variables)`, `docx_insert_table(path, data)`, `docx_insert_image(path, image)` |
| `pptx_generate.py` | PyPI `python-pptx` | WRAP-SDK | `pptx_from_template(template_id, slides)`, `pptx_add_slide(path, layout, content)`, `pptx_export_pdf(path)` |

#### `productivity/` (4 tools — `google_workspace` ampliado con Forms)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `google_workspace.py` | PyPI `google-api-python-client` + `google-auth` (extensión Forms API) | WRAP-SDK | `gmail_send`, `gmail_search`, `calendar_create_event`, `docs_read`, `sheets_read`, `sheets_append`, `drive_search`, `drive_download`, **`forms_create(title, description)`, `forms_add_question(form_id, question, type, options)`, `forms_list_responses(form_id)`, `forms_export_to_sheet(form_id, sheet_id)`, `forms_get_summary(form_id)`** |
| `ms365.py` | PyPI `msgraph-sdk` | WRAP-SDK | `outlook_send`, `outlook_search`, `teams_message`, `onedrive_search`, `onenote_read` |
| `notion.py` | PyPI `notion-client` | WRAP-SDK | `page_create`, `page_read`, `database_query`, `database_update`, `search` |
| `linear.py` | PyPI `gql` + GraphQL Linear | WRAP-SDK | `issue_create`, `issue_update`, `issue_search`, `project_list` |

#### `meetings/` (2 tools — nueva sub-carpeta)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `teams.py` | PyPI `msgraph-sdk` (extensión sobre `ms365` para Online Meetings + Transcripts API) | WRAP-SDK | `meeting_create(subject, start, end, attendees)`, `meeting_list(date_range)`, `meeting_get_transcript(meeting_id)`, `meeting_get_recording(meeting_id)`, `meeting_get_attendance(meeting_id)`, `meeting_cancel(meeting_id)` |
| `zoom.py` | PyPI `pyzoom` o REST API Zoom v2 directo | WRAP-SDK | `meeting_create(topic, start_time, duration, attendees)`, `meeting_list(user_id, type)`, `meeting_get_recording(meeting_id)`, `meeting_get_transcript(meeting_id)` (Zoom AI Companion), `webinar_create`, `webinar_list_registrants` |

#### `crm/` (3 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `hubspot.py` | PyPI `hubspot-api-client` | WRAP-SDK | `contacts_search`, `contacts_create`, `deals_list`, `deals_update`, `engagements_log` |
| `salesforce.py` | PyPI `simple-salesforce` | WRAP-SDK | `query_soql`, `record_create`, `record_update`, `record_delete`, `bulk_query` |
| `apollo.py` | API REST Apollo.io | WRAP-SDK | `people_search`, `enrich_person`, `enrich_organization`, `email_finder` |

#### `communication/` (4 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `slack.py` | PyPI `slack-sdk` | WRAP-SDK | `post_message`, `search_messages`, `list_channels`, `get_thread` |
| `telegram_tool.py` | PyPI `python-telegram-bot` | WRAP-SDK | `send_message`, `send_file`, `get_chat_history` |
| `whatsapp_tool.py` | WhatsApp Cloud API (Meta) REST | WRAP-SDK | `send_message`, `send_template`, `get_media` |
| `mailchimp.py` | PyPI `mailchimp-marketing` | WRAP-SDK | `list_audiences`, `campaign_create`, `campaign_send`, `audience_add_member` |

#### `finance/` (4 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `excel.py` | PyPI `openpyxl` + `pandas` | WRAP-SDK | `read_sheet`, `write_sheet`, `formula_eval`, `pivot_table`, `chart_render` |
| `power_bi.py` | PyPI `azure-identity` + Power BI REST API | WRAP-SDK | `list_workspaces`, `list_reports`, `run_dax_query`, `refresh_dataset`, `export_pdf` |
| `quickbooks.py` | PyPI `python-quickbooks` (OAuth) | WRAP-SDK | `invoice_create`, `invoice_list`, `customer_search`, `account_balance`, `report_pl` |
| `plaid.py` | PyPI `plaid-python` | WRAP-SDK | `accounts_get`, `transactions_get`, `auth_get`, `identity_get` |

#### `desktop/` (2 tools — Computer Use especial, ver §4.4)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `computer_use.py` | Hermes `tools/computer_use_tool.py` + `tools/computer_use/vision_routing.py` | COPY-HERMES + extensión | 13 acciones nativas + **skill learning** (ver §4.4) |
| `file_system.py` | Hermes `tools/file_tools.py` + `file_operations.py` + `file_state.py` + `binary_extensions.py` | COPY-HERMES | `read_file` (paginación), `write_file`, `patch` (replace/insert/delete con fuzzy_match), `search_files` (ripgrep + find), `list_dir`, `stat_file`, `mkdir`, `move`, `copy`, `delete` (con confirmación) |

#### `personalization/` (1 tool nueva)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `writing_style.py` | Nuevo (no existe en Hermes/OpenClaw) | NUEVO | `learn_style_from_corpus(source)`, `infer_style_profile()`, `compose_with_style(intent, recipient)`, `update_profile_from_feedback(approved_text, original_text)` |

#### `code/` (4 tools — Hermes nativas)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `e2b_sandbox.py` | PyPI `e2b` SDK | WRAP-SDK | `execute_code`, `install_pip`, `read_file`, `write_file` |
| `kanban.py` | Hermes `tools/kanban_tools.py` | COPY-HERMES | `kanban_show`, `kanban_list`, `kanban_create`, `kanban_complete`, `kanban_block`, `kanban_unblock`, `kanban_comment`, `kanban_link`, `kanban_heartbeat` |
| `delegate.py` | Hermes `tools/delegate_tool.py` | COPY-HERMES | `delegate_task` (spawn subagente con toolset restringido) |
| `clarify.py` | Hermes `tools/clarify_tool.py` + `tools/clarify_gateway.py` | COPY-HERMES | `clarify` (pregunta al usuario con opciones ≤4 o abierta) |

#### `research/` (2 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `arxiv.py` | PyPI `arxiv` | WRAP-SDK | `search_papers`, `download_pdf`, `read_abstract` |
| `openalex.py` | PyPI `pyalex` | WRAP-SDK | `search_works`, `get_citations`, `analyze_trends`, `get_author` |

#### `people/` (2 tools)
| Builtin | Origen | Estrategia | Tools expuestas |
|---|---|---|---|
| `bamboohr.py` | API REST BambooHR | WRAP-SDK | `employee_list`, `employee_get`, `time_off_request`, `directory_search` |
| `zendesk.py` | PyPI `zenpy` | WRAP-SDK | `ticket_create`, `ticket_update`, `ticket_search`, `user_create`, `macro_apply` |

**Total: 43 tools en 13 sub-carpetas (dominios funcionales)**: search (4) + web (3) + documents (6: 2 lectura + 4 generación) + productivity (4: google_workspace incluye Forms) + meetings (2) + crm (3) + communication (4) + finance (4) + desktop (2) + code (4) + research (2) + people (2) + personalization (1) = **43**.

**Notas sobre `documentation/`** (verificado leyendo el árbol):
- Solo Hermes (`documentation/hermes agent/hermes-agent/`) y OpenClaw (`documentation/openclaw/openclaw/`) están como repos completos con código.
- Hermes aporta 6 tools COPY-HERMES directas: `playwright_browser` (browser_*.py), `computer_use` (computer_use_tool.py + vision_routing.py), `kanban` (kanban_tools.py), `delegate` (delegate_tool.py), `clarify` (clarify_tool.py + clarify_gateway.py).
- OpenClaw sirve solo como referencia de diseño (TS, no se traduce) para computer-use hard-blocks y vision routing.
- Las demás carpetas `documentation/<mcp>/` solo tienen READMEs.

### 4.3 Convención de cada módulo builtin

Cada `enterprise/tooling/builtin/<name>.py` expone una clase que cumple un port común:

```python
# domain/ports/builtin_tool.py
class BuiltinTool(Protocol):
    name: str
    domain: str                              # 'search' | 'productivity' | 'crm' | 'desktop' | etc.
    available_tools: list[ToolSchema]        # nombres + schemas JSON
    requires_auth: bool

    async def execute(self, tool_name: str, args: dict) -> ToolResult: ...
    async def healthcheck(self) -> bool: ...
```

`ToolRegistry` (`enterprise/tooling/tool_registry.py`) descubre todas las clases que implementan `BuiltinTool` vía import explícito en `enterprise/tooling/builtin/__init__.py` (Convención sobre Configuración).

### 4.4 Computer Use con **Skill Learning** (tool especial)

Tool base copiada de Hermes (`tools/computer_use_tool.py` + `tools/computer_use/vision_routing.py`). Adaptación a Windows 11:

- Capa de captura/eventos: Hermes usa `pyobjc`/AppleScript → Windows usa `pyautogui` + `pygetwindow` + `screeninfo` + `mss` (screenshot rápido).
- Schema OpenAI function-calling preservado.
- 13 acciones base preservadas: `capture`, `click`, `double_click`, `right_click`, `drag`, `scroll`, `type`, `key`, `set_value`, `wait`, `list_apps`, `focus_app`.
- `vision_routing.py` preservado: enruta capturas a MiniMax M-2.7 con visión o a modelo auxiliar según tamaño/contenido.
- Hard-blocks: ctrl+alt+del, taskkill /f, alt+f4 en apps marcadas como críticas en `config/company/policies.md`.

#### Capacidad de **Skill Learning** (extensión sobre Hermes)

Decisión del usuario: que el agente aprenda a usar sitios y guarde el procedimiento como un skill reutilizable. Inspirado en OpenClaw `skills/` + Hermes `skill_manage`. Esta extensión NO existe en Hermes; se construye encima.

**Arquitectura del skill learning** (`enterprise/tooling/builtin/desktop/skill_learning.py`):

```
1. MODO DEMOSTRACIÓN
   El usuario invoca: "Aprende a auditar el inventario en el ERP X"
   El agente entra en modo grabación:
     - captura screenshot inicial
     - registra cada acción del usuario (clicks, types, navegación)
     - infiere selectores (text/role/accessibility tree)
     - pide clarificaciones cuando hay ambigüedad ("¿esto es siempre así o cambia?")

2. SÍNTESIS
   Al terminar la demo, el agente:
     - resume los pasos en lenguaje natural
     - identifica variables (fechas, IDs, montos)
     - genera el skill como archivo YAML + función Python

3. PERSISTENCIA
   El skill se guarda en config/skills/learned/<skill_name>.yaml
   Estructura:
     id: audit-inventory
     description: "Audita el inventario en el ERP X"
     learned_at: 2026-05-24
     input_schema: {month: string, area_code: string}
     steps:
       - action: focus_app
         target: "ERP X"
       - action: navigate
         url_pattern: "...inventory/{area_code}"
       - action: extract_table
         selector: "table.inventory"
         output_var: rows
       - action: aggregate
         logic: "sum by category"
     output_schema: {summary: object, anomalies: list}

4. EJECUCIÓN AUTÓNOMA
   El agente puede invocar el skill aprendido como una tool más:
     execute_learned_skill("audit-inventory", {month: "2026-05", area_code: "BOG"})
   El agente lo ejecuta paso a paso, valida outputs, reporta diferencias.

5. AUTO-CORRECCIÓN
   Si un selector falla (ej. el sitio cambió), el agente:
     - entra en modo recovery (vision + accessibility tree)
     - intenta variaciones
     - si tiene éxito, actualiza el skill y registra cambio
     - si falla persistente, marca skill como "stale" y notifica al usuario
```

**Por qué esto es especial** (alineado con la constitución):
- **DRY**: el procedimiento se aprende una vez, se reutiliza N veces sin re-aprender.
- **OCP**: skills aprendidos extienden el harness sin tocar código del orquestador.
- **POLA**: el agente reporta qué aprendió y en qué confía vs qué inferió.
- **YAGNI controlado**: no se construye un editor visual de skills (eso es exceso). El YAML es editable a mano si el usuario quiere ajustar.

**Casos de uso típicos** del usuario:
- "Aprende a generar el informe de inventario mensual" → skill ejecutable cada mes.
- "Aprende a auditar accesos al ERP" → skill que se corre nocturno (vía Dreaming, §10).
- "Aprende a publicar oferta en LinkedIn" → skill reutilizable para nuevas vacantes.

**Guardrails**:
- Skills aprendidos requieren confirmación del usuario en primera ejecución autónoma.
- Cualquier skill que toque CRM, finanzas o envío externo requiere `@audit` decorator (cuando se implemente el audit log; mientras tanto, log estructurado obligatorio).
- Skills con depth > 3 acciones se ejecutan dentro del `SubagentRegistry` para trazabilidad.

OpenClaw (`extensions/codex/src/app-server/computer-use.ts`, 683 líneas TS) sirve como **referencia** para diseño de hard-blocks y vision routing, pero NO se traduce: el código base es Hermes.

### 4.5 Tool discovery progresivo (3 tiers)

Inspiración: Hermes `skills_list` → `skill_view` → `skill_manage`. Aplicado a tools para cumplir **ISP**.

| Tier | Qué expone | Tokens | Cuándo |
|---|---|---|---|
| **Tier 1: listing** | Nombres + 1-line description de tools del dominio del agente | ~50 | Inyectado al spawnear el agente |
| **Tier 2: schema** | JSON Schema completo del tool que el agente pide | ~200-500 por tool | Tool `tool_describe(tool_name)` invocada bajo demanda |
| **Tier 3: execution** | Ejecución con args | — | Tool calling estándar |

Reducción típica de tokens en prompt: 60-80%. Implementación en `enterprise/tooling/tool_schema_loader.py`.

### 4.6 Sistema de Templates (módulo crítico para empresarios)

Decisión del usuario: módulo dedicado para informes, propuestas, contratos, presentaciones, integrado con Writing Style Learning para que los documentos generados suenen al usuario.

**Arquitectura** (`enterprise/tooling/builtin/documents/templates/`):

```
config/templates/                          ← plantillas del usuario (versionadas en git)
├── informes/
│   ├── ventas_mensual.md                  Jinja2-MD: {{ mes }}, {{ pipeline_total }}, {{ tabla_deals }}
│   ├── kpi_trimestral.md
│   └── auditoria_inventario.md
├── propuestas/
│   ├── propuesta_comercial.docx           DOCX con placeholders {{cliente.nombre}}, {{precio_total}}
│   └── cotizacion.docx
├── contratos/
│   ├── contrato_laboral.docx
│   ├── contrato_servicios.docx
│   └── nda.docx
├── presentaciones/
│   ├── pitch_inversor.pptx                python-pptx layouts + placeholders
│   └── update_quarterly.pptx
└── correos/                               (estos sí usan writing_style profile)
    ├── seguimiento_lead.md
    ├── propuesta_followup.md
    └── recordatorio_cobro.md
```

**Flujo de generación**:

```
1. INSTANCIAR
   Tool template_render(template_id, variables) busca en config/templates/
   Carga la plantilla (MD/DOCX/PPTX)

2. VALIDAR
   Compara variables requeridas (extraídas con Jinja2 AST) vs variables provistas
   Si faltan: clarify_tool pide al usuario

3. RENDERIZAR
   MD: jinja2.Template(md).render(variables) → MD final
   DOCX: docxtpl.DocxTemplate(path).render(variables) → DOCX final
   PPTX: python-pptx itera slides y reemplaza placeholders

4. POST-PROCESO (opcional)
   Si tipo informe Y writing_style está activo: pasar texto por compose_with_style para que suene al usuario
   Si tipo PDF requerido: pdf_generate.markdown_to_pdf(md_final, style=corporate_style)

5. ENTREGAR
   Guarda en ~/.vigilador/outputs/<fecha>/<doc>.{pdf,docx,pptx}
   Notifica al usuario por canal preferido (download link o adjunto)
```

**Integración con otros módulos**:
- **TurboVec**: tool `template_render` puede recibir `data_query` que ejecuta búsqueda semántica en documentos indexados y rellena `{{contexto_cliente}}` con extracts relevantes.
- **Writing Style**: correos generados con templates pasan por `compose_with_style` automáticamente.
- **Computer Use + Skill Learning**: si el usuario tiene un proceso manual de generar informes en una app del ERP, el skill aprendido se invoca después de generar el doc (ej. uploader automático).
- **COMPANY policies**: contratos extraen automáticamente cláusulas estándar de `config/company/policies.md` (ej. confidencialidad, jurisdicción).
- **Dreaming proactivo**: el ciclo nocturno pre-genera informes recurrentes (ej. reporte de ventas mensual el primer día del mes) y los deja en drafts para revisión.

**Convención sobre Configuración**:
- Templates en `config/templates/<categoria>/<nombre>.<ext>` se descubren automáticamente.
- Sin registro adicional. La estructura es el catálogo.

**Por qué cumple la constitución**:
- **SRP**: cada tool genera UN formato (pdf/docx/pptx). `template_render` solo renderiza, no genera output final.
- **DRY**: variables comunes (`{{empresa.nombre}}`, `{{fecha_hoy}}`) se inyectan globalmente desde COMPANY/identity.md sin repetir.
- **OCP**: nuevos templates se añaden colocando archivo en `config/templates/`. Cero código.
- **KISS**: 4 tools, 3 formatos. Sin abstraer "DocumentEngine" genérico (eso sería AHA).
- **YAGNI**: no se soporta LaTeX (poca demanda PYME). No editor visual (el template es el editor).

---

## 5. Subsistema de indexación empresarial

### 5.1 TurboVec — integración (no reimplementación)

```python
# infra/persistence/turbovec_index.py
from turbovec import IdMapIndex
from vigilancia_multiagente.domain.ports.vector_index import VectorIndex

class TurboVecIndex(VectorIndex):
    def __init__(self, dim: int = 768, bit_width: int = 4, path: Path | None = None):
        self._idx = IdMapIndex(dim=dim, bit_width=bit_width)
        self._path = path
        if path and path.exists():
            self._idx = IdMapIndex.load(str(path))

    async def add(self, vectors, ids):
        self._idx.add_with_ids(vectors, ids)

    async def search(self, query, k, allowlist=None):
        return self._idx.search(query, k=k, allowlist=allowlist)

    async def persist(self):
        self._idx.write(str(self._path))
```

Coexistencia con pgvector: pgvector → JOINs SQL + metadatos. TurboVec → índice vectorial. Doble write 4 sem, A/B test (recall@10 ≥ 0.92) antes de cortar lectura pgvector. KISS: si recall no llega, se mantiene pgvector como índice principal.

### 5.2 Connectors

| Connector | Auth | Modo sync | Path |
|---|---|---|---|
| `google_drive.py` | OAuth 2.0 PKCE | Delta query `pageToken` cada 15 min | `enterprise/ingestion/connectors/google_drive.py` |
| `onedrive.py` | MS Graph OAuth | Delta endpoint | `enterprise/ingestion/connectors/onedrive.py` |
| `whatsapp.py` | Cloud API + upload manual zip | Webhook + upload | `enterprise/ingestion/connectors/whatsapp.py` |
| `local_fs.py` | N/A | watchdog | `enterprise/ingestion/connectors/local_fs.py` |
| `chatbot.py` | API key | Sync nocturno | `enterprise/ingestion/connectors/chatbot.py` |

### 5.3 Pipeline

```
fetch (connector)
  → MIME detect → markitdown (PyPI directo, no MCP externo)
  → chunk semántico (~512 tok, overlap 64)
  → dedupe SimHash 64-bit + Hamming ≤ 3
  → embed (Gemini text-embedding-004)
  → TurboVec.add_with_ids() + pgvector INSERT (doble write)
  → entity_extraction (reusar application/extraction/entity_extractor.py)
  → emit "document_indexed"
```

### 5.4 OAuth (`enterprise/auth/oauth_manager.py`)

Tokens cifrados con Fernet, master key generada al primer arranque en `~/.vigilador/credentials/master.key`. Tabla `oauth_credentials` solo guarda ciphertext.

### 5.5 ACL

Cada chunk lleva `acl_scopes: TEXT[]`. TurboVec usa `allowlist` (filtrado SIMD-level). pgvector usa `WHERE acl_scopes && current_user_scopes` con GIN. El LLM NUNCA recibe chunks fuera de scopes.

### 5.6 Schema SQL (migración nueva)

```sql
CREATE TABLE ingested_documents (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  source TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  mime_type TEXT,
  title TEXT,
  author TEXT,
  acl_scopes TEXT[] NOT NULL,
  metadata JSONB NOT NULL,
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ,
  UNIQUE(tenant_id, source, source_ref)
);
CREATE INDEX ON ingested_documents USING GIN (acl_scopes);

CREATE TABLE document_chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES ingested_documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  embedding vector(768),
  turbovec_id BIGINT UNIQUE,
  acl_scopes TEXT[] NOT NULL,
  metadata JSONB,
  UNIQUE(document_id, chunk_index)
);
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON document_chunks USING GIN (acl_scopes);

CREATE TABLE oauth_credentials (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  user_id UUID NOT NULL,
  provider TEXT NOT NULL,
  access_token_enc BYTEA NOT NULL,
  refresh_token_enc BYTEA,
  expires_at TIMESTAMPTZ,
  scopes TEXT[],
  UNIQUE(tenant_id, user_id, provider)
);

CREATE TABLE subagents (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  parent_id UUID REFERENCES subagents(id),
  depth INT NOT NULL CHECK (depth <= 5),
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  allowed_tools TEXT[] NOT NULL,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  last_heartbeat_at TIMESTAMPTZ
);
CREATE INDEX ON subagents (session_id);
CREATE INDEX ON subagents (parent_id);
```

(Sin tabla `audit_events` en v3.0 inicial — YAGNI. Se añade cuando haya casos legales/regulatorios que la justifiquen.)

---

## 6. Metodologías de tool calling adoptadas

| Patrón | Origen | Adopción | Implementación |
|---|---|---|---|
| Parallel tool calls | Hermes | Sí | `enterprise/tooling/parallel_dispatcher.py`: `asyncio.gather` sobre tool_calls del LLM (limit=8). |
| Hierarchical delegation recursiva | Hermes (`delegate_task`) | Sí | Tool `spawn_subagent(role, task, allowed_tools)`. Cualquier agente puede invocarla. Depth ≤ 5, persiste en `subagents`. |
| Tool discovery progresivo | Hermes (`skills_list/view/manage`) | Sí | Tiers 1/2/3 descritos en §4.3. |
| Multi-agent debate | Decisión del usuario | Sí | `debate_coordinator.py`: N agentes (3-5) toman posturas, 3 rondas de crítica, moderador sintetiza. Backend CrewAI. **Solo MiniMax M-2.7 + M-2.5 alternados** (no Claude/Gemini). |
| Mixture of Agents (MoA) | Hermes | Sí, opt-in | `mixture_of_agents` tool: 3-4 agentes M-2.7 con temperaturas distintas (0.3, 0.5, 0.7) + agregador M-2.7 (temp=0.2). Diversidad por temperatura, no por proveedor. |
| ReAct loop | Clásico, ya en BaseBranchAgent | Conservar | Reuso. |
| ContextCompressor | Hermes | Sí | Template 13 secciones. Trigger > 70% context window. |
| Frozen-snapshot memory | Hermes | Sí | `MEMORY.md` + `USER.md` + `SOUL.md` leídos una vez en `on_session_start`. Writes a queue, flush en `on_session_end`. |
| Cross-session FTS | Hermes (SQLite FTS5) | **COPY-HERMES directo (SQLite FTS5)** — decisión #51 revierte la primera versión que iba a usar Postgres tsvector | `enterprise/memory/fts_search.py` adopta `tools/session_search_tool.py` de Hermes con 3 modos (DISCOVERY/SCROLL/BROWSE). Postgres sigue para vectores (TurboVec backup) + audit. SQLite **solo** para FTS5 de transcripts. |
| Reactive planning | YA EXISTE en 2.0 | Conservar | [`branch_coordinator.py:258`](src/vigilancia_multiagente/application/execution/branch_coordinator.py). Mantener intacto. |

---

## 7. Combos / Playbooks (CrewAI + YAML)

### 7.1 Schema YAML

```yaml
# config/playbooks/decision-debate.yaml
id: decision-debate
description: "Toma de decisiones empresariales por debate multi-agente con moderador"
backend: crewai
complexity_routing:
  SIMPLE: { num_agents: 2, rounds: 1 }
  MODERADA: { num_agents: 3, rounds: 2 }
  COMPLEJA: { num_agents: 5, rounds: 3 }
agents:
  - id: optimist
    role: "Defensor del cambio propuesto"
    llm: minimax-m-2.7
    domain: business_strategy
    allowed_tools: [tavily_search, firecrawl_scrape, turbovec_query, hubspot_contacts_search]
  - id: pessimist
    role: "Crítico de riesgos y costos"
    llm: minimax-m-2.5
    domain: risk
    allowed_tools: [tavily_search, turbovec_query, excel_pivot_table]
  - id: pragmatist
    role: "Evaluador de viabilidad operativa"
    llm: minimax-m-2.7
    domain: operations
    allowed_tools: [excel_pivot_table, hubspot_deals_list, linear_issue_search]
  - id: moderator
    role: "Sintetizador de la decisión final"
    llm: minimax-m-2.7
    domain: synthesis
    allowed_tools: []
output_schema:
  decision: string
  rationale: string
  dissent_summary: string
  confidence: float
```

### 7.2 Playbooks iniciales (6)

| Playbook | Backend | Agentes | Uso |
|---|---|---|---|
| `technology-watch` | native (BranchCoordinator) | 6 ramas del 2.0 (AVANCES, COMERCIAL, RIESGO, PI_NORMATIVA, COMPETITIVO, OPORTUNIDADES) | Vigilancia tecnológica clásica del 2.0 |
| `deep-research` | native + CrewAI híbrido | 3-6 ramas dinámicas según ComplexityClassifier + moderador final | Patrón Clarify → Plan → Approve → Execute paralelo → Fuse → Report del 2.0, generalizado: el usuario pregunta cualquier cosa (no solo tech) y el harness lanza N ramas de investigación paralelas con MoA o no según complejidad. Reutiliza `BranchCoordinator.execute()` con configuración dinámica de ramas (no fijas como en `technology-watch`). |
| `decision-debate` | CrewAI | 2-5 escalable + moderador | Dilemas empresariales con multi-agent debate |
| `market-research` | CrewAI | researcher + analyst + writer | Investigación de mercado |
| `compliance-audit` | CrewAI | regulator + auditor | Auditoría regulatoria |
| `general` | CrewAI | 1 generalista | Fallback con tool discovery progresivo |

**Deep research como playbook explícito**: el flujo del 2.0 ya está implementado (`OrchestratorService` + `BranchCoordinator`). El playbook `deep-research` simplemente lo invoca con ramas configurables por sesión (no hardcoded como las 6 de `technology-watch`). Esto permite, por ejemplo, "investiga a fondo si conviene abrir sucursal en Bogotá" → ComplexityClassifier elige COMPLEJA → 5 ramas: market_size, regulatory, competitive, operational_costs, talent_availability → ejecutadas en paralelo → fusion + reporte.

---

## 8. Governance y seguridad

### 8.1 SystemBase + DomainProfile + SOUL + COMPANY

Cuatro capas declarativas, cada una con responsabilidad única (SRP):

- `SystemBase` ([domain/system_base.py:10](src/vigilancia_multiagente/domain/system_base.py)) — **sin cambios**. Reglas globales inmutables del harness (safety, output_style, error_handling).
- `BranchOverlay` → subclase `DomainProfile` añade `domain_id`, `connectors_required`, `acl_default_scopes`, `playbook_id` (LSP-compatible: solo extiende).
- **`SOUL.md`** (`config/soul.md`): **personalidad** del asistente por tenant. Ejemplo: *"Hablas español neutro, prefieres bullets, jamás prometes plazos sin consultar"*. Cargado por `frozen_snapshot.py` una vez al inicio de sesión. `PromptComposer` lo prepende al system message.
- **`config/company/` — 5 archivos** [NUEVO en esta iteración]: contexto empresarial dividido por tema para evitar un único archivo largo. Cargados todos por `frozen_snapshot.py` en boot de sesión. `PromptComposer` los concatena en orden tras SOUL.md.

| Archivo | Contenido | Ejemplo |
|---|---|---|
| `config/company/identity.md` | Quiénes somos | Nombre, sector, tamaño, HQ, mercados, misión |
| `config/company/organization.md` | Estructura | Áreas, headcount por área, cargos clave por rol (sin nombres propios para privacidad) |
| `config/company/processes.md` | Procesos y cadencias | Cierre contable, OKR, sprints, onboarding, compras |
| `config/company/systems.md` | Stack de herramientas | CRM, contabilidad, comm, code, docs, BI |
| `config/company/policies.md` | Restricciones y políticas | Manejo de datos cliente, comunicación oficial, plazos, apps críticas (hard-block computer use) |

Ejemplo abreviado de `identity.md`:

```markdown
# Identidad
- Nombre: Acme SAS
- Sector: SaaS B2B (logística)
- Tamaño: 47 empleados
- HQ: Bogotá, Colombia
- Mercados: LATAM (Colombia, México, Chile)
- Misión: digitalizar la última milla en logística regional
```

Ejemplo abreviado de `organization.md`:

```markdown
# Estructura organizacional

## Áreas
- Dirección General — CEO + CFO + COO
- Tecnología — 18 personas (5 backend, 4 frontend, 3 mobile, 3 DevOps, 2 QA, 1 Tech Lead)
- Producto — 4 personas (1 CPO, 2 PMs, 1 designer)
- Ventas — 8 personas (1 VP, 5 AEs, 2 SDRs)
- Marketing — 3 personas
- Operaciones — 6 personas (soporte, finanzas, RRHH)

## Cargos clave (referenciar por rol, no por nombre)
- CEO: decisiones estratégicas, presupuestos > $50M COP
- CFO: aprueba contrataciones y compras > $10M COP
- CPO: roadmap de producto, prioridades trimestrales
- VP Ventas: cuotas y comisiones
```

**Cómo lo usa el LLM**: con `policies.md` activo, el asistente puede *"sugerir que contratar 3 devs senior necesita aprobación de CFO (política > $10M COP)"* sin que el usuario se lo recuerde.

**Separación SOUL vs COMPANY** (SoC):
- `SOUL.md`: **cómo habla** el asistente (tono, formato, restricciones de comunicación).
- `config/company/*.md`: **qué sabe** el asistente sobre la empresa (5 dimensiones independientes).

Todos los archivos viven en `config/`, son editables por el usuario, y se versionan en git (sin secretos — los secretos van a `~/.vigilador/credentials/`).

### 8.2 Auth multi-canal (sin sobreingeniería)

Solo 3 métodos en v3.0 inicial (YAGNI):

| Método | Implementación | Uso |
|---|---|---|
| API tokens HMAC-SHA256 | `token_auth.py` | Acceso programático |
| Password (argon2id) | (reuso si existe; si no, postergar) | Web frontend |
| OAuth (Google/MS) | `oauth_manager.py` | Connectors externos |

Rate limiting con `slowapi`. Device tokens y bootstrap tokens se postergan hasta tener demanda real.

### 8.3 Secrets

`~/.vigilador/credentials/` con Fernet. Master key al primer arranque. Nunca en DB.

### 8.4 ACL por documento

Cubierto en §5.5.

---

## 9. Channel Gateway

| Canal | Estado | Esfuerzo |
|---|---|---|
| Web/SSE | Existe | 0 (reuso) |
| Telegram Bot | Nuevo | ~1 sem |
| WhatsApp Cloud API | Nuevo | ~2-3 sem |

Interface `ChannelAdapter` en `domain/ports/channel_adapter.py`. Implementaciones en `infra/channels/`. `ChannelGateway` en `api/channels/gateway.py` enruta a `OrchestratorService.start_session`.

Tool `send_message(channel, recipient, content)` permite cross-channel reply (recibe Telegram → manda email vía `google_workspace.gmail_send`).

---

## 10. Modo Dreaming — auto-mantenimiento del harness

Decisión del usuario: el harness debe mantenerse solo (consolidar memoria, actualizar skills, refrescar SOUL/COMPANY si cambiaron en disco, podar índices). Inspirado en OpenClaw "Dreaming" (fases biológicas) + Hermes "Curator". Adaptado a la constitución (KISS, YAGNI): un módulo simple con triggers claros, no una réplica biológica.

### 10.1 Arquitectura

`enterprise/dreaming/` (nuevo subpaquete, paralelo a `orchestration/`, `ingestion/`, etc.):

```
enterprise/dreaming/
├── scheduler.py                  APScheduler con cron + idle trigger
├── phases.py                     orquesta tareas en orden
├── tasks/
│   ├── ingestion_sync.py         corre connectors (drive, onedrive, whatsapp, chatbot, local_fs) + pipeline §5.3
│   ├── memory_consolidation.py   mergea snapshots duplicados
│   ├── skill_curator.py          active → stale (30d sin uso) → archived (90d)
│   ├── config_refresher.py       relee SOUL.md, config/company/*.md, config/templates/*, valida cambios
│   ├── index_maintenance.py      vacuum pgvector, persist TurboVec, dedupe chunks
│   ├── learned_skill_revalidation.py  re-ejecuta skills aprendidos críticos
│   └── proactive_preparation.py  email triage, to-do extraction, agenda briefing, news digest (§10.7)
└── reporter.py                   genera reporte breve para el usuario
```

### 10.2 Triggers (decisión usuario: cron nocturno + idle > 10 min)

| Trigger | Ventana | Qué corre |
|---|---|---|
| **Cron nocturno** | 3 AM (configurable en `config/settings.yaml`) | Las 5 tareas completas. ~5-15 min de duración. |
| **Idle > 10 min** | Cuando harness no recibe input por 10+ min | Solo `memory_consolidation` y `config_refresher` (livianos). Detiene apenas llega input nuevo. |

### 10.3 Las 6 tareas de mantenimiento

| Tarea | Qué hace | Frecuencia | Criterio de éxito |
|---|---|---|---|
| **`ingestion_sync`** | Para cada connector activo (google_drive, onedrive, whatsapp, chatbot, local_fs): obtiene cambios desde último sync (delta token / pageToken / mtime / webhook backlog), corre pipeline §5.3 (fetch → markitdown → chunk → dedup → embed → TurboVec+pgvector → extract entities), respeta ACL. | Nocturno + idle | Documentos nuevos del usuario indexados sin intervención. Latencia de aparición en búsqueda < 24h. |
| `memory_consolidation` | Lee `subagents` tree de sesiones cerradas hoy. Mergea snapshots con embeddings ≥ 0.92 cosine similarity. Comprime sesiones >24h al template de 13 secciones de `context_compressor`. | Nocturno + idle | -30% bytes memoria, sin pérdida de info por re-query |
| `skill_curator` | Marca skills sin uso > 30 días → `stale`. Skills > 90 días sin uso → `archived` (movidos a `config/skills/learned/_archived/`). Reactiva si se usan. | Nocturno | Skills activos solo los relevantes |
| `config_refresher` | `mtime check` en `config/soul.md`, `config/company/*.md`, `config/templates/`. Si cambiaron, valida sintaxis, reembedded en frozen snapshot, log de cambios. | Nocturno + idle | LLM ve cambios al iniciar próxima sesión |
| `index_maintenance` | `VACUUM ANALYZE` en `document_chunks`, `subagents`, `oauth_credentials`. `turbovec.persist()`. Dedupe chunks con SimHash colision. | Nocturno | Espacio recuperado, query latency estable |
| `learned_skill_revalidation` | Re-ejecuta skills marcados como `critical` en dry-run. Si selectores fallan, marca skill como `stale` y notifica. | Semanal (domingo 4 AM) | Skills críticos verificados antes de fallar en producción |

**Nota sobre `ingestion_sync` como tarea de Dreaming** (decisión del usuario): la indexación NO corre como cron separado fuera del harness. Vive dentro del ciclo de Dreaming nocturno + se dispara también en idle si hay backlog acumulado (webhooks pendientes, archivos modificados detectados por watchdog). Beneficios:
- **Una sola política de scheduling** (no fragmentación de cron jobs).
- **Reuso del Reporter**: el usuario ve qué se indexó como parte del reporte nocturno.
- **Aprovecha config_refresher**: cuando un connector cambia OAuth/scope, el config_refresher lo detecta antes de que ingestion_sync lo necesite.

### 10.4 Reporter

Tras cada ciclo nocturno, el dreaming escribe un reporte en `~/.vigilador/dream-log/<fecha>.md`:

```markdown
# Dream cycle 2026-05-25 03:14
## Memory consolidation
- 12 snapshots mergados (3 sesiones de 24 May)
- -2.3 MB liberados
## Skill curator
- 2 skills marcados stale: weekly-report-generator, slack-summary-old
- 0 archivados
## Config refresher
- COMPANY/organization.md cambió: +2 personas en Tech
- Re-embedded
## Index maintenance
- pgvector vacuum: -4.7 MB
- turbovec persisted
## Skill revalidation (no aplica hoy)
## Status: HEALTHY
```

Si el usuario tiene Telegram activo, recibe un mensaje resumen al despertar (opcional, configurable en `config/settings.yaml`).

### 10.5 Guardrails (manejo de errores estricto)

- Cada tarea es **idempotente**: si falla a la mitad, reintento es seguro.
- Cada tarea tiene **timeout** (5 min default por tarea, 30 min global por ciclo).
- Si una tarea falla, las demás siguen. Reporter incluye la falla con stack trace.
- El ciclo idle se **cancela inmediatamente** si llega input del usuario (verifica cada 5s).
- NO modifica datos del usuario (documentos indexados, OAuth tokens). Solo metadata, índices, snapshots.

### 10.6 Writing Style Learning (módulo `personalization/`)

Decisión del usuario: el harness aprende el estilo de escritura personal y lo aplica al redactar correos.

**Arquitectura** (`enterprise/tooling/builtin/personalization/writing_style.py`):

```
1. CORPUS DE ENTRENAMIENTO
   Fuentes:
   - Correos enviados (Gmail/Outlook vía productivity tools)
   - Mensajes propios en Telegram/WhatsApp (filtro: from=user)
   - Documentos escritos por el usuario (filtro de metadata.author)
   El corpus se construye al activar el módulo y se actualiza nocturno (Dreaming).

2. INFERENCIA DE STYLE PROFILE
   Análisis (sin LLM, heurístico, barato):
   - Longitud media de oraciones, de párrafos
   - Vocativos típicos ("Hola X", "Buenos días X", "X,")
   - Despedidas típicas ("Saludos", "Atentamente", "Un abrazo")
   - Uso de emojis, signos de exclamación, mayúsculas enfáticas
   - Formalidad (Tú/Usted, tono directivo vs sugerente)
   - Vocabulario técnico vs llano (TF-IDF contra corpus genérico)
   - Firmas habituales

   Output: archivo `~/.vigilador/personalization/<user_id>/style_profile.yaml`

3. APLICACIÓN
   Tool `compose_with_style(intent, recipient, context)` que:
   - Lee style_profile.yaml
   - Inyecta instrucciones de estilo concretas en el prompt al LLM
   - Genera borrador del correo
   - Retorna texto para revisión

4. APRENDIZAJE INCREMENTAL
   Cuando el usuario edita un borrador, `update_profile_from_feedback(approved_text, original_text)`:
   - Calcula diff
   - Actualiza heurísticas (longitud, vocativos, etc.)
   - Logs cambios para audit
```

**Storage** (separado de COMPANY/SOUL por ser per-user, no per-tenant):
- `~/.vigilador/personalization/<user_id>/style_profile.yaml`
- `~/.vigilador/personalization/<user_id>/corpus_index/` (TurboVec index de ejemplos)

**Privacidad**: el corpus nunca sale del dispositivo. style_profile.yaml es portable, el usuario puede compartirlo o borrarlo.

### 10.7 Dreaming proactivo (extensión)

Decisión del usuario: el Dreaming no solo mantiene, también prepara. Tarea adicional al ciclo nocturno:

**Tarea `proactive_preparation`** (`enterprise/dreaming/tasks/proactive_preparation.py`):

| Sub-tarea | Qué hace | Output |
|---|---|---|
| **Email triage** | Lee inbox nuevos desde último ciclo (Gmail/Outlook). Clasifica: requiere respuesta / informativo / spam-like. Para los que requieren respuesta, genera borrador usando `writing_style.compose_with_style`. | Carpeta `[VIGILADOR-DRAFTS]/` en Gmail/Outlook con borradores etiquetados |
| **To-do extraction** | Escanea inbox + Slack + Telegram últimas 24h. Extrae con LLM: tareas mencionadas, compromisos asumidos por el usuario, deadlines mencionados. | Crea entradas en Linear con tag `auto-extracted` y fecha sugerida |
| **Agenda briefing** | Lee Calendar del día siguiente. Para cada reunión: busca contexto en documentos indexados (TurboVec), historial de hilos, decisiones previas. | Documento `~/.vigilador/briefings/<fecha>.md` con un resumen por reunión |
| **News digest** | Si el usuario activó (en `config/settings.yaml`), corre `deep-research` playbook con preguntas predefinidas: "novedades en mi sector hoy", "competidores que tomaron acción". | Mensaje resumen al canal preferido (Telegram default) al despertar |

**Guardrails específicos**:
- Los borradores NUNCA se envían automáticamente. Solo quedan en carpeta drafts para revisión.
- Las tareas extraídas se marcan como `requires_confirmation` hasta que el usuario las apruebe.
- News digest solo si el usuario opta-in (off por default).

### 10.8 Por qué cumple la constitución

- **SRP**: cada tarea hace una cosa. `memory_consolidation` no hace email triage.
- **KISS**: triggers explícitos, sin estados emergentes complejos.
- **YAGNI**: news digest opt-in (no se construye si nadie lo activa).
- **POLA**: log explícito de qué hizo y qué no. Borradores etiquetados, no enviados.
- **CQS**: tareas son commands (mutan estado externo: drafts, Linear) — el reporter es query separado.
- **Manejo de errores estricto**: cada sub-tarea con timeout; si Gmail/Linear falla, las demás siguen; reporter incluye la falla.

---

## 11. Seguridad (sección dedicada)

Decisión del usuario: foco explícito en seguridad, más allá de auth/ACL ya cubiertos en §8.

### 11.1 Tool-gating por configuración de credenciales

**Principio**: si una tool requiere una API key (o OAuth) y ésta no está configurada, la tool **no aparece** en el Tier 1 del listing del agente. El agente nunca intenta invocarla.

**Implementación** (`enterprise/tooling/tool_registry.py`):

```python
class ToolRegistry:
    async def list_tools_for_role(self, role: AgentRole) -> list[ToolName]:
        candidates = self._catalog.filter_by_domain(role.allowed_domains)
        # Tool-gating: filtrar las que requieren auth y no la tienen
        available = []
        for tool in candidates:
            if not tool.requires_auth:
                available.append(tool.name)
                continue
            if await self._credentials.has_valid_credential(tool.auth_key):
                available.append(tool.name)
            else:
                # Log explícito (POLA): el agente nunca sabrá que esta tool existe
                logger.info("tool %s gated: missing credential %s", tool.name, tool.auth_key)
        return available
```

**Beneficios**:
- **Principio 4 (manejo de errores estricto)**: imposible que el agente invoque algo destinado a fallar 401/403.
- **ISP**: el agente solo conoce tools utilizables.
- **POLA**: el operador entiende por qué tal tool no se ofrece — basta `vigilador credentials list` para ver qué falta.

**Schema del catálogo** (`enterprise/tooling/builtin/<dominio>/<tool>.py`):

```python
class HubSpotTool(BuiltinTool):
    name = "hubspot"
    domain = "crm"
    requires_auth = True
    auth_key = "HUBSPOT_API_KEY"           # nombre de env var o entrada OAuth
    auth_method = "API_KEY"                # API_KEY | OAUTH | NONE
```

**Healthcheck en boot**: cada tool con `requires_auth=True` corre `healthcheck()` al arrancar. Resultado se muestra al operador y se persiste en `~/.vigilador/healthcheck.log` para Dreaming/config_refresher.

### 11.2 Manejo de credenciales

- Todas las credenciales en `~/.vigilador/credentials/` (Fernet, master key per-instalación).
- NUNCA en `.env` versionado, NUNCA en DB en plaintext.
- `vigilador credentials add <tool> <key>` único punto de entrada (CLI).
- Rotación: tool con `credential_expiration: 90d` notifica al usuario via canal preferido 7 días antes.

### 11.3 Sandboxing de ejecución

- Computer Use: hard-blocks en `config/company/policies.md`. Apps marcadas `critical: true` no aceptan close/kill/alt-f4.
- E2B sandbox: ejecución de código en cloud sandbox (isolated VM), no en proceso local. Limit 120s default, 512 MB RAM.
- Skills aprendidos: primera ejecución autónoma requiere confirmación explícita; ejecuciones subsecuentes en `subagents` con depth tracking.

### 11.4 ACL de documentos indexados

(Ya descrita en §5.5. Recapitulación: cada chunk lleva `acl_scopes: TEXT[]`; queries filtran por scope del principal; el LLM NUNCA recibe chunks fuera de scope.)

### 11.5 Audit estructurado (sin tabla SQL en v3.0)

Por YAGNI no se crea tabla `audit_events` aún. En su lugar, logs estructurados (JSON) a `~/.vigilador/audit/<fecha>.jsonl` para acciones sensibles:
- Envíos de mensaje externo (email, WhatsApp, SMS)
- Mutaciones de CRM/finanzas/Linear
- Ejecución de skill aprendido en producción
- Cambios en config/company/*.md o SOUL.md

Schema:
```json
{"ts":"2026-05-25T14:32:11Z","user":"caro","action":"hubspot.contacts_create","target":"deal:0042","scopes":["write:crm"],"result":"success"}
```

Si surge requerimiento legal/regulatorio que exija audit SQL/dashboard, se promueve a tabla con migración (es trivial leer los JSONL e insertarlos).

### 11.6 Cómo cumple la constitución

- **SRP**: ToolRegistry hace gating; CredentialManager guarda credenciales; AuditLogger registra. Cada uno responsabilidad única.
- **Manejo de errores estricto**: tool-gating elimina fallas predecibles antes de que ocurran.
- **POLA**: el operador siempre puede inspeccionar por qué algo se gating, qué credenciales hay, qué se auditó.
- **YAGNI**: audit como JSONL, no tabla SQL aún. Se promueve cuando hay demanda real.

---

## 12. Enterprise Foundation

Sección que reúne los requisitos no-funcionales que distinguen un harness empresarial de un agente personal.

### 12.1 Multi-tenancy desde día 1

**Decisión**: `tenant_id UUID NOT NULL` en TODAS las tablas nuevas. v3.0 inicial single-tenant, schema preparado.

Tablas afectadas (las del plan más las nuevas):
- `ingested_documents`, `document_chunks`, `oauth_credentials`, `subagents`, `prompt_versions`, `usage_quotas`, `audit_events_jsonl_index`, `dream_runs`, `learned_skills`, `style_profiles`, `kg_nodes`, `kg_edges`.

Convención DRY: `domain/tenant.py` define `Tenant`, `TenantScopedRepository` mixin con método `_with_tenant(query)` que inyecta `WHERE tenant_id = :tid` en todas las queries. Cada repo concreto hereda.

No se construye UI ni billing per-tenant en v3.0 (eso es YAGNI). Solo schema y `TenantContext` en sesión.

### 12.2 Observability + Metrics Dashboard

**Métricas Prometheus** (`enterprise/observability/metrics.py`):

| Métrica | Tipo | Labels |
|---|---|---|
| `vigilador_session_total` | counter | tenant, playbook, complexity, status |
| `vigilador_session_duration_seconds` | histogram | playbook |
| `vigilador_tokens_total` | counter | tenant, playbook, model, direction (in/out) |
| `vigilador_tool_calls_total` | counter | tool, domain, status |
| `vigilador_tool_latency_seconds` | histogram | tool, domain |
| `vigilador_mcp_errors_total` | counter | tool, error_type |
| `vigilador_quota_consumption_ratio` | gauge | tenant, user, quota_type |
| `vigilador_ingestion_chunks_total` | counter | connector, tenant |

**Tracing OpenTelemetry**: cada `OrchestratorService.start_session` abre un trace root. Cada agente, cada tool call, cada llamada LLM = span hijo. Export a Jaeger o stdout (config). Sampling 100% en dev, 10% en prod.

**Metrics Dashboard** (`enterprise/observability/dashboard.py`): vista web (reuso del frontend SSE) que el usuario abre desde el harness para inspeccionar:
- Qué documentos se indexaron en últimas N horas (filtro por connector, autor, scopes).
- Qué tools accedieron a qué chunks (trazas de query → results).
- Qué preguntas hizo el usuario, qué playbook ejecutó, qué tools invocó cada uno.
- Conversational analytics: top 10 intents detectados, top 10 tools usadas, error rate.

Unifica los conceptos: audit log (qué pasó), conversational analytics (qué preguntan), metadata inspection (qué hay indexado), observability (métricas técnicas) — un solo dashboard.

**Health Monitor separado** (`enterprise/observability/health_monitor.py`) — decisión #81 (fix CQS detectado en auditoría):
- Corre cada 30s pingueando todas las tools/MCPs vía su `healthcheck()`.
- Actualiza tabla `tool_health(name, status: UP|DOWN|STUCK, last_check, fail_count, last_error)`.
- Ejecuta circuit breaker (3 fallos en 60s → DOWN 5 min), dispara alertas al canal del usuario.
- **`ToolRegistry.list_tools_for_role` solo LEE esta tabla** (query pura sin side-effects). Cumple **CQS** + **SRP**: el listado es lectura, la mutación de health es responsabilidad separada.
- Métrica Prometheus dedicada: `vigilador_tool_health_status{name=...}` (1=UP, 0=DOWN, 2=STUCK).

### 12.3 Disaster Recovery + Backup

**Política RTO 1h / RPO 24h**.

`enterprise/backup/manager.py`:
- Backup nocturno (dentro de Dreaming `index_maintenance`): pg_dump custom format de pgvector + `turbovec.write()` + tar de `~/.vigilador/credentials/` (cifrado con master key derivada por PBKDF2 del passphrase de admin) + tar de `config/*`.
- Destino: configurable (S3 / B2 / local filesystem). Default: local con rotación 7-30-365 (diario, semanal, anual).
- Restore: `enterprise/backup/restore.py` con CLI interna (no expuesta al usuario final).
- **Restore probado**: tarea opcional en Dreaming semanal que restaura backup en DB de prueba y valida que esquema y queries básicas funcionan. Resultado al reporter.

### 12.4 Quotas + circuit breakers per-user

`enterprise/governance/quota_manager.py`:

```python
@dataclass(frozen=True)
class QuotaLimits:
    tokens_per_day: int = 1_000_000
    sessions_per_day: int = 100
    max_usd_per_session: float = 5.0
    max_concurrent_sessions: int = 3
```

Tabla `usage_quotas(tenant_id, user_id, date, tokens_consumed, sessions_started, usd_spent)`. Update transaccional al inicio de cada llamada LLM.

Circuit breaker per-user: si consumo > 90% en ventana 1h → throttle (responde con mensaje "alcanzaste 90% de tu cuota diaria, reintenta en X minutos"). Si > 100% → block sesiones nuevas (las activas terminan).

### 12.5 SSO/SAML/OIDC

`enterprise/auth/sso/` con tres backends:

| Backend | Tecnología | Casos |
|---|---|---|
| `saml.py` | python3-saml | Azure AD, Okta, OneLogin |
| `oidc.py` | authlib | Google Workspace, Auth0, generic OIDC |
| `local.py` | argon2id (preservado) | Single-user fallback / dev |

Configuración por tenant en `config/auth/sso/<tenant>.yaml` con `idp_metadata_url`, `entity_id`, `acs_url`. Endpoint `/api/auth/sso/<provider>/login` y `/callback`. SCIM 2.0 para provisioning opcional en futuro (no v3.0).

### 12.6 Compliance evidence

`docs/compliance/` (nueva carpeta de documentos generados al runtime):
- `data-residency.md`: declara región de almacenamiento (PostgreSQL host, S3 bucket region, MiniMax API endpoint).
- `right-to-be-forgotten.md`: documentación + tool `enterprise/governance/forget_user.py` que ejecuta DELETE en cascada (ingested_documents, document_chunks, audit JSONL, snapshots, style_profiles, kg_nodes, kg_edges, subagents, usage_quotas). Tool **NO** accesible por agentes (solo admin via API protegida).
- `dpa-template.md`: Data Processing Agreement template editable por tenant.
- `soc2-readiness-checklist.md`: mapeo de controles SOC 2 TSC vs implementación del harness (cuáles cumple, cuáles requieren proceso humano, cuáles están out of scope).

### 12.7 Encryption at rest + in transit

| Capa | Tecnología |
|---|---|
| Credentials | Fernet (master key per-install, derivada PBKDF2 de passphrase admin) en `~/.vigilador/credentials/` |
| pgvector | TDE de PostgreSQL (pg_tde extension o cifrado a nivel de filesystem LUKS/BitLocker) — documentado, no impuesto por código |
| TurboVec índice | Almacenado bajo `~/.vigilador/turbovec/` con cifrado de filesystem (mismo enfoque) |
| Transport | TLS obligatorio en endpoints HTTP (uvicorn con cert), webhooks salida verifican TLS, MCPs salida validan cert pinning para los críticos (finance/, crm/) |
| Key rotation | Política 90 días. Tarea opcional de Dreaming `rotate_encryption_keys` que regenera Fernet master y re-cifra credentials. Documentado en `docs/compliance/key-rotation.md` |

### 12.8 PII detection + redaction (Presidio opt-in)

`enterprise/governance/pii_redactor.py` envuelve `presidio-analyzer` + `presidio-anonymizer` con perfiles ES+EN.

Modos de aplicación (configurable por playbook y por documento):

| Modo | Cuándo | Efecto |
|---|---|---|
| `OFF` | Default | Sin redacción |
| `INDEX_ONLY` | Antes de indexar en TurboVec/pgvector | Chunks indexados redactan PII; queries semánticas no recuperan PII original |
| `LLM_PROMPT_ONLY` | Antes de pasar chunks al LLM | Indexa original (recovery posible para usuario autorizado), pero el LLM solo ve redactado |
| `BOTH` | Index + prompt | Máxima privacidad, irreversible |

Entidades detectadas: PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN_CODE, IP_ADDRESS, MEDICAL_LICENSE + entidades ES custom (cédula colombiana, NIT, RUT, CURP, RFC).

### 12.9 Versionado de prompts/playbooks

Tabla `prompt_versions(id, tenant_id, file_path, content_hash, content, activated_at, deactivated_at, activated_by)`. Cada cambio a:
- `config/soul.md`
- `config/company/*.md`
- `config/playbooks/*.yaml`
- `config/templates/**`
- `config/skills/learned/*.yaml`

…se versiona en esta tabla automáticamente por `enterprise/governance/version_tracker.py` (watcher de filesystem). Rollback CLI interna: `vigilador-admin prompt rollback <file> <version_id>` reescribe el archivo desde DB y registra nueva versión.

A/B testing: dos versiones activas etiquetadas A/B, `PromptComposer` enrutar 50/50 por session_id hash. Métricas Prometheus segmentadas por versión.

---

## 13. Idioma: interno EN / externo en idioma detectado

`enterprise/governance/language_router.py`.

**Reglas**:
- TODO lo que el LLM ve en sistema (system prompts, BranchOverlay, AgentRole, tool descriptions, schemas, SOUL.md, COMPANY/*.md, playbook YAML) **se redacta en inglés**.
- TODO lo que sale al usuario (respuesta final, correos, informes, mensajes en canales, entregables de Templates) **se redacta en el idioma del usuario** (default español, autodetectado por turno).

**Detección**: librería `lingua-py` (no `langdetect` por su lenta inicialización). Detecta idioma del último input del usuario y guarda en `session.locale`. Si cambia idioma intra-sesión, se actualiza.

**Implementación en composer**:

```python
class PromptComposer:
    def compose(self, query: str, role: AgentRole, locale: Locale) -> ComposedPrompt:
        system = (
            self._system_base.render_en()                # always EN
            + self._domain_profile.render_en(role)       # always EN
            + self._soul.render_en()                     # always EN
            + self._company.render_en()                  # always EN (translated at edit time)
            + f"\n\nRespond to the user in {locale.name}.\n"  # instrucción EN al modelo
        )
        return ComposedPrompt(system=system, user=query, locale=locale)
```

**Templates de Templates** (correos, informes): tienen variante por locale (`config/templates/informes/ventas_mensual.es.md`, `.en.md`). `template_render(template_id, variables, locale=session.locale)` selecciona.

**Migración**: SOUL.md y COMPANY/*.md actuales en español del plan deben re-redactarse en inglés durante F0. El usuario edita en inglés; si prefiere editar en español, se traduce una vez al guardar (deja registro de origen).

---

## 14. Embeddings + reranker locales con switch

`infra/embeddings/local_embeddings.py`:

```python
class LocalEmbeddingsGateway(EmbeddingGateway):
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "auto"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name, device=device)
    async def embed_batch(self, texts: list[str]) -> list[Vector]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()
```

`infra/reranking/local_reranker.py`:

```python
class LocalReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(model_name)
    async def rerank(self, query: str, passages: list[str], top_k: int) -> list[tuple[int, float]]:
        scores = self._model.predict([(query, p) for p in passages])
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])[:top_k]
        return ranked
```

**Switch** en `config/settings.yaml`:

```yaml
embeddings:
  backend: local                  # local | gemini
  local_model: BAAI/bge-m3
  device: auto                    # auto | cpu | cuda | mps
reranking:
  enabled: true
  backend: local
  local_model: BAAI/bge-reranker-v2-m3
  top_k_pre_rerank: 50
  top_k_final: 10
```

**Coexistencia con Gemini**: `infra/embeddings/gemini_gateway.py` sigue intacto. `Container` (DI) elige al boot según `settings.embeddings.backend`. El 2.0 sigue con Gemini por default; el 3.0 default a local.

**Pipeline de búsqueda con reranking**:
1. Query → embed local → TurboVec.search(allowlist, k=50)
2. Top 50 → reranker local cross-encoder → top 10
3. Top 10 → al LLM con compresión si aplica

Resultado típico: +5-10 puntos de recall@10 efectivo gracias al reranking, sin coste por API.

---

## 15. Knowledge Graph dual

**Decisión**: dos grafos coexisten, con propósitos distintos, mismo backend (pgvector + NetworkX) pero namespace separado.

### 15.1 Grafo de investigación (preservado del 2.0)

Vive en `application/graph/knowledge_graph_service.py` (existente). Entidades extraídas de **resultados de research público** (papers, web, patents). Usado por playbooks `technology-watch` y `deep-research`. Sin cambios.

### 15.2 Grafo de conocimiento empresarial (nuevo)

`enterprise/graph/business_kg_service.py`. Entidades extraídas del **corpus indexado del usuario** (Drive, OneDrive, WhatsApp, COMPANY/*.md, CRM, correos).

**4 tipos de entidades** (decisión usuario):

| Tipo | Fuente | Atributos | Relaciones |
|---|---|---|---|
| **Person** | COMPANY/organization.md, correos (from/to), WhatsApp, CRM contacts | role, area, email_hash, joined_at | reports_to, manages, peer_of, mentions |
| **Document** | Todos los ingested_documents | type, author_id, date, acl_scopes | authored_by, mentions, references, version_of |
| **Process** | COMPANY/processes.md | cadence, owner_role, owner_systems | owned_by, depends_on, produces |
| **Organization** | Correos external, CRM accounts, docs mencionados | type (customer/supplier/competitor), industry, country | supplies_to, competes_with, customer_of, mentioned_in |

Schema:

```sql
CREATE TABLE kg_nodes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  graph_namespace TEXT NOT NULL,        -- 'research' | 'business'
  kind TEXT NOT NULL,                    -- person | document | process | organization
  name TEXT NOT NULL,
  attributes JSONB NOT NULL,
  acl_scopes TEXT[] NOT NULL,
  source_document_id UUID REFERENCES ingested_documents(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON kg_nodes (tenant_id, graph_namespace, kind);
CREATE INDEX ON kg_nodes USING GIN (acl_scopes);

CREATE TABLE kg_edges (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  graph_namespace TEXT NOT NULL,
  src UUID REFERENCES kg_nodes(id) ON DELETE CASCADE,
  dst UUID REFERENCES kg_nodes(id) ON DELETE CASCADE,
  relation TEXT NOT NULL,
  confidence FLOAT NOT NULL,
  source_chunks UUID[],                  -- chunks que evidencian la relación
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON kg_edges (tenant_id, graph_namespace);
CREATE INDEX ON kg_edges (src);
CREATE INDEX ON kg_edges (dst);
```

**Extracción**: tarea de Dreaming `kg_extraction` (sub-tarea de `ingestion_sync`) que tras indexar cada documento corre el extractor existente (`application/extraction/entity_extractor.py`) extendido para los 4 tipos. PII redaction se aplica **antes** de poblar nodos del grafo empresarial.

**Consumo**: tool `enterprise/tooling/builtin/research/business_kg.py`:
- `kg_query(question, kinds=[...])`
- `kg_find_path(src_name, dst_name)`
- `kg_neighbors(node_name, depth=2)`
- `kg_explain_relation(src, dst)` — devuelve los chunks que evidencian la relación

**Dashboard**: vista navegable en Metrics Dashboard (§12.2) con D3.js (ya en el stack del frontend).

---

## 16. Approval workflows acotados

**Reglas**:

1. **Cero transacciones bancarias**: tools de `finance/` son read-only o generan borradores/reportes, jamás ejecutan transferencias. Mecanismo: cualquier método marcado `mutates_money: true` en su schema se gating-out a nivel `ToolRegistry`. Aplicable a Plaid (solo `accounts_get`, `transactions_get`, `auth_get`, `identity_get` — todos read), QuickBooks (`invoice_list`, `account_balance`, `report_pl` activos; `invoice_create` requiere approval ya que crea factura sin enviar pago; pagos descartados), Excel/PowerBI (solo cálculos).

2. **Cero permiso de delete**: cualquier método cuyo nombre coincida con regex `^(delete|remove|destroy|purge|drop)_` se gating-out automáticamente en `ToolRegistry`. Aplicable a `gmail_delete`, `drive_delete`, `hubspot_contacts_delete`, etc. OAuth scopes solicitados al usuario excluyen explícitamente delete permissions (Drive: `drive.file` + `drive.readonly`, MS Graph: scopes equivalentes).

3. **Cero modificación a config/governance**: el agente **NUNCA** edita `config/soul.md`, `config/company/*.md`, `config/templates/*`, `config/playbooks/*`. Si detecta que algo deberia cambiar (ej. detecta una persona nueva en correos no listada en organization.md), **solo propone el cambio al usuario por canal** con diff sugerido. Usuario edita manualmente.

4. **Approval workflows para acciones masivas**:

| Acción | Threshold | Workflow |
|---|---|---|
| Envío de email | > 10 destinatarios distintos en single batch (incluye CC/BCC) | Mensaje al canal preferido del usuario con preview (subject + first 200 chars body + destinatarios). Botones "Aprobar" / "Editar" / "Rechazar". Timeout 24h → expira como "rechazado". |
| Mutación CRM | > 5 registros en single batch | Mismo flujo: preview de cambios (campo, valor anterior, valor propuesto). |
| Ejecución de skill aprendido | Primera vez autónoma | Mensaje con: "Voy a ejecutar el skill `audit-inventory` con parámetros X. Te muestro los pasos: 1... 2... 3... ¿Apruebo?". |

**Storage de approvals pendientes**: tabla `pending_approvals(id, tenant_id, user_id, action, payload, expires_at, status)`. Si timeout → status=`expired`. Si aprobado vía canal → trigger ejecución asíncrona.

5. **Bot accounts vs cuentas del usuario**:
   - El harness puede operar con **bot accounts** dedicados cuando estén disponibles (ej. cuenta `vigilador-bot@empresa.com` en Slack, bot personal de Telegram).
   - O con **cuentas del usuario** via OAuth con scopes restrictivos.
   - Switch configurable per-tool en `config/tools/<tool_name>.yaml`:
   ```yaml
   account_mode: bot                # bot | user_oauth
   bot_credential: SLACK_BOT_TOKEN  # cuando account_mode=bot
   ```

---

## 17. Onboarding wizard + Update mechanism + Migration runner

### 17.1 Onboarding wizard

`enterprise/onboarding/wizard.py`. Activado en el primer login a un tenant nuevo (`tenant.first_login_at IS NULL`). Conversacional vía el mismo canal del usuario:

1. **Saludo + presentación** (2 turnos).
2. **Crear COMPANY/identity.md**: bot pregunta nombre, sector, tamaño, HQ, mercados, misión. Genera el archivo.
3. **Crear COMPANY/organization.md**: bot pregunta áreas, headcount, cargos clave. Genera estructura.
4. **Crear COMPANY/processes.md, systems.md, policies.md**: bot pregunta 3-5 procesos clave, sistemas, restricciones críticas. Genera archivos.
5. **Conectar primer OAuth**: bot ofrece link para autorizar Drive o OneDrive. Espera callback.
6. **Lanzar primera ingestión**: bot pide carpeta raíz a indexar, lanza `ingestion_sync` con feedback de progreso en canal.
7. **Probar primer playbook**: bot sugiere "¿Quieres probar con una pregunta tipo 'resume el último contrato firmado'?". Ejecuta playbook `general`, muestra resultado.

Tiempo total esperado: 15-25 minutos. Si el usuario abandona, se reanuda en próxima sesión desde el paso siguiente.

### 17.2 Update mechanism

`enterprise/updates/manager.py`. Tarea opcional de Dreaming semanal:
- Para cada tool `WRAP-SDK` y `CLONE-UPSTREAM`: consulta versión en PyPI / GitHub releases.
- Si hay update y patch notes contienen `security|fix|vulnerability` → marca tool como `update_pending` en `tool_updates` table.
- Notifica al usuario. Update se aplica al próximo restart con backup automático del estado previo.
- Tools `COPY-HERMES` no se auto-actualizan (Hermes es referencia, no dependencia activa). Updates manuales si llegan a importarse.

### 17.3 Migration runner (Alembic)

Schema migrations versionadas. Cada cambio a tablas en `alembic/versions/`. Auto-run en boot del harness si hay migrations pendientes (con backup pre-migration). Rollback CLI interna disponible.

---

## 18. Plan de migración (6 fases con F0 Enterprise Foundation)

| Fase | Sem | Objetivo | Criterio verificable |
|---|---|---|---|
| **F0: Enterprise Foundation + Sprint A extracción** | 1-4 | **Auditoría de licencias** (~30 archivos Hermes + 32 paquetes PyPI). **Sprint A** del inventario (`docs/extraction-inventory.md §5`): copiar `tools/registry.py`, `lazy_deps.py`, `schema_sanitizer.py`, `tool_output_limits.py`, `debug_helpers.py` a `enterprise/tooling/`. Multi-tenancy schema (`tenant_id` everywhere) + Observability básica (Prometheus + 3 traces clave: session/agent/tool) + Backup script + Quotas (base copiada de `budget_config.py`) + SSO (1 provider: Google Workspace OIDC) + Encryption capas declaradas + PII Presidio opt-in + Versionado de SOUL/COMPANY/playbooks (watcher + tabla prompt_versions, base copiada de `checkpoint_manager.py`) + Onboarding wizard esqueleto + Alembic. Embeddings locales (bge-m3) activos. LanguageRouter funcionando (interno EN / externo ES/detected). | Tests 2.0 verdes. Licencias auditadas y atribuciones añadidas a cada archivo copiado. Sprint A: 5 archivos copiados, importables como `from vigilancia_multiagente.enterprise.tooling import registry`. Crear segundo tenant aislado (datos no se cruzan). Métricas Prometheus expuestas en `/metrics`. SSO login con Google. Backup + restore validados en DB de prueba. Embeddings locales generan vectores 768-d en < 200ms batch=32. |
| **F1: Foundation** | 5-7 | Crear `enterprise/` + `DomainProfile` + `AgentRole` + `ComplexityClassifier` + `SubagentRegistry`. Empaquetar 6 ramas como plugin `technology-watch`. | Suite 2.0 verde. API `/research/*` funcional. ComplexityClassifier devuelve SIMPLE para "hola" y COMPLEJA para "decide si abrir sucursal en Bogotá". |
| **F2: TurboVec + Ingestion (local_fs + Drive) + KG empresarial básico** | 8-11 | TurboVec backend + 2 connectors + pipeline + ACL + extracción de Person/Document para KG empresarial. CLI interna `vigilador-admin ingest` (no expuesta al usuario). | Indexar 100 docs heterogéneos. ACL respetada (test E2E). recall@10 ≥ 0.92 vs pgvector baseline. KG empresarial extrae 20+ Person nodes con role inferido. |
| **F3: ~79 capacidades en 17 dominios (40 Tier1 + 23 Tier2 + 6 Tier3 + 10 sub-tools locales) + MCPProcessSupervisor + LocalAppDetector + Tool Discovery + Skill Learning + Tool-gating + Templates + Approval workflows + Contrato `ToolWrapper` unificado** | 12-23 | `enterprise/tooling/builtin/{search,web,documents,productivity,meetings,crm,communication,finance,desktop,code,research,people,personalization,design,engineering,media,analytics}/` con ~40 tools Python (4 nuevos dominios). **`MCPProcessSupervisor`** gestiona ~15 MCPs Tier 2 en procesos STDIO aislados. **`LocalAppDetector` (nuevo ~80 LOC)** detecta apps locales instaladas via Win registry + macOS /Applications. **10 sub-tools `*_local.py` nuevas** para Excel/Power BI Desktop/Tableau Desktop/AutoCAD/SolidWorks/Outlook/Word/PowerPoint/iMessage (cubre 60-70% PYMEs no-cloud). Contrato `BuiltinTool` ampliado: `requires_key` + `env_var` + `signup_url` + `pricing`. Tier 2 MCPs en `config/mcp/external.yaml`. **17 tools FREE sin API key desde día 1**. Computer Use con skill learning, file_system, writing_style, Templates, teams, zoom, Google Forms. | Cada una de las ~79 capacidades pasa `healthcheck()` o está gated. Test gating: borrar TAVILY_API_KEY → tool desaparece. Test circuit breaker: 3 fallos en 60s → tool DOWN + alerta + recovery. Test supervisor: `kill -9 discord-mcp` → auto-restart en < 16s, otros MCPs intactos. Test LocalAppDetector: en máquina sin Excel → `excel_local` NO aparece, en máquina con Excel → SÍ aparece. Test conflicto cloud/local: usuario con ambos → respeta `prefer: local` config. Test delete: `gmail` nunca expone `delete_message`. Test approval: envío masivo aprueba/rechaza. Test FREE: usuario sin API keys puede usar 17 tools. Test privacidad: `excel_local` analiza spreadsheet → vectores quedan en TurboVec local, datos jamás salen del PC. |
| **F4: CrewAI + Playbooks (general + deep-research + decision-debate) + KG empresarial completo** | 20-22 | CrewAI bridge + DebateCoordinator + 3 playbooks YAML. Extracción KG completa (Process, Organization). Dashboard de KG en frontend. | E2E debate. E2E deep-research con ramas dinámicas según complejidad. KG empresarial navegable con D3 mostrando relaciones person→document→process→organization. |
| **F5: Channels (Telegram + WhatsApp) + connectors restantes + Dreaming completo + Skill Learning auto-corrección + Onboarding wizard final** | 23-28 | 2 canales + 3 connectors (OneDrive, WhatsApp, chatbot) + frozen_snapshot + context_compressor + Dreaming completo (7 tareas: ingestion_sync, kg_extraction, memory_consolidation, skill_curator, config_refresher, index_maintenance, learned_skill_revalidation + 4 proactivas: email triage, to-do extraction, agenda briefing, news digest) + Writing Style Learning + Skill Learning recovery + Onboarding wizard completo. | E2E por Telegram con datos de Drive indexado. Compresor activa al cruzar 70% context. Dreaming corre 3 AM, deja reporte + borradores etiquetados. Onboarding wizard guía usuario nuevo en 20 min. |

**Riesgos por fase**:
- F0: complejidad de SAML/SSO subestimada → arrancar con OIDC Google solo, SAML genérico en F1 si surge demanda real (YAGNI).
- F0: bge-m3 lento en CPU del usuario → fallback a Gemini con switch ya implementado.
- F1: imports circulares al mover ramas → `import-linter` en CI.
- F2: degradación recall PQ 4-bit → re-ranking obligatorio + métrica recall@10.
- F3: 43 tools = 43 puntos de cambio → implementar 5 por sprint con healthcheck previo al siguiente. PII opcional bloqueando tools que llaman LLM externo si no está configurado correctamente.
- F4: CrewAI versionado evoluciona rápido → pin estricto + regression tests.
- F5: aprobación Meta WhatsApp → Telegram primero, WhatsApp en paralelo.

---

## 19. Documento entregable: `docs/vigilador-3.0-enterprise-design.md`

### Estructura

```
# Vigilador Tecnológico 3.0 — Diseño Empresarial

## 0. Resumen ejecutivo + supuestos explícitos
## 1. Visión y alcance
## 2. Estado del arte (Hermes Agent, OpenClaw, TurboVec) — referencias, no copias
## 3. Alineación con la constitución del proyecto (tabla principio → cómo se aplica)
## 4. Arquitectura
   4.1 Estructura de carpetas
   4.2 Componentes nuevos / refactorizados / preservados
   4.3 Diagrama de flujo
## 5. Orquestador complejidad-aware
   5.1 ComplexityClassifier
   5.2 Sub-agentes recursivos con guardrails
   5.3 SubagentRegistry (schema)
## 6. 43 tools internalizadas en 13 sub-carpetas (incluye meetings y Google Forms)
   6.1 Tres estrategias de origen (COPY-HERMES / CLONE-UPSTREAM / WRAP-SDK)
   6.2 Catálogo completo sub-carpetizado por dominio funcional
   6.3 Convención BuiltinTool
   6.4 Computer Use + Skill Learning (especial)
   6.5 Tool discovery progresivo (3 tiers)
   6.6 Sistema de Templates (módulo crítico: informes, propuestas, contratos, presentaciones)
   6.7 Tool-gating por credenciales (referencia a §12.1)
## 7. Subsistema de Indexación
   7.1 TurboVec
   7.2 Connectors
   7.3 Pipeline
   7.4 OAuth + ACL
   7.5 Schema SQL completo
## 8. Metodologías de tool calling
## 9. Combos / Playbooks (CrewAI + YAML)
## 10. Governance y Seguridad
   10.1 SystemBase + DomainProfile + SOUL.md + config/company/*.md (cuatro capas)
   10.2 Auth multi-canal
   10.3 ACL por documento
## 11. Modo Dreaming (auto-mantenimiento + ingesta + proactivo)
   11.1 Arquitectura (enterprise/dreaming/)
   11.2 Triggers (cron 3 AM + idle > 10 min)
   11.3 6 tareas de mantenimiento (incluye ingestion_sync — indexación automatizada)
   11.4 Writing Style Learning (módulo personalization/)
   11.5 Dreaming proactivo: email triage, to-do extraction, agenda briefing, news digest
   11.6 Reporter + Guardrails
## 12. Seguridad
   12.1 Tool-gating por credenciales
   12.2 Manejo de credenciales (Fernet, ~/.vigilador/credentials/)
   12.3 Sandboxing (computer use hard-blocks, E2B, skill learning con confirmación)
   12.4 ACL de documentos (referencia §5.5)
   12.5 Audit estructurado (JSONL, no SQL aún por YAGNI)
## 13. Channel Gateway
## 14. Enterprise Foundation
   14.1 Multi-tenancy desde día 1 (schema, tablas, queries)
   14.2 Observability (Prometheus + OpenTelemetry traces + Metrics Dashboard)
   14.3 Disaster Recovery + Backup (RTO 1h, RPO 24h)
   14.4 Quotas + circuit breakers per-user
   14.5 SSO/SAML/OIDC
   14.6 Compliance evidence (data residency, right to be forgotten, DPA, SOC 2 readiness)
   14.7 Encryption at rest + in transit (TDE pgvector, TLS obligatorio, key rotation 90d)
   14.8 PII detection + redaction (Presidio opt-in)
   14.9 Versionado de prompts/playbooks (tabla prompt_versions)
## 15. Idioma: interno EN / externo ES o detectado (LanguageRouter)
## 16. Embeddings + reranker locales (bge-m3, bge-reranker-v2-m3) con switch
## 17. Knowledge Graph dual (investigación + empresarial con 4 tipos de entidades)
## 18. Approval workflows acotados (no transacciones)
## 19. Onboarding wizard + Update mechanism + Migration runner
## 20. Plan de migración (6 fases con criterios verificables — F0 nueva: Enterprise Foundation)
## 21. Preguntas abiertas y decisiones pendientes
## Apéndices
   A. Mapeo archivo-por-archivo (qué del 2.0 muta, qué se preserva)
   B. Variables de entorno nuevas
   C. Glosario
   D. Referencias (Hermes, OpenClaw, TurboVec, CrewAI, MiniMax M-2.5/M-2.7, bge-m3, Presidio, OpenTelemetry, Alembic, SAML 2.0)
```

### Qué incluir vs referenciar
- **Incluir**: tablas, diagramas ASCII, schema SQL completo (incluye `tenant_id` desde día 1), snippets YAML/Python, tabla de las 43 tools con origen/tools, métricas Prometheus declaradas.
- **Referenciar**: `ARQUITECTURA.md` (hexagonal 2.0), `SPEC_V2.md`, `docs/v3-enterprise-toolkit-extraction.md`, `.specify/memory/constitution.md`, código del 2.0 por path:línea.

---

## 20. Preguntas abiertas (para resolver durante implementación)

1. **MiniMax M-2.5 disponibilidad**: confirmar que `infra/llm/minimax_client.py` puede parametrizar `model` para alternar entre M-2.7 y M-2.5. Verificar al inicio de F3.
2. **CrewAI + MiniMax**: confirmar que CrewAI 0.x acepta `base_url` custom para clientes OpenAI-compatible. Verificar en F4 antes de codificar el bridge.
3. **TurboVec en Windows 11**: confirmar que `pip install turbovec` funciona o requiere build con Rust. Verificar al inicio de F2.
4. **Licencias de los 43 tools**: auditar antes de F3. Cualquiera con licencia GPL/AGPL → descartar o sustituir.
5. **bge-m3 latencia en CPU del usuario**: medir al inicio de F0. Si > 500ms batch=32 → fallback Gemini o GPU local.
6. **Presidio + entidades custom LATAM**: validar precision sobre cédula colombiana, NIT, RUT, CURP. Si baja → entrenar patrones custom.
7. **SAML providers prioritarios**: ¿el usuario tiene casos concretos en mente (Azure AD vs Okta vs Auth0)? Esto define cuál implementar primero en F0.
8. **Quotas defaults**: ¿valores razonables para PYME en COP? Mi propuesta: tokens 1M/día, sesiones 100/día, $ 5 USD/sesión. Validar con el usuario.
9. **Bot accounts disponibilidad**: ¿el usuario puede crear bot accounts en Slack/HubSpot/Linear, o todo será OAuth del usuario?
10. **Compliance regional**: ¿el harness debe alinear a Habeas Data Colombia (Ley 1581/2012), LGPD Brasil, o solo GDPR genérico? Define qué incluye `docs/compliance/`.

---

## Verificación de este plan

1. **Coherencia interna**: cada componente referenciado en §2.2 tiene su sección detallada (§3–§9). Mapeo archivo-por-archivo en apéndice A coincide con §2.1.
2. **Validación contra código actual**: las referencias a `branch_coordinator.py:47`, `system_base.py:28`, `branch_coordinator.py:44 MAX_REPLANS_PER_SESSION`, los 14 MCPs de `mcp-providers.json` están confirmadas leyendo los archivos.
3. **Realismo técnico**:
   - TurboVec: paquete real verificado (2.6K stars en GitHub, PyPI, integraciones LangChain/LlamaIndex).
   - CrewAI: framework maduro, soporta base_url OpenAI-compatible.
   - PostgreSQL `tsvector` + GIN: feature estable, sin extensiones extra.
4. **Compatibilidad con 2.0**: F1 exige tests verdes del 2.0 como criterio. Plugin `technology-watch` mantiene API `/research/*` idéntica.
5. **Alineación constitucional**: §0 incluye tabla principio → aplicación. Cero scheduler, cero audit log, cero device tokens en v3.0 inicial (YAGNI). Solo 5 fases, no 6 (recortada F6 a "cuando surja demanda real").
6. **Aprobación**: este plan se entrega vía `ExitPlanMode` antes de cualquier escritura del documento `docs/vigilador-3.0-enterprise-design.md` o de código.
