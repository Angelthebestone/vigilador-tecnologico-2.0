from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass(slots=True)
class ObsolescenceSignal:
    tech: str
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendation: str = ""


class ObsolescenceDetector:
    async def analyze(
        self,
        tech_name: str,
        brave_news_results: list | None = None,
        exa_company_results: list | None = None,
    ) -> ObsolescenceSignal:
        signal = ObsolescenceSignal(tech=tech_name)
        signals_found: list[str] = []

        if brave_news_results:
            if len(brave_news_results) < 3:
                signals_found.append(f"Low news coverage: only {len(brave_news_results)} recent mentions")
            else:
                signals_found.append(f"Stable news coverage: {len(brave_news_results)} mentions found")

        if exa_company_results:
            signals_found.append(f"{len(exa_company_results)} companies/alternatives detected")

        if not brave_news_results and not exa_company_results:
            signals_found.append(f"Monitoring {tech_name} — connect MCP providers for deeper analysis")
            signal.confidence = 0.3
        else:
            decline_signals = sum(1 for s in signals_found if "low" in s.lower() or "only" in s.lower())
            signal.confidence = max(0.1, 0.7 - (decline_signals * 0.2))

        signal.signals = signals_found
        if signal.confidence >= 0.6:
            signal.recommendation = f"{tech_name} appears stable. Continue monitoring."
        elif signal.confidence >= 0.3:
            signal.recommendation = f"{tech_name} shows early decline signals. Monitor quarterly."
        else:
            signal.recommendation = f"Insufficient data for {tech_name}. Enable MCP providers."

        return signal
