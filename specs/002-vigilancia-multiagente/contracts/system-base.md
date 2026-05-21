---
version: 1.0.0
---

# System Base — Reglas Globales de Agentes

Este documento es la fuente canónica única para reglas globales de comportamiento de agentes. Todas las ramas lo referencian. Ningún branch overlay puede redefinir estas reglas.

---

## 1) Global Rules (Tool Usage)

1. Cada agente ejecuta herramientas MCP en el orden definido en `agent-governance.md` (matriz agente→skill).
2. Si una herramienta falla tras agotar reintentos, el agente debe pasar a la siguiente herramienta en el orden. No debe detener la investigación.
3. El timeout por tool se define en la matriz MCP. Si se excede, se considera fallo y se reintenta según política de retry.
4. Sustitución automática: `none` — no se sustituyen herramientas entre proveedores. Si todas las herramientas fallan, la rama se marca como `FAILED`.

## 2) Safety Limits

1. **Validación de URLs**: Toda URL obtenida de herramientas MCP debe pasar por `validate_external_url()` antes de almacenarse.
2. **Límite de profundidad**: Máximo 5 iteraciones por rama (configurable vía `depth_limit` en `global_constraints`).
3. **Aislamiento de sesión**: Ningún agente puede leer o escribir datos de una sesión diferente a la suya.
4. **Protección de inyección**: El `user_query` nunca se interpola directamente en comandos del sistema. Solo se pasa como campo estructurado en llamadas MCP.

## 3) Error Handling

1. Errores de tool MCP: reintentar según política de retry, luego marcar error y continuar con siguiente herramienta.
2. Errores de red/HTTP: reintentar con backoff, luego falla la iteración actual.
3. Errores de validación (payload sin `url`, confianza fuera de rango): fallo inmediato sin reintento.
4. Errores de embedding: omitir embedding para esa iteración, no detener la rama.
5. Todas las ramas deben completar con `errors: list[str]` — nunca lanzar excepción no capturada.

## 4) Output Style

1. **Formato**: JSON estructurado con campos `findings[]`, `sources[]`, `confidence`, `needs_follow_up`, `next_query`.
2. **Confianza**: `float` entre 0.0 y 1.0. Valores < 0.6 deben incluir `next_query` concreto.
3. **Fuentes**: Cada `finding` debe referenciar al menos un `source` vía `source_ids`.
4. **Trazabilidad**: Cada iteración incluye `latency_ms` y `attempt_count` para telemetría.

## 5) Model Behavior

*Esta sección aplica cuando se use MiniMax u otro LLM directamente. Actualmente el flujo activo es MCP tool execution, no MiniMax.*

1. **Temperature**: 0.3 (balance entre precisión y creatividad).
2. **Max tokens**: 100000 por respuesta.
3. **Stop sequences**: ninguno.
4. **Formato de mensajes**: `system` → `user` → `assistant` (estándar OpenAI-compatible).
5. **Tool calling**: `auto` con todas las tools disponibles para la rama.

## 6) Embedding Configuration (Activo)

1. **Proveedor activo**: Gemini Embedding 2 (`gemini-embedding-2`).
2. **Dimensiones**: 768.
3. **Batch size**: 16 documentos por llamada.
4. **Umbral de duplicado semántico**: `similarity > 0.999` para considerar duplicado.
5. **Umbral de soporte**: `similarity > 0.7` para relación de soporte entre hallazgos.
