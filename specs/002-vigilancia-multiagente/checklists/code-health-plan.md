# Plan: Dead Code, Verificaciones Innecesarias y System Base por Agente

**Created**: 2026-05-12  
**Input**: Análisis de código muerto + revisión de system base + MCP tool audit

---

## Hallazgos Clave

### 1. Límite de tokens incorrecto

**Archivo**: `specs/002-vigilancia-multiagente/contracts/system-base.md:45`
```markdown
2. **Max tokens**: 2048 por respuesta.
```

Este valor se incluye en el `ComposedPrompt` de **todos los agentes**. A 2048 tokens, cualquier agente que haga investigación compleja colapsa. MiniMax M2.7 soporta 128k tokens de contexto.

**Fix**: Cambiar a `100000` (o al menos `32768`). Este valor es informativo en el canal MCP actual — el LLM que ejecuta las tools no lo usa como límite técnico sino como guía de comportamiento. Pero si algún día se activa MiniMax directamente, será el límite real.

---

### 2. Bug: variable indefinida en `prompt_composer.py`

**Archivo**: `src/.../application/governance/prompt_composer.py:117`
```python
branch_type=overlay.branch_type if overlay is not None else bt
```
`bt` es una variable **indefinida** — causaría `NameError` si `overlay` fuera `None`. Además `overlay` es un parámetro **obligatorio** (no `Optional`), así que el `else` nunca se ejecuta.

**Fix**: Reemplazar el ternario entero por `overlay.branch_type` directamente.

---

## Fase 1: Dead Code Cleanup

### 1.1 Eliminar módulo huérfano: `serper_client.py`

| Archivo | Líneas | Problema |
|---------|--------|----------|
| `src/infra/serper/serper_client.py` | 148 | Módulo completo nunca importado ni referenciado |

**Fix**: Eliminar el archivo. Serper no es MCP, y si se necesita en el futuro se integra vía un adaptador MCP real, no como REST directo.

### 1.2 Limpiar re-exports huérfanos

| Archivo | Problema |
|---------|----------|
| `src/infra/llm/__init__.py` | Re-exporta `MiniMaxClient`, `MiniMaxMessage`, `MiniMaxResponse`, `MiniMaxToolCall` — nadie importa desde `infra.llm` |

**Fix**: Eliminar `__init__.py` o dejarlo vacío.

### 1.3 Eliminar función no usada

| Archivo | Función | Línea |
|---------|---------|-------|
| `src/domain/session_state.py` | `is_terminal()` | 36-37 |

**Fix**: Eliminar la función. `VALID_TRANSITIONS` y `ensure_transition()` se usan, `is_terminal()` no.

### 1.4 Eliminar DTOs/Modelos huérfanos

| Archivo | Clases | Líneas |
|---------|--------|--------|
| `src/api/routes/research_governance.py` | `GraphPathRequest`, `GraphSearchRequest`, `GraphCentralityDTO`, `GraphClusterDTO`, `GraphAnalyticsResponse`, `GraphPathResponse`, `GraphSearchHitDTO`, `GraphSearchResponse` | 19-72 |

**Fix**: Eliminar todas estas clases. La funcionalidad de grafo vive en `research_outputs.py`, no aquí.

### 1.5 Eliminar imports no usados

| Archivo | Imports a eliminar |
|---------|-------------------|
| `src/api/dependencies.py:31` | `MCPAuthMode`, `MCPProviderConfig`, `MCPTransport`, `RetryPolicy` |
| `src/api/routes/research_approve.py:1` | `Path` from `pathlib` |
| `src/api/routes/research_outputs.py:27` | `VectorRecord` |
| `src/api/routes/research_governance.py:8,11,12` | `branch_kpi_service`, `golden_cases_runner`, `plan_repository` |
| `src/api/routes/system_base.py:14` | `branch_coordinator` |
| `src/application/graph/knowledge_graph_service.py:6` | `atan2` from `math` |
| `tests/conftest.py:20,23,25` | `BranchKPIService`, `SessionEvent`, `format_sse`, `ReportSynthesizer` |
| `tests/test_e2e_flow.py:3` | `MemorySessionRepository` |

### 1.6 Eliminar fixture no usada

| Archivo | Fixture | Línea |
|---------|---------|-------|
| `tests/conftest.py` | `fake_db` | 253-254 |

**Fix**: Eliminar la fixture (tests usan `FakeDatabase` directamente).

### 1.7 Variables no usadas

| Archivo | Variable | Línea | Nota |
|---------|----------|-------|------|
| `src/application/execution/branch_coordinator.py` | `undirected_edges` | 106 | Se asigna y se borra con `del`. Reemplazar `adjacency, undirected_edges = ...` por `adjacency, _ = ...` |

---

## Fase 2: Verificaciones Innecesarias

### 2.1 Bug: variable indefinida en `prompt_composer.py`

```python
# Antes (roto):
branch_type=overlay.branch_type if overlay is not None else bt
# Después:
branch_type=overlay.branch_type
```

### 2.2 Verificación redundante en `contract_loader.py`

El método `load_prompt_template()` llama a `self.ensure_contract_file()` y `load_branch_overlay()` también lo hace. Hay doble verificación de existencia del archivo en la misma llamada.

**Fix**: Cachear el resultado de `ensure_contract_file()` o eliminar la llamada redundante en `load_prompt_template()`.

### 2.3 Verificación de `system_base_enabled` redundante (YA CORREGIDO)

El fix que hicimos en `dependencies.py` ya eliminó el `if settings.system_base_enabled else None` redundante en cada constructor de agente. Verificar que no hayan quedado residuos similares en otros archivos.

### 2.4 `MCPTransport` case en `provider_registry.py`

La línea 182 verifica `if provider.transport == MCPTransport.STDIO` para validar comandos. Pero los providers STDIO (`brave`, `firecrawl`, `google_scholar`, `arxiv`) no tienen argumentos configurados en `ensure_standard_providers()`. Esto causará error si se intenta ejecutar un provider STDIO sin los argumentos correctos.

**Fix**: Agregar argumentos a los providers STDIO en `ensure_standard_providers()`, o verificar que los argumentos existan antes de ejecutar.

---

## Fase 3: System Base por Agente

### 3.1 Problema actual

Hoy el `PromptComposer.compose()` genera un `ComposedPrompt` que se pasa como campo `composed_prompt` en el payload MCP. Pero el agente (LLM) no recibe instrucciones específicas sobre **cómo usar cada herramienta MCP asignada a su rama**.

Cada agente necesita saber:
- Qué herramientas MCP tiene disponibles (orden, tiempo de espera, reintentos)
- Cuál es su objetivo específico como rama (definido en `BranchOverlay`)
- Cómo interpretar el output de cada herramienta
- Qué hacer cuando una herramienta falla (fallback a la siguiente)
- Cuál es el formato de salida esperado

### 3.2 Solución propuesta

Extender `PromptComposer.compose()` para incluir el **skill matrix** de la rama en el prompt compuesto:

```
[System Base: Global Rules]
[System Base: Tool Usage Policy]
...
---
[Branch Overlay: Objective]
[Branch Overlay: Context]
---
[Skill Matrix: Tools disponibles]
  - tool_1 → timeout X, retry Y, fallback a tool_2
  - tool_2 → timeout X, retry Y, fallback a tool_3
  - tool_3 → timeout X, retry Y, sin fallback (FAILED branch)
---
[User Query]
```

### 3.3 Impacto

| Archivo | Cambio |
|---------|--------|
| `src/application/governance/prompt_composer.py` | Agregar sección "Skill Matrix" al compose |
| `src/application/agents/base.py` | Pasar `policy` (AgentSkillPolicy) a `PromptComposer.compose()` |
| Archivos de overlay de rama | No requieren cambios (el overlay ya tiene do/dont rules) |

### 3.4 Ejemplo de sección agregada

```
## Tools Disponibles (Skill Matrix)

Order de ejecución: brave_web_search → firecrawl_scrape → guess_datetime_url

| Tool | Timeout | Retry | Fallback |
|------|---------|-------|----------|
| brave_web_search | 20s | 2 | firecrawl_scrape |
| firecrawl_scrape | 35s | 1 | guess_datetime_url |
| guess_datetime_url | 15s | 1 | FAIL branch |

Si todas las herramientas fallan, la rama se marca como FAILED.
```

---

## Fase 4: Token Limit

### 4.1 Cambio en `system-base.md`

```diff
- 2. **Max tokens**: 2048 por respuesta.
+ 2. **Max tokens**: 100000 por respuesta (configurable vía VT_SYSTEM_BASE_VERSION).
```

### 4.2 Código dependiente

La sección "Model Behavior" del system base se parsea en `system_base_loader.py:180` (`_parse_model_behavior`). El valor `max_tokens` se almacena en `SystemBase.model_behavior`. Luego se incluye en el prompt compuesto. El cambio de 2048 → 100000 se propaga automáticamente a todos los agentes sin modificar código.

---

## Orden de Implementación

1. **Token limit** (Phase 4) — cambio de 1 línea en `system-base.md`
2. **Bug fix** (Phase 2.1) — variable indefinida en `prompt_composer.py`
3. **Dead code imports** (Phase 1.5) — 15 imports a eliminar en paralelo
4. **Dead code classes** (Phase 1.4) — 8 DTOs a eliminar
5. **Orphaned module** (Phase 1.1) — eliminar `serper_client.py`
6. **Re-exports** (Phase 1.2) — limpiar `infra/llm/__init__.py`
7. **Unused function** (Phase 1.3) — eliminar `is_terminal()`
8. **Unused fixture** (Phase 1.6) — eliminar `fake_db`
9. **Unused variable** (Phase 1.7) — `_` en lugar de `undirected_edges`
10. **Redundant check** (Phase 2.2) — double `ensure_contract_file()`
11. **STDIO args** (Phase 2.4) — argumentos para providers STDIO
12. **System base per agent** (Phase 3) — skill matrix en composed prompt

---

## Paralelización

| Bloque | Tasks | Subagentes |
|--------|-------|------------|
| Token + Bug fix | Fase 4 + 2.1 | 2 en paralelo |
| Imports cleanup | Fase 1.5 (todos los archivos) | 8 subagentes en paralelo |
| Classes + Module | Fase 1.1 + 1.4 | 2 en paralelo |
| Re-exports + Function + Fixture + Variable | Fase 1.2 + 1.3 + 1.6 + 1.7 | 4 en paralelo |
| Redundant check + STDIO args | Fase 2.2 + 2.4 | 2 en paralelo |
| System base per agent | Fase 3 | 1 (más complejo, requiere cambios en 3 archivos) |

**Tests**: `python -m pytest -q` debe pasar después de cada bloque.
