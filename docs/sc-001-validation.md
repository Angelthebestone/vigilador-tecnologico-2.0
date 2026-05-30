# Validación manual de Success Criteria — spec 009 MVP Foundation

**Feature**: 009-mvp-foundation
**Creado**: 2026-05-29 (Fase 4 — Polish)

Procedimientos de las validaciones que requieren **entorno vivo** (API key Xiaomimimo,
PostgreSQL con pgvector, navegador). Pendientes de ejecución por el operador; aquí queda
el guion reproducible y el espacio para registrar resultados.

Prerequisitos comunes:
- `VT_DATABASE_URL` apuntando a PostgreSQL con `pgvector` instalado.
- `VT_XIAOMIMIMO_API_KEY` válida.
- `VT_EMBEDDING_DIMENSIONS` alineado con el modelo Gemini activo (ver postgres-readiness).
- Backend: `uvicorn vigilancia_multiagente.api.app:app --host 0.0.0.0 --port 8000`.
- Frontend: `npm run dev --prefix frontend`.

---

## SC-001 — Onboarding completable en ≤ 5 min (T059)

**Criterio**: un operador admin completa login → paso 1 (empresa) → paso 2 (LLM provider) en
≤ 5 minutos en un navegador limpio.

Procedimiento:
1. Abrir navegador en modo incógnito (sin localStorage previo). Iniciar cronómetro.
2. Ir a `/enterprise/login`. Login con `admin` / contraseña configurada.
3. Paso 1: completar nombre de empresa, sector, país, departamento, municipio, timezone.
   Enviar.
4. Paso 2: seleccionar proveedor Xiaomimimo, pegar API key, pulsar "Probar conectividad",
   confirmar modelo + latencia, guardar.
5. Detener cronómetro al aterrizar en `/enterprise/tools`.

| Fecha | Tiempo medido | Navegador | Resultado | Notas |
|-------|---------------|-----------|-----------|-------|
| _pendiente_ | | | | |

Persistencia parcial (EC-06): tras completar el paso 1, cerrar la pestaña y reabrir
`/enterprise/onboarding`; debe reanudar en el paso 2 con los datos de empresa conservados
(localStorage `vigilador-onboarding`).

---

## SC-005 — HealthMonitor detecta tool caída en ≤ 90 s (T060)

**Criterio**: con una tool fake que falla deliberadamente, el HealthMonitor marca su estado
`DOWN` en ≤ 90 s.

Procedimiento:
1. Registrar en el `ToolRegistry` una tool fake cuyo `healthcheck()` lance excepción o devuelva
   `status="DOWN"`.
2. Arrancar la app con `VT_HEALTH_MONITOR_ENABLED=true` y `VT_HEALTH_MONITOR_INTERVAL_SEC=30`.
3. Observar `~/.vigilador/audit/healthcheck.log` (líneas JSONL) y la tabla `tool_health`.
4. Medir el tiempo desde el arranque hasta que `status='DOWN'` se persiste.
   Con intervalo 30 s y umbral de circuit breaker 3, el peor caso es ≈ 90 s.

| Fecha | Tiempo a DOWN | Intervalo | Umbral CB | Resultado |
|-------|---------------|-----------|-----------|-----------|
| _pendiente_ | | 30 s | 3 | |

---

## SC-006 — Latencia mediana de `mimo-v2-flash` (T061)

**Criterio**: medir la latencia mediana de respuestas del modelo `mimo-v2-flash` con un batch
de ~10 prompts de ~200 tokens.

Procedimiento:
1. Con `VT_XIAOMIMIMO_API_KEY` configurada, ejecutar 10 llamadas `chat_completion` con prompts
   de ~200 tokens (vía `POST /api/v2/enterprise/onboarding/test-llm` repetido o un script que
   use `XiaomimimoClient`).
2. Registrar la latencia de cada llamada y calcular la mediana.

| Fecha | n | Latencia mediana (ms) | p95 (ms) | Notas |
|-------|---|-----------------------|----------|-------|
| _pendiente_ | 10 | | | |
