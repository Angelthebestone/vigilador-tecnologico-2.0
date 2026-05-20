"""Líneas de tiempo causales: encadena eventos por relación causal inferida
(paper -> startup -> adquisición) en vez de listarlos solo por fecha, para
mostrar *cómo* evolucionó una tecnología.
"""
# STATUS: ACTIVE — consumer: report_synthesizer (CausalTimelineBuilder.render_section)

from __future__ import annotations

import re
from dataclasses import dataclass, field

from vigilancia_multiagente.application.evaluation._markdown import markdown_section
from vigilancia_multiagente.domain.models import BranchResult

_YEAR_RE = re.compile(r"\b(19[9]\d|20[0-4]\d)\b")

# Tipo de evento inferido por palabras clave. El orden de la tupla define la
# precedencia causal canónica (investigación habilita producto habilita mercado).
_EVENT_KINDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("research", ("paper", "study", "research", "arxiv", "preprint", "investigación")),
    ("prototype", ("prototype", "demo", "beta", "release", "launch", "prototipo")),
    ("funding", ("funding", "raised", "series", "investment", "inversión", "ronda")),
    ("market", ("acquisition", "ipo", "merger", "adquisición", "fusión", "salida")),
    ("regulation", ("regulation", "law", "ban", "compliance", "normativa", "ley")),
)
_KIND_ORDER: dict[str, int] = {kind: i for i, (kind, _) in enumerate(_EVENT_KINDS)}


@dataclass(slots=True)
class TimelineEvent:
    year: int
    kind: str
    statement: str
    branch: str


@dataclass(slots=True)
class CausalLink:
    cause: TimelineEvent
    effect: TimelineEvent
    relation: str


@dataclass(slots=True)
class CausalTimeline:
    events: list[TimelineEvent] = field(default_factory=list)
    links: list[CausalLink] = field(default_factory=list)

    @property
    def has_narrative(self) -> bool:
        return bool(self.links)


class CausalTimelineBuilder:
    """Determinístico (sin LLM): infiere causalidad por tipo de evento +
    proximidad temporal usando la precedencia canónica research->market."""
# STATUS: ACTIVE


    def build(self, branch_results: list[BranchResult], max_gap_years: int = 3) -> CausalTimeline:
        timeline = CausalTimeline()
        for result in branch_results:
            for finding in result.findings:
                year = self._extract_year(finding.statement)
                if year is None:
                    continue
                timeline.events.append(
                    TimelineEvent(
                        year=year,
                        kind=self._classify(finding.statement),
                        statement=finding.statement,
                        branch=result.branch_type.value,
                    )
                )

        timeline.events.sort(key=lambda e: (e.year, _KIND_ORDER.get(e.kind, 99)))
        timeline.links = self._infer_links(timeline.events, max_gap_years)
        return timeline

    @staticmethod
    def _extract_year(text: str) -> int | None:
        match = _YEAR_RE.search(text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _classify(text: str) -> str:
        lowered = text.lower()
        for kind, keywords in _EVENT_KINDS:
            if any(kw in lowered for kw in keywords):
                return kind
        return "event"

    @staticmethod
    def _infer_links(events: list[TimelineEvent], max_gap_years: int) -> list[CausalLink]:
        links: list[CausalLink] = []
        for i, cause in enumerate(events):
            cause_rank = _KIND_ORDER.get(cause.kind)
            if cause_rank is None:
                continue
            for effect in events[i + 1 :]:
                gap = effect.year - cause.year
                if gap < 0 or gap > max_gap_years:
                    continue
                effect_rank = _KIND_ORDER.get(effect.kind)
                if effect_rank is None or effect_rank <= cause_rank:
                    continue  # el efecto debe estar más adelante en la cadena causal
                links.append(
                    CausalLink(
                        cause=cause,
                        effect=effect,
                        relation=f"{cause.kind} → {effect.kind}",
                    )
                )
                break  # un solo efecto inmediato por causa evita explosión combinatoria
        return links

    @staticmethod
    def render_section(timeline: CausalTimeline) -> str:
        body = [
            f"- **{link.cause.year}** ({link.cause.kind}) → "
            f"**{link.effect.year}** ({link.effect.kind}): {link.relation}"
            for link in timeline.links
        ]
        return markdown_section("Trayectoria causal", body)
