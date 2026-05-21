# Quickstart: Sistema de Evaluacion Inteligente (Spec 007)

Demuestra el flujo end-to-end con un golden case representativo. Verifica
que los cinco workstreams cooperan y que el quality gate de WS-E aprueba
o bloquea el reporte segun corresponda.

---

## Pre-requisitos

1. Spec 006 completada y activa (puertos de dominio funcionando).
2. Variables de entorno adicionales en `.env` (todas son **opcionales**;
   sin ellas el sistema arranca como hoy, comportamiento identico al
   pre-007). Para activar los workstreams:
   ```
   # Flags (default: false — el sistema preserva su funcionamiento actual)
   VT_EVAL_WS_A_ENABLED=true
   VT_EVAL_WS_B_ENABLED=true
   VT_EVAL_WS_C_ENABLED=true
   VT_EVAL_WS_D_ENABLED=true
   VT_EVAL_WS_E_ENABLED=true

   # Claves externas WS-A (default: vacias — los adapters degradan)
   VT_OPENALEX_EMAIL=ops@example.com   # polite pool, recomendado
   VT_GOOGLE_FACTCHECK_API_KEY=...     # opcional, fallback a Wikidata
   VT_RETRACTION_WATCH_CSV_URL=https://example.com/retractions.csv
   ```
3. Migracion `alembic upgrade head` aplicada (crea las 6 tablas nuevas).
4. Suite inicial de golden cases sembrada (al menos 3):
   ```bash
   python scripts/seed_golden_cases.py --suite minimum
   ```

---

## Escenario: "Tecnologias de IA generativa en quimica computacional"

### Paso 1 — Lanzar sesion

```bash
curl -X POST http://localhost:8000/research/start \
  -H "Content-Type: application/json" \
  -d '{"query": "Estado actual de los LLMs aplicados a descubrimiento de materiales y prediccion de propiedades quimicas"}'
```

El sistema dispara la rama `AVANCES` (entre otras) que ahora incluye
los nuevos pipeline steps de WS-A, WS-B, WS-C, WS-D.

### Paso 2 — Observar WS-B en accion (en logs)

```
INFO  data_intelligence_step  hybrid_search candidates=147 -> top_k=10
INFO  data_intelligence_step  dedup similarity=0.94 fused=23 sources -> 9
INFO  data_intelligence_step  language_distribution en=0.71 zh=0.21 es=0.08
INFO  data_intelligence_step  ai_probability mean=0.18 high(>0.7)=2 sources
INFO  data_intelligence_step  effective_freshness avg=0.81 (raw 0.86, penalty applied to 2)
INFO  consensus_dispute       claim="Los LLMs superan a DFT" support=4 oppose=2
```

### Paso 3 — Observar WS-A enriqueciendo findings

```
INFO  source_quality_step  author=Smith J. h_index=42 retractions=0
INFO  source_quality_step  conflict_of_interest funder=NVIDIA risk=high
INFO  source_quality_step  fact_check status=verified db=wikidata
INFO  source_quality_step  retraction_check passed=9 retracted=0
```

### Paso 4 — Observar WS-C (analisis profundo)

```
INFO  deep_analysis_step  s_curve r2=0.87 inflection_year=2024
INFO  deep_analysis_step  implicit_assumption finding=f8 severity=warning
INFO  deep_analysis_step  meta_analysis i2=0.34 consensus=0.78
INFO  deep_analysis_step  counterfactual scenarios=3
```

### Paso 5 — Observar WS-D (senales estrategicas)

```
INFO  strategic_signals_step  convergence_cluster=AI+ChemEng growth=0.31
INFO  strategic_signals_step  collaboration_network nodes=87 bubbles=1
INFO  strategic_signals_step  narrative_shift topic=alphafold magnitude=0.46
INFO  strategic_signals_step  patenting_gap subdomain=protein_design class=blue_ocean
```

### Paso 6 — Quality gate (WS-E)

```
INFO  report_quality_gate  forensic_trace claims=12 complete=12
INFO  report_quality_gate  bias_audit geographic=us=0.62 critical=false
INFO  report_quality_gate  falsification scenarios_per_conclusion=3.2 falsifiable=true
INFO  report_quality_gate  stakeholder_simulation investor=2.1k chars regulator=1.8k...
INFO  report_quality_gate  calibrator raw=0.72 calibrated=0.65 curve_id=...
INFO  report_quality_gate  RESULT pass=true
```

Si el gate hubiera bloqueado, el endpoint `GET /research/{id}/report`
devolveria `409 Conflict` con detalle de la causa.

---

## Verificacion ejecutable: golden case run

```bash
python scripts/run_golden_cases.py --case alphafold-baseline
```

Salida esperada:
```
Running case: alphafold-baseline
Expected findings: 8  Actual: 8 (match)
Expected confidence: 0.74  Actual: 0.71  Delta: -0.03
Calibration delta < 0.05 -> PASS
```

---

## Verificacion empirica (criterios de exito del spec)

- **SC-A01**: la columna `author_reputation` del response anota `h_index`,
  `retraction_count`, `affiliation_type`, `total_citations`.
- **SC-B01**: comparar `recall@10` con flag `VT_EVAL_WS_B_ENABLED=false`
  vs `true` sobre el corpus de prueba (script
  `scripts/benchmark_recall.py`).
- **SC-E06**: `grep -r "buzz = max(0, substance // 2)" src/` retorna
  vacio. La columna `calibrated_confidence` de `findings` se actualiza
  con cada `golden_case_run`.

---

## Rollback

Para revertir al sistema anterior sin redespliegue:

```bash
export VT_EVAL_WS_A_ENABLED=false
export VT_EVAL_WS_B_ENABLED=false
export VT_EVAL_WS_C_ENABLED=false
export VT_EVAL_WS_D_ENABLED=false
export VT_EVAL_WS_E_ENABLED=false
systemctl restart vigilancia-api
```

El comportamiento previo (heuristicas) sigue presente bajo las flags;
no hay perdida de datos.
