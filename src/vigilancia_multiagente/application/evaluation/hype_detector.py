# STATUS: ACTIVE — consumers: report_synthesizer, research_outputs (HypeDetector.analyze, infer_from_branch_results, render_section)
# Spec 007 T101: _infer_maturity usa SCurveProjection cuando disponible.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vigilancia_multiagente.application.evaluation.calibration.isotonic_calibrator import (
        IsotonicConfidenceCalibrator,
    )

from vigilancia_multiagente.domain.evaluation_entities import SCurveProjection

# Technology Readiness Level bands inferred from the relative weight of
# research / patent / funding / prototype signals. Mirrors the NASA TRL scale
# collapsed into the four phases relevant to technology watch.
_TRL_LABELS: dict[str, str] = {
    "research": "TRL 1-3 · investigación básica",
    "validation": "TRL 4-6 · validación y prototipos",
    "commercialization": "TRL 7-9 · comercialización",
    "unknown": "TRL desconocido",
}

# Spec 007 T036: calibrador isotonico opcional (IsotonicConfidenceCalibrator).
# Cuando es None (flag WS-E off), se usa un ratio sustancial simple como
# fallback.
_CALIBRATOR: IsotonicConfidenceCalibrator | None = None
# Para inferir el ratio se necesita un "techo" relativo de substance que la
# curva isotonica conoce. Usamos un techo robusto observado historicamente
# (4 senales * ~50 hits cada una). Si en prod se observa un techo mayor,
# se ajusta sin riesgo (la curva clipea a [0, 1]).
_SUBSTANCE_CEILING = 200.0


def set_isotonic_calibrator(calibrator: IsotonicConfidenceCalibrator | None) -> None:
    """Wiring punto-libre para que dependencies.py inyecte el calibrator.

    Mantiene el HypeDetector sin tocar su constructor publico (cero ruptura
    en consumidores) y respeta YAGNI: solo se sobreescribe cuando WS-E activo.
    """
    global _CALIBRATOR
    _CALIBRATOR = calibrator


@dataclass(slots=True)
class HypeReport:
    tech: str
    hype_ratio: float = 0.0
    verdict: str = "unknown"
    signals: dict[str, int] = field(default_factory=dict)
    analysis: str = ""
    trl_phase: str = "unknown"
    trl_label: str = "TRL desconocido"
    maturity_analysis: str = ""


class HypeDetector:
    # Spec 007 T101: SCurveProjection opcional para inferir madurez
    _s_curve_projection: SCurveProjection | None = None

    def set_s_curve_projection(self, proj: SCurveProjection | None) -> None:
        self._s_curve_projection = proj

    async def analyze(
        self,
        tech_name: str,
        arxiv_papers: list | None = None,
        exa_companies: list | None = None,
        firecrawl_prototypes: list | None = None,
        serper_patents: list | None = None,
    ) -> HypeReport:
        report = HypeReport(tech=tech_name)
        signals: dict[str, int] = {}

        if arxiv_papers is not None:
            signals["academic_papers"] = len(arxiv_papers)
        if exa_companies is not None:
            signals["companies_with_funding"] = len(exa_companies)
        if firecrawl_prototypes is not None:
            signals["working_prototypes"] = len(firecrawl_prototypes)
        if serper_patents is not None:
            signals["patents"] = len(serper_patents)

        report.signals = signals

        if not signals:
            report.hype_ratio = 0.0
            report.verdict = "insufficient_data"
            report.analysis = (
                f"Connect MCP providers (arxiv, exa, firecrawl, serper) to analyze {tech_name}"
            )
            return report

        substance = sum(signals.values())
        # Spec 007 T036: el ratio se deriva de la curva calibrada empirica
        # (IsotonicConfidenceCalibrator.calibrate) en vez de la heuristica
        # la heuristica por division entera. La verdict se deriva del hype_ratio
        # calibrado vs umbrales fijos mas abajo (>0.7 exagerada, >0.3 real).
        # Cuando no hay calibrator (WS-E off), se usa un ratio sustancial
        # simple como fallback.
        calibrator = _CALIBRATOR
        if calibrator is not None:
            try:
                normalized = min(1.0, substance / _SUBSTANCE_CEILING)
                calibrated = await calibrator.calibrate(normalized)
                # hype_ratio = 1 - calibrated_substance_credibility
                report.hype_ratio = round(max(0.0, min(1.0, 1.0 - calibrated)), 2)
            except Exception:
                report.hype_ratio = round(substance / (substance + 200), 2)
        else:
            report.hype_ratio = round(substance / (substance + 200), 2)

        if report.hype_ratio > 0.7:
            report.verdict = "exagerada"
            report.analysis = (
                f"{tech_name} appears overhyped: {substance} substance signals vs estimated buzz"
            )
        elif report.hype_ratio > 0.3:
            report.verdict = "real"
            report.analysis = f"{tech_name} shows substantive signals ({substance} evidence points)"
        else:
            report.verdict = "real"
            report.analysis = f"{tech_name} appears grounded in real research/companies"

        s_curve = getattr(self, '_s_curve_projection', None)
        self._infer_maturity(report, signals, s_curve_projection=s_curve)
        return report

    @staticmethod
    def _infer_maturity(
        report: HypeReport,
        signals: dict[str, int],
        s_curve_projection: SCurveProjection | None = None,
    ) -> None:
        """Triangula la fase de madurez (TRL).

        Spec 007 T101: cuando SCurveProjection esta presente, deriva TRL
        de growth_rate e inflection_year; sino fallback a reglas if/else actuales.
        """
        if s_curve_projection is not None and s_curve_projection.r_squared > 0.5:
            _infer_from_s_curve(report, s_curve_projection)
            return

        # Fallback a heuristicas originales
        papers = signals.get("academic_papers", 0)
        companies = signals.get("companies_with_funding", 0)
        prototypes = signals.get("working_prototypes", 0)
        patents = signals.get("patents", 0)

        total = papers + companies + prototypes + patents
        if total == 0:
            report.trl_phase = "unknown"
            report.trl_label = _TRL_LABELS["unknown"]
            report.maturity_analysis = "Sin señales para inferir madurez."
            return

        research_weight = papers / total
        market_weight = (companies + patents) / total
        proto_weight = prototypes / total

        if market_weight >= 0.5:
            phase = "commercialization"
            detail = (
                f"{companies} empresas + {patents} patentes dominan sobre "
                f"{papers} papers: tecnología en comercialización."
            )
        elif proto_weight >= 0.25 or (market_weight >= 0.25 and research_weight < 0.6):
            phase = "validation"
            detail = (
                f"{prototypes} prototipos y señales de mercado emergentes "
                f"frente a {papers} papers: fase de validación."
            )
        else:
            phase = "research"
            detail = (
                f"{papers} papers dominan ({research_weight:.0%} de las señales) "
                f"con poca tracción comercial: investigación temprana."
            )

        report.trl_phase = phase
        report.trl_label = _TRL_LABELS[phase]
        report.maturity_analysis = detail


def _infer_from_s_curve(report: HypeReport, proj: SCurveProjection) -> None:
    """Deriva TRL de los parametros de la curva-S (spec 007 T101)."""
    growth = proj.growth_rate
    inflection = proj.inflection_year
    now = 2026

    if growth <= 0.001:
        phase = "unknown"
        detail = f"Crecimiento casi nulo (k={growth:.4f}), no se puede inferir TRL."
    elif growth < 0.3:
        if inflection > now + 5:
            phase = "research"
            detail = (
                f"Crecimiento lento (k={growth:.4f}), punto de inflexion en {inflection}. "
                f"Tecnologia en fase de investigacion basica."
            )
        else:
            phase = "validation"
            detail = (
                f"Crecimiento moderado (k={growth:.4f}), punto de inflexion en {inflection}. "
                f"Tecnologia en validacion/prototipos."
            )
    elif growth < 0.7:
        phase = "validation"
        detail = (
            f"Crecimiento sostenido (k={growth:.4f}), punto de inflexion en {inflection}. "
            f"Tecnologia en fase de validacion con traccion creciente."
        )
    else:
        phase = "commercialization"
        detail = (
            f"Crecimiento alto (k={growth:.4f}), punto de inflexion en {inflection}. "
            f"Tecnologia en comercializacion o madurez."
        )

    report.trl_phase = phase
    report.trl_label = _TRL_LABELS.get(phase, _TRL_LABELS["unknown"])
    report.maturity_analysis = detail

    @classmethod
    def infer_from_branch_results(cls, branch_results) -> HypeReport:
        """Estima el TRL a partir de los findings ya recolectados, sin llamar
        a proveedores en vivo (igual de determinístico que el resto de
        analizadores de inteligencia).

        Cuenta señales por palabras clave en los statements: papers /
        prototipos / funding / patentes.
        """
# STATUS: ACTIVE

        signal_keywords: dict[str, tuple[str, ...]] = {
            "academic_papers": ("paper", "study", "research", "arxiv", "preprint"),
            "working_prototypes": ("prototype", "demo", "beta", "pilot", "deployment"),
            "companies_with_funding": ("funding", "raised", "series", "investment", "startup"),
            "patents": ("patent", "ip ", "trademark"),
        }
        signals: dict[str, int] = dict.fromkeys(signal_keywords, 0)
        for result in branch_results:
            for finding in result.findings:
                text = finding.statement.lower()
                for key, keywords in signal_keywords.items():
                    if any(kw in text for kw in keywords):
                        signals[key] += 1

        report = HypeReport(tech="", signals=signals)
        cls._infer_maturity(report, signals)
        return report

    @staticmethod
    def render_section(report: HypeReport) -> str:
        if report.trl_phase == "unknown":
            return ""
        return "\n".join(
            [
                "## Madurez tecnológica",
                "",
                f"- **{report.trl_label}**",
                f"- {report.maturity_analysis}",
                "",
            ]
        )
