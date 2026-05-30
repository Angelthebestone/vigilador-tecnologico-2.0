# 00b — Alcance MVP y cronograma reducido

> **Vigente desde 2026-05-26**. Si este documento contradice el alcance declarado en cualquier otro archivo del set, **manda este documento** para la fase MVP. El catálogo completo de capacidades sigue siendo válido como **roadmap post-MVP**, pero NO se implementa en esta primera entrega.
>
> Complementa al [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md). Léelos en orden: canon C0 primero, luego este MVP scope C1.

---

## Por qué un MVP reducido

El plan acumulaba ~79 capacidades en 4 tiers, 17 dominios funcionales, 8 playbooks, 7 modos preconfigurados, 5 motores de persistencia y 8 superficies de frontend. La auditoría mostró que el alcance era **demasiado ambicioso para validar arquitectura**: se necesita primero una versión simple operacional que confirme que la jerarquía `Channel → Mode → Agent → Playbook → Skill → Capability` funciona en producción con un cliente real, sin diluir esfuerzo en breadth.

Esta entrega MVP prioriza:

1. **Reusar lo que ya funciona del 2.0**: los 15 MCPs registrados + workstreams + 6 agentes de rama + pipeline existente.
2. **Añadir solo lo mínimo nuevo** para habilitar `enterprise/`: 1 LLM nuevo, 1 MCP de Google Workspace, ~4 tools básicas, frontend de consola mínimo.
3. **Documentar todo lo demás** como roadmap accesible pero **bloqueado** para implementación hasta validación del MVP.

---

## Decisiones MVP (C1)

| ID | Decisión | Origen |
|---|---|---|
| **C1.1** | **LLM default del MVP: Xiaomimimo `mimo-v2-flash`** (reemplaza MiniMax M-2.7 como default inicial). MiniMax queda como adapter opcional implementable cuando se quiera. | Usuario explícito esta sesión |
| **C1.2** | Tiers 1 y 2 se **conservan ambos**; los archivos de los demás tiers (Tier 3 traducidos + sub-tools `*_local.py`) **NO se eliminan** del set — solo se difieren a roadmap. | Usuario explícito esta sesión |
| **C1.3** | **Dominios MVP**: solo `search`, `web`, `research`, `documents`. Los otros 13 dominios documentados pero fuera del MVP. | Usuario explícito esta sesión |
| **C1.4** | **MCP de Google Workspace** se añade al Tier 2 como ÚNICA adición vía `MCPProcessSupervisor` en MVP. | Usuario explícito esta sesión |
| **C1.5** | **Dominios nuevos** (design/engineering/media/analytics) **se conservan documentados** en el set pero NO se implementan en MVP. La arquitectura debe quedar lista para activarlos sin refactor. | Usuario explícito esta sesión |
| **C1.6** | **Frontend MVP mínimo**: login + onboarding (empresa+ubicación+providers) + chat con selección de modo + visor de workstreams del 2.0 + configuración básica de tools/MCPs. Las otras 4 superficies (artefactos, optimización, admin de repos, audit changelog rollback) quedan post-MVP. | Usuario explícito esta sesión |

---

## Stack del MVP

| Capa | Componente | Origen |
|---|---|---|
| **LLM principal** | Xiaomimimo `mimo-v2-flash` vía API OpenAI-compatible | Nuevo adapter `infra/llm/xiaomimimo_client.py` |
| LLM alterno (opcional) | MiniMax M-2.7 (existente 2.0) | `infra/llm/minimax_client.py` preservado |
| LLM debates (opcional, diferido) | MiniMax M-2.5 | Roadmap |
| **Embeddings** | `GeminiEmbeddingGateway` existente del 2.0 (vía API) | `infra/embeddings/gemini_gateway.py` preservado |
| Embeddings opcional | `bge-m3` local (deferred) | Roadmap |
| **Reranker** | `SemanticReranker` (Cohere por API + fallback embeddings) existente | `infra/reranking/semantic_reranker.py` preservado |
| **Vector index** | `TurboVecIndex` único | `infra/persistence/turbovec_index.py` nuevo |
| **Metadata DB** | PostgreSQL existente del 2.0 | Preservado |
| **Persistencia auxiliar** | JSONL (audit) + YAML (config) | Convenciones del set |
| FTS opcional | SQLite FTS5 (deferred — solo si valor claro tras MVP) | Roadmap |

---

## Capacidades de Xiaomimimo `mimo-v2-flash`

Documentación oficial del proveedor:

- **Chat OpenAI-compatible**: `https://platform.xiaomimimo.com/docs/en-US/api/chat/openai-api`. Habilita tool-calling estándar y reuso de cualquier librería compatible OpenAI.
- **Image understanding (multimodal)**: `https://platform.xiaomimimo.com/docs/en-US/usage-guide/multimodal-understanding/image-understanding`. Reemplaza el MCP `minimax-image` del 2.0 si se prefiere.
- **Web search nativo (built-in tool)**: `https://platform.xiaomimimo.com/docs/en-US/usage-guide/tool-calling/web-search`. Complementa (no reemplaza) los MCPs `tavily`/`exa`/`brave` existentes — útil para queries simples sin invocar MCP externo.

Implementación recomendada del adapter:

```python
# infra/llm/xiaomimimo_client.py
from openai import AsyncOpenAI

class XiaomimimoClient:
    """
    Adapter para Xiaomimimo via API OpenAI-compatible.
    Default LLM del MVP (C1.1).
    """
    def __init__(self, api_key: str, base_url: str = "https://platform.xiaomimimo.com/v1"):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str = "mimo-v2-flash",
        **kwargs,
    ): ...

    async def image_understanding(self, image: bytes, prompt: str): ...

    async def web_search(self, query: str): ...
```

**Selección en `config/settings.yaml`**:

```yaml
llm:
  default: xiaomimimo
  adapters:
    xiaomimimo:
      enabled: true
      model: "mimo-v2-flash"
      api_key_env: "VT_XIAOMIMIMO_API_KEY"
      base_url: "https://platform.xiaomimimo.com/v1"
    minimax:
      enabled: false   # Opcional. Activar para combos M-2.7/M-2.5 en debates si se necesitan.
      api_key_env: "VT_MINIMAX_API_KEY"
```

---

## Inventario MVP de tools y MCPs

### Tier 1 (Python interno) — MVP: 4 tools nuevas

| Tool | Dominio | Estado | Origen |
|---|---|---|---|
| `file_system` | documents | NUEVO MVP | COPY-HERMES `tools/file_tools.py` + dependencias |
| `template_render` | documents | NUEVO MVP | NUEVO Python (Jinja2 sobre MD/HTML/DOCX) |
| `docx_generate` | documents | NUEVO MVP | NUEVO Python (python-docx) |
| `pdf_generate` | documents | NUEVO MVP | NUEVO Python (WeasyPrint) |

### Tier 2 (MCPs externos STDIO) — MVP: 16 MCPs (15 preservados del 2.0 + 1 nuevo)

**Preservados del 2.0** (ya funcionan en `infra/mcp/mcp-providers.json`):

| MCP | Dominio | Transport |
|---|---|---|
| `tavily` | search | HTTP |
| `exa` | search | HTTP |
| `jina` | web | HTTP |
| `brave` | search | STDIO |
| `firecrawl` | web | STDIO |
| `serper` | search/research | STDIO |
| `google_scholar` | research | STDIO |
| `arxiv` | research | STDIO |
| `fetch` | web | STDIO |
| `sandbox` | code (deferred dominio pero se mantiene activo) | STDIO |
| `markitdown` | documents | STDIO |
| `minimax-image` | media (deferred dominio pero se mantiene activo) | STDIO |
| `openalex` | research | STDIO |
| `playwright` | web | STDIO |
| `(15º del 2.0)` | — | — |

**Adición MVP**:

| MCP | Dominio | Transport | Razón |
|---|---|---|---|
| `google-workspace-mcp` | productivity (deferred dominio pero MCP se activa) | STDIO | Gmail + Calendar + Drive + Docs + Sheets + Forms en una sola integración. Crítico para onboarding empresarial real. |

**Total Tier 2 MVP**: 16 MCPs.

> **Nota**: aunque los dominios `code`, `media` y `productivity` están listados como diferidos para implementación de nuevas tools, sus MCPs preservados del 2.0 + el de Google Workspace **siguen activos**: lo que se difiere son las **nuevas tools Tier 1 Python** en esos dominios, no los MCPs que ya operan.

### Total MVP

| Tier | Capacidades MVP | Capacidades roadmap |
|---|---|---|
| Tier 1 (Python interno) | 4 nuevas | ~36 adicionales |
| Tier 2 (MCPs externos) | 16 (15 + 1) | ~7 adicionales |
| Tier 3 (TS traducidos) | 0 | 6 |
| Sub-tools `*_local.py` | 0 | 10 |
| **MVP TOTAL** | **20 capacidades** | **+59 roadmap** = 79 totales |

---

## Dominios MVP vs roadmap

| Dominio | Estado MVP | Tools en MVP | Justificación |
|---|---|---|---|
| **search** | ✅ MVP | tavily, exa, brave, serper | Núcleo del 2.0 preservado |
| **web** | ✅ MVP | jina, firecrawl, fetch, playwright | Núcleo del 2.0 preservado |
| **research** | ✅ MVP | google_scholar, arxiv, openalex, serper_patents | Núcleo del 2.0 preservado |
| **documents** | ✅ MVP | markitdown, file_system, template_render, docx_generate, pdf_generate | Necesario para informes y app-development scaffold |
| productivity | 🟡 MCPs activos sin tools nuevas | `google-workspace-mcp` (Gmail/Calendar/Drive/Docs/Sheets/Forms) | MCP cubre lo esencial; tools individuales Python pueden diferir |
| code | 🟡 MCP `sandbox` activo, sin tools nuevas | sandbox (2.0) | Habilita `app-development` y `artifact-development` mínimos |
| desktop | ⏸ Diferido | — | Computer Use Windows 11 queda en roadmap |
| crm | ⏸ Diferido | — | HubSpot/Apollo/Salesforce post-MVP |
| communication | ⏸ Diferido | — | Telegram/WhatsApp/Slack adapters post-MVP (canal Web/SSE basta) |
| finance | ⏸ Diferido | — | Excel/QuickBooks/Plaid post-MVP |
| meetings | ⏸ Diferido | — | Teams/Zoom post-MVP |
| people | ⏸ Diferido | — | BambooHR/Zendesk post-MVP |
| personalization | ⏸ Diferido | — | Writing style post-MVP |
| design | ⏸ Diferido (conservado en docs) | — | Figma/Excalidraw post-MVP |
| engineering | ⏸ Diferido (conservado en docs) | — | Blender/JupyterCAD post-MVP |
| media | ⏸ Diferido (conservado en docs) | `minimax-image` activo del 2.0 | FAL/ComfyUI/Suno post-MVP |
| analytics | ⏸ Diferido (conservado en docs) | — | Power BI/Tableau/Snowflake post-MVP |

**Total dominios activos en MVP**: 4 con tools nuevas + 2 con MCPs preservados activos = **6 dominios operativos**.

---

## Playbooks MVP vs roadmap

| Playbook | Estado MVP | Razón |
|---|---|---|
| `technology-watch` | ✅ MVP | Envoltura preservada del 2.0 (`BranchCoordinator` + 6 ramas) |
| `deep-research` | ✅ MVP | Patrón del 2.0 expuesto como playbook explícito |
| `general` | ✅ MVP | 1 agente generalista con tool discovery progresivo |
| `decision-debate` | 🟡 MVP reducido | Solo si hay 2 LLMs disponibles (MiniMax activado); si solo Xiaomimimo, queda diferido |
| `market-research` | ⏸ Post-MVP | Requiere CrewAI agentes especializados |
| `compliance-audit` | ⏸ Post-MVP | Requiere skills `finance:` plugin completo |
| `goal-pursuit` | ⏸ Post-MVP | Requiere capability tokens + checkpoint reporter completo |
| `app-development` | ⏸ Post-MVP | Requiere `e2b_sandbox` + 7 agents — diferir a F4 |
| `artifact-development` | ⏸ Post-MVP | Requiere módulo `enterprise/artifacts/` |
| `company-optimization` | ⏸ Post-MVP | Requiere módulo `enterprise/optimization/` |

**Total playbooks MVP**: 3 con plenamente operativos.

---

## Modos MVP vs roadmap

| Modo | Estado MVP | Razón |
|---|---|---|
| `default` | ✅ MVP | Sin contexto empresarial específico; fallback universal |
| `Vigilancia Tech` | ✅ MVP | = playbook `technology-watch` preservado del 2.0 |
| `CEO` | 🟡 MVP reducido | Disponible pero solo invoca playbooks MVP (general, decision-debate si MiniMax activo) |
| `CFO` | ⏸ Post-MVP | Requiere skills `finance:` plugin operativo |
| `Consultor Legal` | ⏸ Post-MVP | Requiere templates contratos + `company_geo` consultas normativa |
| `Marketing` | ⏸ Post-MVP | Requiere dominio design/media |
| `Vendedor B2B` | ⏸ Post-MVP | Requiere dominio crm |
| `Operaciones PYME` | ⏸ Post-MVP | Requiere `app-development` + `artifact-development` |

**Total modos MVP**: 3 (1 plenamente + 2 reducidos).

---

## Frontend MVP

5 superficies del frontend habilitadas en MVP (de las 8 del C0 #1):

| Superficie | MVP | Contenido |
|---|---|---|
| **Autenticación** | ✅ | Login simple, sesión local. SSO/SAML diferido. |
| **Configuración inicial / Onboarding** | ✅ | Empresa, ubicación (`company_geo`), providers LLM (Xiaomimimo default, MiniMax opcional), fuentes (Drive/OneDrive vía Google Workspace MCP), indexación inicial. |
| **Operación diaria (chat)** | ✅ | Chat con selección de modo (`/mode <id>`), visor de workstreams del 2.0, historial básico. |
| **Tools y MCPs** | ✅ reducido | Listado de los 20 tools/MCPs MVP con estado (UP/DOWN), credenciales (configurar API keys), health view. Sin admin de repos clonados (post-MVP). |
| **Datos empresariales** | ✅ reducido | Conectores cloud (Google Workspace), progreso de indexación inicial. ACL, búsqueda y reindexación post-MVP. |
| Artefactos | ⏸ Post-MVP | Dashboards/pipelines diferidos. |
| Optimización | ⏸ Post-MVP | ISO/NTC diferido. |
| Admin (Dreaming/auditoría/rollback) | ⏸ Post-MVP | Solo CLI inicial para admin. |

---

## Cronograma MVP

**Estimado**: 12-16 semanas (vs 28 sem del roadmap completo). Equipo 1-2 ingenieros.

| Fase | Duración | Alcance MVP |
|---|---|---|
| **F0** | 2-3 sem | Auditoría licencias + validar supuestos A1-A14 + estructura `enterprise/` vacía. Sin cambios respecto al plan original (07-migracion). |
| **F1** | 3-4 sem | Foundation: `XiaomimimoClient` adapter + `ToolRegistry` con discovery semántico + `tool_health` + persistencia base (sin `agent_modifications` aún) + multi-tenancy schema. |
| **F2** | 2-3 sem | TurboVecIndex + ingestion básico (Google Workspace MCP solo Drive primero) + reusar `GeminiEmbeddingGateway` y `SemanticReranker` del 2.0. |
| **F3a (MVP)** | 3-4 sem | Las 4 tools Tier 1 nuevas + `google-workspace-mcp` Tier 2 vía `MCPProcessSupervisor`. Documentar tests E2E. |
| **F4a (MVP)** | 2-3 sem | `Mode` (default + Vigilancia Tech + CEO), `ModeResolver`, 3 playbooks MVP (`technology-watch`, `deep-research`, `general`). Frontend MVP 5 superficies. |
| **F5a (MVP)** | 1 sem | Dreaming básico (solo memory consolidation + ingestion sync). PI defense + tool-gating. Sin loops avanzados de autoaprendizaje. |

**Roadmap post-MVP** (suma a la duración total si se persigue):
- F3b: resto de tools (~59 capacidades adicionales).
- F4b: resto de playbooks (`goal-pursuit`, `app-development`, `artifact-development`, `company-optimization`, `compliance-audit`, `market-research`).
- F4c: modos `CFO`, `Consultor Legal`, `Marketing`, `Vendedor B2B`, `Operaciones PYME`.
- F5b: 5 loops de autoaprendizaje (Skill learning, Writing style, Prompt self-improvement, Tool composition, COMPANY self-update).
- F5c: frontend completo (artefactos + optimización + admin).
- F5d: DR + SSO + compliance avanzado.

---

## Reformulaciones que este MVP introduce

| Decisión previa | Status tras C1 | Doc destino |
|---|---|---|
| **#7** Solo MiniMax: M-2.7 principal, M-2.5 para debates | **reformulada por C1.1**: Xiaomimimo `mimo-v2-flash` es default MVP. MiniMax queda como adapter opcional implementable. | [01](01-vision-y-arquitectura.md), [ANEXO-B](ANEXO-B-decision-log-por-tema.md) |
| #38 Sin multi-LLM (solo MiniMax) | **reformulada por C1.1 + C0 #6**: adapters por proveedor; el "solo MiniMax" original era política, ahora se relaja para Xiaomimimo. | [01](01-vision-y-arquitectura.md) |
| #75 Total catálogo 79 capacidades | Sigue vigente como **roadmap**. MVP = 20 capacidades. | [06](06-catalogo-tools-y-extraccion.md) |
| #65 4 dominios nuevos (design/engineering/media/analytics) | Sigue vigente como roadmap. **MVP no los implementa** pero la documentación se conserva. | [06](06-catalogo-tools-y-extraccion.md) |
| #82 Supuesto A10 — 28 semanas con 2-3 ingenieros | **reformulada por C1**: MVP de 12-16 semanas con 1-2 ingenieros. Roadmap completo sigue siendo 28 sem post-MVP. | [07](07-migracion-2.0-a-3.0.md) |

---

## Criterios de salida del MVP (cuándo declarar "MVP completado")

1. ✅ Frontend MVP operativo en 5 superficies.
2. ✅ Onboarding funcional: usuario nuevo registra empresa + `company_geo` + provider Xiaomimimo + conecta Google Workspace en <15 min.
3. ✅ Indexación inicial de 100 documentos vía Google Workspace MCP completa sin errores.
4. ✅ Modo `Vigilancia Tech` ejecuta el playbook `technology-watch` con los 6 agentes de rama del 2.0 sin regresiones.
5. ✅ Modo `default` con playbook `general` responde queries usando los 20 tools/MCPs MVP.
6. ✅ Modo `CEO` ejecuta `deep-research` con outputs structured + free-form.
7. ✅ `MCPProcessSupervisor` levanta 16 MCPs (15 + Google Workspace) sin crash.
8. ✅ Tool-gating funcional: tools sin API key no aparecen en listing.
9. ✅ Audit trail básico operativo en JSONL (sin tabla SQL `agent_modifications` aún).
10. ✅ Tests E2E pasan para los 20 tools MVP.

Si los 10 criterios se cumplen, se cierra MVP y se prioriza por demanda real qué de F3b/F4b/F5b implementar primero.

---

## Lo que NO entra en MVP (recordatorio)

- ❌ Sub-tools `*_local.py` (Excel/Outlook/Power BI Desktop local).
- ❌ Tier 3 traducidos (6 tools).
- ❌ Modos custom de fintech/salud/manufactura.
- ❌ Goal-pursuit con horizon de horas/días.
- ❌ App-development como playbook (flujo Spec-Kit completo).
- ❌ Artifact-development (dashboards/pipelines auto-generados).
- ❌ Company-optimization (ISO/NTC).
- ❌ 5 loops de autoaprendizaje (Skill learning, Writing style, Prompt self-improvement, Tool composition, COMPANY self-update).
- ❌ Capability tokens granulares (audit trail JSONL básico es suficiente).
- ❌ SSO/SAML/OIDC (login simple basta).
- ❌ DR + backup automatizado (manual en MVP).
- ❌ Anomaly detector (post-MVP).
- ❌ PI defense con embedding comparison (solo regex Lakera en MVP).
- ❌ Telegram/WhatsApp channels (solo Web/SSE en MVP).
- ❌ Voice channel (ya descartado en plan original #111).

Todos estos están **documentados** en sus respectivos docs del set como vigentes para el roadmap completo. No se eliminan ni se invalidan — se difieren.

---

## Cómo se relaciona con el resto del set

| Doc | Cómo se actualiza por este MVP |
|---|---|
| [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md) | Sigue vigente al 100%. Este 00b lo refina con scope MVP. |
| [README.md](README.md) | Añade enlace a este doc como "primera lectura junto con el canon". |
| [01-vision-y-arquitectura.md](01-vision-y-arquitectura.md) | Stack tecnológico: Xiaomimimo como default LLM. |
| [02-modos-y-personalidades.md](02-modos-y-personalidades.md) | Catálogo se conserva; tabla "Estado MVP" añadida (este doc 00b la provee). |
| [03-playbooks-y-orquestacion.md](03-playbooks-y-orquestacion.md) | Catálogo se conserva; status MVP/post-MVP por playbook. |
| [04-skills-y-capacidades.md](04-skills-y-capacidades.md) | Marketplaces externos quedan documentados pero no se cargan en MVP (post-MVP). |
| [05-autoaprendizaje-y-autonomia.md](05-autoaprendizaje-y-autonomia.md) | 5 loops documentados pero NINGUNO implementado en MVP — todo a F5b. |
| [06-catalogo-tools-y-extraccion.md](06-catalogo-tools-y-extraccion.md) | Tabla MVP añadida arriba; sprints A-K se replanifican F3a (MVP) + F3b (roadmap). |
| [07-migracion-2.0-a-3.0.md](07-migracion-2.0-a-3.0.md) | Fases F3-F5 se splittean en MVP (F3a/F4a/F5a) y roadmap (F3b/F4b/F5b/c/d). |
| [08-gobernanza-seguridad-y-operaciones.md](08-gobernanza-seguridad-y-operaciones.md) | Las políticas (tool-gating, no-delete, PI defense básico, audit trail JSONL) se aplican en MVP. SSO, DR, anomaly diferidos. |
| [ANEXO-A](ANEXO-A-mapa-dependencias.md) | Diagramas representan el estado final (post-MVP). Para visualizar MVP, hacer mental scoping a los nodos marcados ✅. |
| [ANEXO-B](ANEXO-B-decision-log-por-tema.md) | Decisiones C1.1-C1.6 añadidas como sub-set. Reformulación explícita de #7, #38 y #82. |

---

## Checklist de implementación del MVP

- [ ] `00b-mvp-scope-y-cronograma.md` (este doc) referenciado desde README como **primera lectura junto con C0**.
- [ ] `infra/llm/xiaomimimo_client.py` implementado (chat + image + web_search).
- [ ] `config/settings.yaml` con `llm.default: xiaomimimo`.
- [ ] Variable de entorno `VT_XIAOMIMIMO_API_KEY` documentada en `.env.example`.
- [ ] `config/mcp/external.yaml` con entrada `google-workspace-mcp` configurada.
- [ ] 4 tools Tier 1 nuevas (`file_system`, `template_render`, `docx_generate`, `pdf_generate`) implementadas.
- [ ] `MCPProcessSupervisor` levanta los 16 MCPs (15 del 2.0 + Google Workspace).
- [ ] 3 modos MVP (`default`, `Vigilancia Tech`, `CEO`) registrados en `config/modes/`.
- [ ] 3 playbooks MVP (`technology-watch`, `deep-research`, `general`) operativos.
- [ ] Frontend MVP 5 superficies operativas.
- [ ] 10 criterios de salida del MVP cumplidos.
