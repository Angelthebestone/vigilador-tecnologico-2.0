# Runbook: Rollback de Workstreams de Evaluacion (Spec 007)

## Objetivo

Procedimiento para deshabilitar workstreams individuales del Sistema de
Evaluacion Inteligente sin afectar el resto del sistema. Cada workstream
tiene un flag `bool` en `settings.py` que lo desactiva en origen.

---

## 1. Deshabilitar Workstream

### WS-A (Source Quality)

```bash
# En .env o variable de entorno
VT_EVAL_WS_A_ENABLED=false
```

Efecto: el `SourceQualityAdapter` retorna `None`. El pipeline de evaluacion
salta la verificacion de fuentes entrantes.

### WS-B (Data Intelligence)

```bash
VT_EVAL_WS_B_ENABLED=false
```

Efecto: `DataIntelligenceAdapter` retorna `None`. No se genera analisis
estadistico ni deteccion de outliers sobre los datos recopilados.

### WS-C (Deep Analysis)

```bash
VT_EVAL_WS_C_ENABLED=false
```

Efecto: `DeepAnalysisAdapter` retorna `None`. El pipeline no ejecuta
proyeccion S-Curve ni analisis de madurez. Los endpoints `/maturity`
y `/obsolescence` caen a comportamiento legacy (HypeDetector heuristico).

### WS-D (Strategic Signals)

```bash
VT_EVAL_WS_D_ENABLED=false
```

Efecto: `StrategicSignalsAdapter` retorna `None`. No se detectan NarrativeShift
ni ConvergenceClusters. El endpoint `/obsolescence` omite el analisis de
narrativa.

### WS-E (Output Assurance)

```bash
VT_EVAL_WS_E_ENABLED=false
```

Efecto: `OutputAssuranceAdapter` retorna `None`. El `ReportQualityGate` no
se ejecuta. No se bloquean reportes por sesgo critico (HTTP 409 no se
dispara por este motivo).

---

## 2. Criterios de Canary

Antes de activar un WS en produccion, validar:

| Criterio | Metodo |
|----------|--------|
| 0 errores basedpyright | `python -m basedpyright src/vigilancia_multiagente/` |
| 0 violaciones capas | `python scripts/check-layer-imports.py` |
| Pasa pytest completo | `pytest` (flags false) |
| Pasa golden suite | `pytest` (flags true + golden cases) |
| Benchmark latencia | `python scripts/benchmark_latency.py` — degradacion P95 < 50% |
| Healthcheck endpoints | `python scripts/healthcheck.py` |

**Canary**: activar WS en 1 instancia (5% trafico) durante 24h. Sin errores
ni degradacion > umbrales, escalar a 50% por 24h, luego 100%.

---

## 3. Plan de Recuperacion

### Incidente: Degradacion de latencia

1. Deshabilitar el WS que causa la degradacion (set flag a `false` y
   reiniciar contenedor).
2. Verificar que P95 vuelve a linea base con `scripts/benchmark_latency.py`.
3. Abrir issue con el reporte de benchmark para investigar causa raiz.

### Incidente: Error en pipeline de evaluacion

1. Identificar el WS fallido por los logs (`StepError` con `workstream`).
2. Deshabilitar ese WS.
3. Verificar que el pipeline completa exitosamente sin el WS.
4. Abrir issue con el stack trace y contexto del error.

### Incidente: Falso positivo / Falso negativo en golden suite

1. Congelar el WS afectado (flag `false`).
2. Revisar golden cases y threshold del WS.
3. Corregir y validar contra golden suite completa antes de reactivar.

---

## 4. Monitoreo Post-Rollback

- Metricas Prometheus: `evaluation_step_duration_seconds`,
  `evaluation_step_errors_total` por workstream.
- Logs estructurados: buscar `StepResult.failure_details` no vacio.
- Healthcheck: endpoints de evaluacion retornan 200 con el WS
  deshabilitado (respuesta indica `evaluation_skipped: true`).
