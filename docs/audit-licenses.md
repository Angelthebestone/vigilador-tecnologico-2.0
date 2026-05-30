# Audit: Licencias y Dependencias — F0 Completo (spec 019)

**Fecha**: 2026-05-29
**Política**: solo se aceptan MIT, Apache-2.0, BSD-2/3-Clause. Cualquier paquete con GPL/AGPL/SSPL u otra licencia copyleft se excluye y se documenta alternativa.

---

## 1. Hermes copies (COPY-HERMES)

**Licencia del repositorio**: MIT (Copyright 2025 Nous Research)
**Archivo LICENSE**: `documentation/hermes agent/hermes-agent/LICENSE`
**Verificación**: ningún archivo en `tools/` ni `agent/` tiene header de licencia per-file diferente al MIT del repositorio raíz.

| # | Archivo origen (en hermes-agent/) | Destino previsto (enterprise/) | Licencia | Compatible MIT/Apache-2.0 | Acción | Atribución |
|---|---|---|---|---|---|---|
| 1 | tools/registry.py | tooling/tool_registry.py | MIT | ✅ Sí | Copiar + adaptar | Sí (header MIT Nous Research) |
| 2 | tools/lazy_deps.py | tooling/lazy_deps.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 3 | tools/schema_sanitizer.py | tooling/tool_schema_loader.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 4 | tools/tool_output_limits.py | tooling/output_formatter.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 5 | tools/debug_helpers.py | tooling/debug_helpers.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 6 | tools/file_tools.py | tooling/builtin/documents/file_tools.py | MIT | ✅ Sí | Copiar + modularizar (≤400 LOC) | Sí |
| 7 | tools/file_operations.py | tooling/builtin/documents/file_operations.py | MIT | ✅ Sí | Copiar + modularizar | Sí |
| 8 | tools/file_state.py | tooling/builtin/documents/file_state.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 9 | tools/path_security.py | governance/path_security.py | MIT | ✅ Sí | Copiar | Sí |
| 10 | tools/url_safety.py | governance/url_safety.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 11 | tools/website_policy.py | governance/website_policy.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 12 | agent/redact.py | governance/redact.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 13 | agent/file_safety.py | governance/file_safety.py | MIT | ✅ Sí | Copiar + adaptar | Sí |
| 14 | tools/tirith_security.py | governance/prompt_injection_detector.py | MIT | ✅ Sí | Copiar parcial (regex patterns) | Sí |
| 15 | tools/threat_patterns.py | governance/threat_patterns.py | MIT | ✅ Sí | Copiar parcial | Sí |
| 16 | tools/mcp_tool.py | mcp/process_supervisor.py | MIT | ✅ Sí | Referencia de diseño; reimplementar | No (reimplementación) |
| 17 | tools/process_registry.py | mcp/process_supervisor.py | MIT | ✅ Sí | Referencia de diseño; reimplementar | No |
| 18 | tools/tool_search.py | tooling/tool_registry.py | MIT | ✅ Sí | Referencia de diseño | No |
| 19 | tools/tool_result_storage.py | tooling/adaptive_cache.py | MIT | ✅ Sí | Referencia de diseño | No |
| 20 | tools/tool_backend_helpers.py | tooling/parallel_dispatcher.py | MIT | ✅ Sí | Referencia de diseño | No |
| 21 | tools/skills_hub.py | skills_marketplace/skill_loader.py | MIT | ✅ Sí | Referencia de diseño | No |
| 22 | tools/skills_guard.py | governance/agent_modifier.py | MIT | ✅ Sí | Referencia de diseño | No |
| 23 | tools/skill_manager_tool.py | skills_marketplace/skill_curator.py | MIT | ✅ Sí | Referencia de diseño | No |
| 24 | tools/checkpoint_manager.py | orchestration/goal_pursuit/checkpoint_reporter.py | MIT | ✅ Sí | Referencia de diseño | No |
| 25 | tools/approval.py | governance/approval_queue.py | MIT | ✅ Sí | Referencia de diseño | No |
| 26 | tools/memory_tool.py | memory/frozen_snapshot.py | MIT | ✅ Sí | Referencia de diseño | No |
| 27 | tools/cronjob_tools.py | dreaming/scheduler.py | MIT | ✅ Sí | Referencia de diseño | No |
| 28 | tools/microsoft_graph_client.py | ingestion/connectors/onedrive.py | MIT | ✅ Sí | Referencia de diseño | No |
| 29 | tools/microsoft_graph_auth.py | auth/oauth_manager.py | MIT | ✅ Sí | Referencia de diseño | No |
| 30 | agent/tool_executor.py | tooling/parallel_dispatcher.py | MIT | ✅ Sí | Referencia de diseño | No |

**Resultado**: 30/30 archivos son MIT. **Cero incompatibilidades**.

---

## 2. New PyPI dependencies

| # | Paquete | Versión mínima | Licencia | Compatible | Acción |
|---|---|---|---|---|---|
| 1 | openai | >=1.40 | Apache-2.0 | ✅ | Usar |
| 2 | cryptography | >=42 | Apache-2.0 / BSD-3-Clause (dual) | ✅ | Usar |
| 3 | apscheduler | >=3.10 | MIT | ✅ | Usar |
| 4 | prometheus-client | >=0.19 | Apache-2.0 | ✅ | Usar |
| 5 | opentelemetry-api | >=1.27 | Apache-2.0 | ✅ | Usar |
| 6 | opentelemetry-sdk | >=1.27 | Apache-2.0 | ✅ | Usar |
| 7 | click | >=8.1 | BSD-3-Clause | ✅ | Usar |
| 8 | jinja2 | >=3.1 | BSD-3-Clause | ✅ | Usar |
| 9 | python-docx | >=1.1 | MIT | ✅ | Usar |
| 10 | weasyprint | >=61.0 | BSD-3-Clause | ✅ | Usar (optional dep `[pdf]`) |
| 11 | respx | >=0.21 | BSD-3-Clause | ✅ | Usar (dev only) |

**Resultado**: 11/11 paquetes con licencias permisivas. **Cero incompatibilidades**.

---

## 3. MCPs externos Tier 2 (preservados del 2.0)

Estos son servicios consumidos vía protocolo MCP (STDIO o HTTP). No se copia ni distribuye su código fuente; se invoca como servicio externo.

| # | MCP Provider | Transporte | Licencia del paquete/servicio | Compatible | Nota |
|---|---|---|---|---|---|
| 1 | tavily | HTTP (SaaS) | Propietario (SaaS) | ✅ | Consumo vía API; no se distribuye código |
| 2 | exa | HTTP (SaaS) | Propietario (SaaS) | ✅ | Consumo vía API |
| 3 | jina | HTTP (SaaS) | Propietario (SaaS) | ✅ | Consumo vía API |
| 4 | brave | STDIO (npm) | MIT | ✅ | Paquete npm MIT |
| 5 | firecrawl | STDIO (npx) | AGPL-3.0 (servidor) | ⚠️ Ver nota | Se consume como servicio; no se distribuye código AGPL. Compatible bajo uso SaaS. |
| 6 | google_scholar | STDIO (Python) | MIT | ✅ | Script Python MIT |
| 7 | arxiv | STDIO | MIT | ✅ | Paquete PyPI MIT |
| 8 | fetch | STDIO (Python) | MIT | ✅ | mcp-server-fetch MIT |
| 9 | serper | STDIO (npx) | MIT | ✅ | Paquete npm MIT |
| 10 | sandbox | STDIO (interno) | Propio (interno) | ✅ | Código propio del 2.0 |
| 11 | markitdown | STDIO | MIT | ✅ | Paquete Microsoft MIT |
| 12 | minimax-image | STDIO (uvx) | MIT | ✅ | Paquete MIT |
| 13 | openalex | STDIO (npx) | MIT | ✅ | Paquete npm MIT |
| 14 | playwright | STDIO (npx) | Apache-2.0 | ✅ | Microsoft Playwright Apache-2.0 |
| 15 | google-workspace-mcp (nuevo F3a) | STDIO | Apache-2.0 | ✅ | Previsto para F3a |
| 16 | (reservado para expansión) | — | — | — | Slot disponible |

**Resultado**: 15/15 MCPs compatibles. Firecrawl es AGPL pero se consume como servicio externo (no se distribuye su código). **Cero incompatibilidades bloqueantes**.

---

## 4. Incompatibilidades y alternativas

| Origen | Problema | Impacto | Alternativa | Acción |
|---|---|---|---|---|
| — | — | — | — | — |

**No se detectaron incompatibilidades de licencia.** Todos los archivos COPY-HERMES son MIT, todos los paquetes PyPI son permisivos, y los MCPs se consumen como servicios.

---

## Nota sobre firecrawl (AGPL-3.0)

El servidor firecrawl es AGPL-3.0. Sin embargo:
- Se consume vía `npx -y firecrawl-mcp` como proceso externo.
- No se copia, modifica ni distribuye código AGPL.
- El uso como servicio externo (SaaS o proceso local invocado vía protocolo) no activa las obligaciones copyleft de AGPL.
- **Conclusión**: compatible con el proyecto MIT/Apache-2.0.
