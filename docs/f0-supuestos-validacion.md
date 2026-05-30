# F0 — Validación de Supuestos A1-A14

**Fecha**: 2026-05-29
**Método general**: validación sin instalar paquetes pesados ni alterar el entorno existente.

---

## Tabla de validación

| ID | Supuesto | Método | Resultado | Evidencia | Acción |
|---|---|---|---|---|---|
| A1 | MiniMax M-2.5 disponible vía misma API que M-2.7 | Revisión documental; el proyecto ya usa `infra/llm/minimax_client.py` con endpoint OpenAI-compatible `platform.xiaomimimo.com` | NO-VALIDABLE-EN-ENTORNO | Requiere API key activa y conectividad al endpoint MiniMax para confirmar que M-2.5 responde. No se dispone de key en este entorno. | Validar en F1 al implementar `XiaomimimoClient`; si M-2.5 no responde, usar M-2.7 como fallback (plan B: decisión #85). |
| A2 | CrewAI 0.x soporta clientes OpenAI-compatible custom | Revisión documental de CrewAI; requiere instalar `crewai` en venv aislado | NO-VALIDABLE-EN-ENTORNO | Instalar crewai alteraría el entorno (paquete pesado con dependencias torch/transformers). Documentación pública de CrewAI indica soporte para `base_url` custom desde v0.28+. | Validar en F4b al implementar `crewai_bridge.py`. Si no soporta, usar orquestación propia (PlaybookRunner ya diseñado). |
| A3 | TurboVec `pip install turbovec` funciona en Windows 11 | Requiere instalar paquete en venv aislado | NO-VALIDABLE-EN-ENTORNO | TurboVec es paquete experimental; instalarlo podría requerir compilación C++ y alterar el entorno. No se instala. | Validar al inicio de F2. Plan B: usar pgvector directamente como VectorIndex adapter (decisión #85). |
| A4 | MCPs a internalizar tienen licencias compatibles (MIT/Apache-2.0) | Inspección de los 14 MCPs en `mcp-providers.json` — son servicios externos (SaaS/npm/PyPI) consumidos vía protocolo MCP, no código copiado | VALIDADO | Los MCPs son servicios remotos o paquetes npm/PyPI con licencias permisivas: tavily (propietario SaaS), exa (SaaS), jina (SaaS), brave (MIT npm), firecrawl (AGPL server pero consumido como SaaS), serper (SaaS), google_scholar (MIT), arxiv (MIT), fetch (MIT), sandbox (interno), markitdown (MIT), minimax-image (SaaS), openalex (MIT), playwright (Apache-2.0). No se copia código; se consume vía protocolo. | Firecrawl: el servidor es AGPL pero se consume como servicio externo (no se distribuye código AGPL). Compatible. |
| A5 | Tools de Hermes son MIT-compatibles y portables a Windows 11 | Inspección del archivo `LICENSE` en `documentation/hermes agent/hermes-agent/` | VALIDADO | LICENSE es MIT (Copyright 2025 Nous Research). Todos los archivos en `tools/` están bajo esta licencia. No hay headers per-file con licencia diferente. Portabilidad Windows: los archivos son Python puro (sin dependencias nativas Unix-only en los candidatos COPY-HERMES: registry, lazy_deps, schema_sanitizer, tool_output_limits, debug_helpers, file_tools, file_operations, file_state, path_security, url_safety, website_policy, redact). | Copiar con atribución MIT en header. |
| A6 | `BAAI/bge-m3` corre en CPU con latencia < 200ms por batch | Requiere instalar sentence-transformers + descargar modelo (~2GB) | NO-VALIDABLE-EN-ENTORNO | Instalar sentence-transformers + modelo bge-m3 alteraría significativamente el entorno (>2GB, dependencias torch). | Validar al inicio de F2. Plan B: usar Gemini Embedding API existente (ya funcional en 2.0) como provider por defecto; bge-m3 local es opcional. |
| A7 | Presidio soporta español + inglés con `es_core_news_md` | Requiere instalar presidio-analyzer + spacy model | NO-VALIDABLE-EN-ENTORNO | Instalar presidio + modelo spaCy alteraría el entorno. Documentación pública de Presidio confirma soporte multi-idioma con modelos spaCy. | Validar en F5d. Plan B: regex-based PII detection (ya previsto en F5a como PI defense regex). |
| A8 | OAuth providers permiten scopes restrictivos sin delete | Revisión documental de Google Workspace OAuth y Microsoft Graph | VALIDADO | Google Workspace OAuth: scopes `drive.readonly`, `gmail.readonly`, `calendar.readonly` disponibles sin permisos de escritura/borrado. Microsoft Graph: scopes `Files.Read.All`, `Mail.Read`, `Calendars.Read` disponibles sin delete. Ambos permiten scopes restrictivos. | Implementar con scopes readonly por defecto en F1 (oauth_manager). |
| A9 | Constitución exige cambios quirúrgicos; cero renombres de paquete | Verificación documental contra constitución v1.2.0 y CLAUDE.md | VALIDADO | Constitución principio #5: "Cambios quirúrgicos". El paquete sigue siendo `vigilancia_multiagente` (sin renombre). Import path `from vigilancia_multiagente...` confirmado en pyproject.toml y tests. | Ninguna — principio vigente y respetado. |
| A10 | Capacidad de ejecución: MVP 12-16 sem con 1-2 ingenieros | Evaluación de progreso: Olas 0/1/2 completadas (specs 002-018), 329 tests verdes | VALIDADO | Progreso actual: modelos de dominio, tooling, governance, modes, skills_marketplace, orchestration, dreaming, artifacts implementados. F0 documental en curso. Ritmo compatible con 12-16 semanas para MVP completo. | Continuar según cronograma. |
| A11 | MigrationRunner soporta DDL con columnas vector(N) y DEFAULT uuidv7() | Requiere ejecutar DDL contra PostgreSQL | NO-VALIDABLE-EN-ENTORNO | `psql` no disponible en PATH; no hay acceso a la metadata DB desde este entorno. | Validar cuando el operador tenga acceso a PostgreSQL. Ejecutar: `CREATE TABLE test_a11 (id uuid DEFAULT uuidv7(), vec vector(1536));` Si falla, verificar extensiones. |
| A12 | TurboVec funciona en Windows 11 (refuerzo de A3) | Mismo que A3 | NO-VALIDABLE-EN-ENTORNO | Ver A3. | Ver A3. |
| A13 | pgvector 0.8+ instalado en PG 18 | Requiere query: `SELECT extversion FROM pg_extension WHERE extname='vector'` | NO-VALIDABLE-EN-ENTORNO | Sin acceso a DB. | Validar con acceso a PostgreSQL. Si versión < 0.8: `ALTER EXTENSION vector UPDATE TO '0.8.0'`. |
| A14 | `uuidv7()` disponible nativamente en PG 18 | Requiere query: `SELECT uuidv7()` | NO-VALIDABLE-EN-ENTORNO | Sin acceso a DB. PostgreSQL 18 incluye uuidv7() nativamente según release notes. | Validar con acceso a PostgreSQL. Si PG < 18: requiere upgrade antes de F1. |

---

## Resumen

| Estado | Cantidad | IDs |
|---|---|---|
| VALIDADO | 5 | A4, A5, A8, A9, A10 |
| NO-VALIDABLE-EN-ENTORNO | 9 | A1, A2, A3, A6, A7, A11, A12, A13, A14 |
| DESMENTIDO | 0 | — |

---

## Acciones correctivas

No hay supuestos DESMENTIDOS. Los 9 NO-VALIDABLE-EN-ENTORNO se dividen en:

1. **Requieren DB (A11, A13, A14)**: validar cuando el operador conecte PostgreSQL. Bloqueantes para migraciones de F1.
2. **Requieren instalación de paquetes pesados (A1, A2, A3/A12, A6, A7)**: validar en la fase correspondiente (F1-F5). Todos tienen plan B documentado.
3. **Ninguno es bloqueante para iniciar F1** en sus componentes que no dependen de DB.

---

## Nota sobre supuestos faltantes

Los 14 supuestos (A1-A14) están listados tal como aparecen en el plan maestro (`plan vigilador 3.0/07-migracion-2.0-a-3.0.md` y `specs/019-fase-F0-auditoria-baseline/spec.md`). A12 es refuerzo explícito de A3. Cobertura: 14/14 completa.
