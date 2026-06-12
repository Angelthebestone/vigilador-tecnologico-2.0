"""Helper compartido para renderizar secciones de markdown del reporte."""
# STATUS: ACTIVE — consumers: weak_signal_detector, causal_timeline, contradiction_analyzer

from __future__ import annotations

from collections.abc import Iterable


def markdown_section(title: str, body_lines: Iterable[str]) -> str:
    """Devuelve `## title` + cuerpo, o `""` si el cuerpo está vacío.

    Centraliza el patrón repetido en los analizadores de inteligencia
    (contradicciones, señales débiles, trayectoria causal).
    """
    # STATUS: ACTIVE

    lines = list(body_lines)
    if not lines:
        return ""
    return "\n".join([f"## {title}", "", *lines, ""])
