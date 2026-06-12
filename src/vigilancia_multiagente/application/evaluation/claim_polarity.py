"""Heurística compartida de solapamiento y polaridad entre afirmaciones.

Antes vivía duplicada en OrchestratorService, CrossSessionService y el
ContradictionAnalyzer. Una sola definición evita que las tres versiones
diverjan.
"""
# STATUS: ACTIVE — consumers: orchestrator_service, adversarial_critic, contradiction_analyzer

from __future__ import annotations

_NEGATORS: frozenset[str] = frozenset(
    {
        "not",
        "never",
        "no",
        "cannot",
        "doesn't",
        "don't",
        "won't",
        "isn't",
        "aren't",
        "fails",
        "unable",
        "sin",
        "nunca",
        "tampoco",
    }
)

# Mínimo de palabras compartidas para considerar que dos claims hablan de lo
# mismo (umbral validado en OrchestratorService._claims_match).
_MIN_WORD_OVERLAP = 3


def claims_overlap(statement_a: str, statement_b: str) -> bool:
    """True si ambos enunciados comparten suficiente vocabulario."""
    words_a = set(statement_a.lower().split())
    words_b = set(statement_b.lower().split())
    return len(words_a & words_b) >= _MIN_WORD_OVERLAP


def polarity_conflict(statement_a: str, statement_b: str) -> bool:
    """True si uno niega y el otro afirma (polaridad opuesta)."""
    # STATUS: ACTIVE

    neg_a = bool(set(statement_a.lower().split()) & _NEGATORS)
    neg_b = bool(set(statement_b.lower().split()) & _NEGATORS)
    return neg_a != neg_b
