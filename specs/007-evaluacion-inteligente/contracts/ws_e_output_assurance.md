# Contracts: WS-E Output Assurance

WS-E corre **fuera** del pipeline de rama. Se ejecuta despues de
`ReportSynthesizer` como un gate sobre el `FinalReport`.

---

## `GoldenCaseRepository` (`domain/ports/golden_case_repository.py`)

```python
class GoldenCaseRepository(Protocol):
    async def list_active(self) -> list[GoldenCase]: ...
    async def record_run(self, run: GoldenCaseRun) -> None: ...
    async def recent_runs(self, case_id: UUID, limit: int = 20) -> list[GoldenCaseRun]: ...
```

Adapter: `PostgresGoldenCaseRepository`.

## `GoldenCaseRunner` (`domain/ports/golden_case_runner.py`)

```python
class GoldenCaseRunner(Protocol):
    async def run_case(self, case: GoldenCase) -> GoldenCaseRun: ...
    async def run_all(self) -> list[GoldenCaseRun]: ...
```

Adapter: `OrchestratorGoldenCaseRunner` (invoca el flujo completo en
modo sandbox sin escribir produccion).

## `StakeholderSimulator` (`domain/ports/stakeholder_simulator.py`)

```python
class StakeholderSimulator(Protocol):
    async def simulate(
        self,
        report: FinalReport,
        stakeholder: str,
    ) -> StakeholderSimulation: ...
```

Adapter: `LlmStakeholderSimulator` (un prompt por tipo de stakeholder,
templates en `prompts/evaluation/stakeholder_<type>.txt`).

## `FalsificationProber` (`domain/ports/falsification.py`)

```python
class FalsificationProber(Protocol):
    async def probe(
        self,
        conclusion: str,
    ) -> list[FalsificationScenario]: ...
```

Adapter: `LlmFalsificationProber`. Si retorna lista vacia, la conclusion
se marca `falsifiable=False`.

## Auditor de sesgos — clase concreta (sin Protocol)

`BiasAuditor` vive en
`application/evaluation/audit/bias_auditor.py`. **No tiene Protocol** —
calculo puro sobre metadatos ya recolectados (autores, paises), sin
llamadas externas. YAGNI.

```python
class BiasAuditor:
    async def audit(
        self,
        report: FinalReport,
        thresholds: BiasThresholds,
    ) -> BiasAudit: ...
```

## Escritor de trazas forenses — clase concreta (sin Protocol)

`JsonbForensicTraceWriter` vive en
`application/evaluation/forensic/jsonb_trace_writer.py`. **No tiene
Protocol** — escribe en columna JSONB de `findings` via repositorio
inyectado del 006. YAGNI.

```python
class JsonbForensicTraceWriter:
    def __init__(self, findings_repository: FindingRepository) -> None: ...

    async def record_step(
        self,
        claim_id: UUID,
        step: TraceStep,
        confidence: float,
    ) -> None: ...

    async def finalize(self, claim_id: UUID) -> ForensicTrace: ...
```

## Calibrador de confianza — clase concreta (sin Protocol)

`IsotonicConfidenceCalibrator` vive en
`application/evaluation/calibration/isotonic_calibrator.py`. **No tiene
Protocol** — usa `sklearn.isotonic.IsotonicRegression` + repositorio
inyectado, sin frontera externa. YAGNI.

```python
class IsotonicConfidenceCalibrator:
    def __init__(self, curve_repository: CalibrationCurveRepository) -> None: ...

    async def calibrate(self, raw_score: float) -> float: ...
    async def retrain(self, runs: list[GoldenCaseRun]) -> CalibrationCurve: ...
    async def active_curve(self) -> CalibrationCurve: ...
```

---

## Quality gate

`ReportQualityGate` (en `application/evaluation/report_quality_gate.py`)
orquesta los Protocols de arriba. Recibe el `FinalReport` recien
sintetizado, ejecuta en orden:

1. `ForensicTraceWriter.finalize` por cada claim.
2. `BiasAuditor.audit` — si `critical_bias_detected` -> bloquea entrega.
3. `FalsificationProber.probe` por cada conclusion.
4. `StakeholderSimulator.simulate` para los 4 perfiles.
5. `ConfidenceCalibrator.calibrate` ajusta confianzas finales.

Outputs anexados al `FinalReport.assurance` (nuevo campo).
