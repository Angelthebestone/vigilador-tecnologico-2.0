"""Filtro de calidad de fuente *antes* de extraer.

Hoy se gasta tokens y embeddings extrayendo de todo lo que el MCP devuelve,
incluido SEO-spam, contenido duplicado o paywalls sin cuerpo. Este gate
descarta lo de baja señal a la entrada, no a la salida: el source_scorer ya
mide reputación de dominio para filtrar al final — aquí se usa también como
filtro de admisión.
"""

from __future__ import annotations

from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer

# Frases típicas de paywall/consent/anti-bot: si el contenido es básicamente
# esto, no hay sustancia que extraer.
_LOW_SIGNAL_MARKERS: tuple[str, ...] = (
    "subscribe to continue",
    "create a free account",
    "enable javascript",
    "verifying you are human",
    "access denied",
    "403 forbidden",
    "are you a robot",
    "accept all cookies to continue",
)
# Por debajo de esta reputación de dominio + contenido pobre => descartar.
_MIN_DOMAIN_SCORE = 0.35
_MIN_CONTENT_CHARS = 120


class SourceQualityGate:
    def __init__(self) -> None:
        self._scorer = SourceScorer()

    def accept(self, url: str, content: str) -> bool:
        """True si vale la pena extraer de esta fuente.

        Rechaza si: contenido demasiado corto, marcadores de paywall/anti-bot,
        o dominio de baja reputación con contenido pobre.
        """
        text = (content or "").strip()
        if len(text) < _MIN_CONTENT_CHARS:
            return False

        lowered = text[:600].lower()
        if any(marker in lowered for marker in _LOW_SIGNAL_MARKERS):
            return False

        domain_score = self._scorer.score(url)
        return not (domain_score < _MIN_DOMAIN_SCORE and len(text) < 400)

    def filter_records(
        self, records: list[dict], url_key: str = "url", text_key: str = "content"
    ) -> list[dict]:
        """Filtra una lista de resultados crudos quedándose con los de señal."""
        return [
            r for r in records if self.accept(str(r.get(url_key, "")), str(r.get(text_key, "")))
        ]
