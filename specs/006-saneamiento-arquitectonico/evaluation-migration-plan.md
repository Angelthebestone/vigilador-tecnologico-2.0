# Evaluation Module Migration Plan

## Summary

| Component | LOC | Consumidores | Destino | Prioridad |
|-----------|-----|-------------|---------|-----------|
| `source_scorer.py` | 156 | evidence_linker, dependencies, finding_impact_scorer, source_quality_gate | ACTIVE (fusionado) | - |
| `branch_kpi_service.py` | 25 | approve_research_usecase, dependencies | MIGRAR a spec 007 | MEDIA |
| `golden_cases_runner.py` | 16 | dependencies | MIGRAR a spec 007 | BAJA |
| `prompt_regression_service.py` | 22 | dependencies | MIGRAR a spec 007 | BAJA |
| `confidence_calibrator.py` | 90 | ninguno | LEGACY | BAJA |
| `causal_timeline.py` | 121 | report_synthesizer | ACTIVE | - |
| `claim_polarity.py` | 45 | orchestrator_service, adversarial_critic, contradiction_analyzer | ACTIVE | - |
| `contradiction_analyzer.py` | 80 | report_synthesizer | ACTIVE | - |
| `finding_impact_scorer.py` | 101 | report_synthesizer | ACTIVE | - |
| `hype_detector.py` | 163 | report_synthesizer, research_outputs | ACTIVE | - |
| `obsolescence_detector.py` | 54 | research_outputs | ACTIVE | - |
| `weak_signal_detector.py` | 184 | report_synthesizer | ACTIVE | - |
| `_markdown.py` | 17 | weak_signal_detector, causal_timeline, contradiction_analyzer | ACTIVE | - |

## Criteria for Classification

- **ACTIVE**: tiene consumidores activos en el pipeline principal (orquestación, fusión, API routes). No necesita migración inmediata.
- **LEGACY**: sin consumidores activos fuera de `evaluation/`. Mantener por referencia pero deprecado. Elegible para eliminación post-spec-007.
- **MIGRATE**: funcionalidad que pertenece conceptualmente a spec 007 (observabilidad, QA, testing). Mantener stubs de compatibilidad hasta migración completa.

## Detailed Assessment

### 1. `source_scorer.py` — ACTIVE
- **Consumidores**: `evidence_linker.py` (línea 1), `dependencies.py` (línea 20, `SourceScorerService`), `finding_impact_scorer.py` (línea 14), `source_quality_gate.py` (línea 16)
- **Análisis**: Dos clases en un archivo — `SourceScorer` (snapshot sync) y `SourceScorerService` (transactional async). El snapshot scorer ya está fusionado en T022. El transactional service se inyecta desde `dependencies.py`. Separar clases podría mejorar claridad pero no es urgente.
- **Recomendación**: Mantener como está. No migrar a spec 007.

### 2. `branch_kpi_service.py` — MIGRATE (prioridad MEDIA)
- **Consumidores**: `approve_research_usecase.py` (línea 12), `dependencies.py` (línea 15)
- **Análisis**: Mide KPIs (coverage, precision, latency, cost) por rama de investigación. Es un componente de observabilidad/monitoreo, no de evaluación de hallazgos. Pertenece más a spec 007 (métricas y monitoreo).
- **Recomendación**: Migrar a spec 007. Reemplazar inyección en `dependencies.py` con el nuevo servicio de métricas de spec 007.
- **Alternativa**: Si spec 007 no cubre KPIs, refactorizar como adapter del sistema de observabilidad.

### 3. `golden_cases_runner.py` — MIGRATE (prioridad BAJA)
- **Consumidores**: `dependencies.py` (línea 16)
- **Análisis**: Runner de casos de prueba golden. Es infraestructura de testing/QA, no parte del pipeline de producción. Su lugar es spec 007 (testing y validación).
- **Recomendación**: Migrar a spec 007 como parte del framework de pruebas de regresión. Stub `GoldenCasesRunner` simple en `dependencies.py` mientras tanto.

### 4. `prompt_regression_service.py` — MIGRATE (prioridad BAJA)
- **Consumidores**: `dependencies.py` (línea 17-19)
- **Análisis**: Evaluación de regresión de prompts por rama. Similar a golden_cases_runner, pertenece a infraestructura de QA/validación de spec 007.
- **Recomendación**: Migrar a spec 007 junto con golden_cases_runner.

### 5. `confidence_calibrator.py` — LEGACY (prioridad BAJA)
- **Consumidores**: Ninguno.
- **Análisis**: Calibración estadística de confianza basada en feedback. Sin consumidores en ningún módulo del proyecto. Lógica potencialmente útil pero no integrada.
- **Recomendación**: Mantener como referencia. Si spec 007 no lo retoma, eliminar post-spec-007.
- **Alternativa**: Si se reactiva, integrar como pipeline post-fusión en `report_synthesizer`.

### 6. `causal_timeline.py` — ACTIVE
- **Consumidores**: `report_synthesizer.py` (línea 6)
- **Análisis**: Construye líneas de tiempo causales a partir de findings. Usa `_markdown.py` para renderizado. Integrado en el reporte final.
- **Recomendación**: Mantener. No migrar.

### 7. `claim_polarity.py` — ACTIVE
- **Consumidores**: `orchestrator_service.py` (línea 5), `adversarial_critic.py` (línea 94, import diferido), `contradiction_analyzer.py` (línea 12)
- **Análisis**: Heurísticas compartidas de solapamiento y polaridad. Es el componente más compartido del módulo — tres consumidores en distintas capas.
- **Recomendación**: Mantener. Es el ejemplo de código compartido que el resto de evaluation/ debería seguir.

### 8. `contradiction_analyzer.py` — ACTIVE
- **Consumidores**: `report_synthesizer.py` (línea 7-10)
- **Análisis**: Detecta contradicciones entre findings usando `claim_polarity`. Renderiza sección de disputas. Integrado en reporte.
- **Recomendación**: Mantener. No migrar.

### 9. `finding_impact_scorer.py` — ACTIVE
- **Consumidores**: `report_synthesizer.py` (línea 10)
- **Análisis**: Jerarquiza findings por impacto (autoridad × novedad × convergencia). Depende de `source_scorer.py`. Integrado en reporte.
- **Recomendación**: Mantener. No migrar.

### 10. `hype_detector.py` — ACTIVE
- **Consumidores**: `report_synthesizer.py` (línea 11), `research_outputs.py` (línea 24)
- **Análisis**: Detecta exageración mediática e infiere madurez TRL. Usado tanto en reportes como en API directa.
- **Recomendación**: Mantener. No migrar.

### 11. `obsolescence_detector.py` — ACTIVE
- **Consumidores**: `research_outputs.py` (línea 25)
- **Análisis**: Detecta señales de obsolescencia tecnológica. Expuesto vía endpoint de API.
- **Recomendación**: Mantener. No migrar.

### 12. `weak_signal_detector.py` — ACTIVE
- **Consumidores**: `report_synthesizer.py` (línea 12)
- **Análisis**: Detecta temas emergentes con poca presencia. Usa `_markdown.py` para renderizado. Integrado en reporte.
- **Recomendación**: Mantener. No migrar.

### 13. `_markdown.py` — ACTIVE
- **Consumidores**: `weak_signal_detector.py` (línea 14), `causal_timeline.py` (línea 11), `contradiction_analyzer.py` (línea 11)
- **Análisis**: Helper interno de renderizado markdown. Tres consumidores dentro de evaluation/. Solo uso interno.
- **Recomendación**: Mantener. No migrar. Si crece, considerar mover a `application/fusion/`.

## Deprecation Timeline

### Fase 4 (actual) — Auditoría
- [x] Añadir comentarios `# STATUS` y `# DEPRECATED` a cada archivo
- [x] Documentar plan de migración
- [ ] Notificar a consumidores de MIGRATE components sobre cambio futuro

### spec 007 — Migración
- [ ] Migrar `branch_kpi_service.py` → módulo de observabilidad/monitoreo
- [ ] Migrar `golden_cases_runner.py` → framework de testing/QA
- [ ] Migrar `prompt_regression_service.py` → framework de testing/QA
- [ ] Actualizar imports en `dependencies.py` para apuntar a nuevos módulos

### Post-007 — Limpieza
- [ ] Eliminar `confidence_calibrator.py` si spec 007 no lo retomó
- [ ] Eliminar stubs de compatibilidad de componentes MIGRATE
- [ ] Eliminar comentarios `# STATUS` y `# DEPRECATED` de todos los archivos

## Graph de Dependencias Internas

```
_markdown.py (ACTIVE)
  └── causal_timeline.py (ACTIVE)
  └── contradiction_analyzer.py (ACTIVE)
  └── weak_signal_detector.py (ACTIVE)

claim_polarity.py (ACTIVE)
  └── orchestrator_service.py (consumer externo)
  └── adversarial_critic.py (consumer externo)
  └── contradiction_analyzer.py (mismo módulo)

source_scorer.py (ACTIVE)
  └── evidence_linker.py (consumer externo)
  └── finding_impact_scorer.py (mismo módulo)
  └── source_quality_gate.py (consumer externo)

confidence_calibrator.py (LEGACY) → sin dependencias entrantes

branch_kpi_service.py (MIGRATE)
golden_cases_runner.py (MIGRATE)
prompt_regression_service.py (MIGRATE)
hype_detector.py (ACTIVE)
obsolescence_detector.py (ACTIVE)
finding_impact_scorer.py (ACTIVE)
```

## Resumen de Acciones Tomadas

- 13 archivos auditados y etiquetados con comentarios `# STATUS`
- 3 componentes marcados como MIGRATE (branch_kpi_service, golden_cases_runner, prompt_regression_service)
- 1 componente marcado como LEGACY (confidence_calibrator)
- 9 componentes marcados como ACTIVE (source_scorer, causal_timeline, claim_polarity, contradiction_analyzer, finding_impact_scorer, hype_detector, obsolescence_detector, weak_signal_detector, _markdown)
- Plan de migración creado en este documento
