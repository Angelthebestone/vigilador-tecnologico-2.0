# STATUS: ACTIVE — consumer: research_outputs (ObsolescenceDetector.analyze)
# Spec 007 T102: cuando SCurveProjection presente con growth_rate < 0,
# reportar obsolescencia con base en cola descendente; sino fallback heuristico.

from __future__ import annotations

from dataclasses import dataclass, field

from vigilancia_multiagente.domain.evaluation_entities import (
    NarrativeShift,
    SCurveProjection,
)


@dataclass(slots=True)
class ObsolescenceSignal:
    tech: str
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendation: str = ""
    s_curve_obsolescence: bool = False  # spec 007 T102
    narrative_obsolescence: bool = False  # spec 007 T123


class ObsolescenceDetector:
    async def analyze(
        self,
        tech_name: str,
        brave_news_results: list | None = None,
        exa_company_results: list | None = None,
        s_curve_projection: SCurveProjection | None = None,  # spec 007 T102
        narrative_shifts: list[NarrativeShift] | None = None,  # spec 007 T123
    ) -> ObsolescenceSignal:
        signal = ObsolescenceSignal(tech=tech_name)

        # spec 007 T123: NarrativeShift con sentimiento negativo creciente
        if narrative_shifts:
            negative = [n for n in narrative_shifts if n.sentiment_post < n.sentiment_pre]
            if negative:
                return self._narrative_obsolescence(tech_name, negative)

        # spec 007 T102: SCurveProjection con growth_rate < 0 -> obsolescencia
        if s_curve_projection is not None and s_curve_projection.growth_rate < 0:
            return self._s_curve_obsolescence(tech_name, s_curve_projection)

        # Fallback heuristico (comportamiento original)
        signals_found: list[str] = []

        if brave_news_results:
            if len(brave_news_results) < 3:
                signals_found.append(
                    f"Low news coverage: only {len(brave_news_results)} recent mentions"
                )
            else:
                signals_found.append(
                    f"Stable news coverage: {len(brave_news_results)} mentions found"
                )

        if exa_company_results:
            signals_found.append(f"{len(exa_company_results)} companies/alternatives detected")

        if not brave_news_results and not exa_company_results:
            signals_found.append(
                f"Monitoring {tech_name} — connect MCP providers for deeper analysis"
            )
            signal.confidence = 0.3
        else:
            decline_signals = sum(
                1 for s in signals_found if "low" in s.lower() or "only" in s.lower()
            )
            signal.confidence = max(0.1, 0.7 - (decline_signals * 0.2))

        signal.signals = signals_found
        if signal.confidence >= 0.6:
            signal.recommendation = f"{tech_name} appears stable. Continue monitoring."
        elif signal.confidence >= 0.3:
            signal.recommendation = f"{tech_name} shows early decline signals. Monitor quarterly."
        else:
            signal.recommendation = f"Insufficient data for {tech_name}. Enable MCP providers."

        return signal

    @staticmethod
    def _narrative_obsolescence(
        tech_name: str, shifts: list[NarrativeShift]
    ) -> ObsolescenceSignal:
        max_mag = max(s.change_magnitude for s in shifts)
        avg_delta = sum(s.sentiment_pre - s.sentiment_post for s in shifts) / len(shifts)
        confidence = min(0.85, 0.4 + max_mag)
        return ObsolescenceSignal(
            tech=tech_name,
            narrative_obsolescence=True,
            signals=[
                f"Narrative shift toward negative sentiment detected: "
                f"{len(shifts)} shift(s), max magnitude={max_mag:.4f}, "
                f"avg delta={avg_delta:.4f}",
                *[f"  {s.topic}: pre={s.sentiment_pre:.3f}, post={s.sentiment_post:.3f}"
                  for s in shifts[:3]],
            ],
            confidence=round(confidence, 2),
            recommendation=(
                f"{tech_name} shows growing negative sentiment across "
                f"{len(shifts)} narrative shift(s). "
                f"Sentiment declining by avg {avg_delta:.3f}. "
                f"Monitor closely for reputational risk."
            ),
        )

    @staticmethod
    def _s_curve_obsolescence(
        tech_name: str, proj: SCurveProjection
    ) -> ObsolescenceSignal:
        decline_magnitude = abs(proj.growth_rate)
        confidence = min(0.9, 0.5 + decline_magnitude)
        return ObsolescenceSignal(
            tech=tech_name,
            s_curve_obsolescence=True,
            signals=[
                f"S-Curve decline detected: growth_rate={proj.growth_rate:.4f}, "
                f"inflection_year={proj.inflection_year}, "
                f"ceiling={proj.ceiling:.2f}"
            ],
            confidence=round(confidence, 2),
            recommendation=(
                f"{tech_name} shows S-Curve decline (rate={proj.growth_rate:.4f}). "
                f"Technology may be approaching obsolescence. "
                f"Consider monitoring替代 technologies."
            ),
        )
