"""Detección de señales débiles: temas emergentes que aún casi nadie menciona.

Un tema es señal débil si aparece poco en la sesión actual, estaba ausente en
sesiones previas y no es ruido aislado (aparece en >1 fuente o rama). Detecta
tecnologías antes de que sean tendencia.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

from vigilancia_multiagente.application.evaluation._markdown import markdown_section
from vigilancia_multiagente.domain.models import BranchResult


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    """Stopwords genéricas (en+es) tomadas de spaCy en vez de una lista propia.

    Si spaCy no está instalado degrada a un núcleo mínimo, igual que el patrón
    de carga perezosa de entity_extractor. Los términos de dominio
    (provienen de las focus_queries que genera plan_builder) se añaden siempre.
    """
    domain_terms = {"technology", "signals", "market", "context"}
    try:
        from spacy.lang.en.stop_words import STOP_WORDS as EN_STOP
        from spacy.lang.es.stop_words import STOP_WORDS as ES_STOP
    except ImportError:
        return frozenset(_FALLBACK_STOPWORDS | domain_terms)
    return frozenset(EN_STOP | ES_STOP | domain_terms)


# Núcleo usado solo si spaCy no está instalado: las stopwords >3 chars más
# frecuentes en inglés y español (las de <=3 ya las filtra el largo mínimo).
_FALLBACK_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "they",
        "their",
        "them",
        "would",
        "could",
        "should",
        "have",
        "has",
        "had",
        "been",
        "were",
        "will",
        "what",
        "when",
        "where",
        "which",
        "while",
        "about",
        "into",
        "than",
        "then",
        "these",
        "those",
        "such",
        "more",
        "most",
        "para",
        "con",
        "que",
        "como",
        "por",
        "los",
        "las",
        "del",
        "una",
        "este",
        "esta",
        "estos",
        "estas",
        "sobre",
        "entre",
        "desde",
        "hasta",
        "pero",
        "porque",
        "cuando",
        "donde",
        "muy",
        "más",
        "ser",
        "son",
        "fue",
        "han",
        "hay",
        "sus",
        "esa",
        "ese",
    }
)
# Un término que aparece más que esto ya es tema central, no señal débil.
_SALIENCE_CEILING = 4
# Mínimo de fuentes/ramas distintas para descartar ruido de una sola fuente.
_MIN_SPREAD = 2


@dataclass(slots=True)
class WeakSignal:
    term: str
    occurrences: int
    branch_spread: int
    rationale: str


@dataclass(slots=True)
class WeakSignalReport:
    signals: list[WeakSignal] = field(default_factory=list)

    @property
    def has_signals(self) -> bool:
        return bool(self.signals)


class WeakSignalDetector:
    """No requiere LLM: opera sobre los statements de findings ya recolectados
    y la memoria recurrente que CrossSessionService ya expone."""

    def detect(
        self,
        branch_results: list[BranchResult],
        recurring_entities: list[str] | None = None,
    ) -> WeakSignalReport:
        known = {term.lower() for term in (recurring_entities or [])}
        term_count: Counter[str] = Counter()
        term_branches: dict[str, set[str]] = {}

        for result in branch_results:
            branch = result.branch_type.value
            for finding in result.findings:
                for token in self._tokenize(finding.statement):
                    if token in known:
                        continue  # ya conocido en sesiones previas => no es débil
                    term_count[token] += 1
                    term_branches.setdefault(token, set()).add(branch)

        report = WeakSignalReport()
        for term, count in term_count.items():
            spread = len(term_branches[term])
            if count > _SALIENCE_CEILING:
                continue  # ya es tema central
            if spread < _MIN_SPREAD and count < _MIN_SPREAD:
                continue  # ruido de una sola fuente
            report.signals.append(
                WeakSignal(
                    term=term,
                    occurrences=count,
                    branch_spread=spread,
                    rationale=(
                        f"Emergente: {count} menciones en {spread} rama(s), "
                        f"ausente en investigación previa."
                    ),
                )
            )
        report.signals.sort(key=lambda s: (s.branch_spread, s.occurrences), reverse=True)
        return report

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        stopwords = _stopwords()
        tokens: list[str] = []
        for raw in text.lower().split():
            cleaned = raw.strip(".,;:!?()[]\"'")
            if len(cleaned) > 3 and cleaned not in stopwords and not cleaned.isdigit():
                tokens.append(cleaned)
        return tokens

    @staticmethod
    def render_section(report: WeakSignalReport) -> str:
        body = [f"- **{signal.term}** — {signal.rationale}" for signal in report.signals[:15]]
        return markdown_section("Señales débiles emergentes", body)
