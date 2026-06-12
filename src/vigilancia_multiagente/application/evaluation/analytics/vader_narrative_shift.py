"""Deteccion de cambios de narrativa via VADER sentiment + ventanas deslizantes.

Clase concreta (sin Protocol — YAGNI). Usa vaderSentiment para analizar
sentimiento en ventanas temporales de 90 dias y detecta change-points
con z-score.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from vigilancia_multiagente.domain.evaluation_entities import NarrativeShift


class VaderNarrativeShiftDetector:
    """Detecta cambios de narrativa mediante VADER + ventanas deslizantes."""

    def __init__(
        self,
        window_days: int = 90,
        z_score_threshold: float = 1.5,
        min_samples: int = 5,
    ) -> None:
        self._window_days = window_days
        self._z_score_threshold = z_score_threshold
        self._min_samples = min_samples
        self._analyzer = SentimentIntensityAnalyzer()

    async def detect(
        self,
        topic: str,
        timeline: list[tuple[datetime, str]],
    ) -> list[NarrativeShift]:
        if len(timeline) < self._min_samples:
            return []

        scored: list[tuple[datetime, float, str]] = []
        for ts, text in timeline:
            scores = self._analyzer.polarity_scores(text)
            scored.append((ts, scores["compound"], text))

        scored.sort(key=lambda x: x[0])

        window = timedelta(days=self._window_days)
        shifts: list[NarrativeShift] = []

        for i in range(len(scored)):
            window_start = scored[i][0]
            window_end = window_start + window

            pre = [s for s in scored if s[0] < window_start]
            post = [s for s in scored if window_start <= s[0] <= window_end]

            if len(pre) < self._min_samples or len(post) < self._min_samples:
                continue

            pre_scores = [s[1] for s in pre]
            post_scores = [s[1] for s in post]

            mean_pre = sum(pre_scores) / len(pre_scores)
            mean_post = sum(post_scores) / len(post_scores)
            change_magnitude = abs(mean_post - mean_pre)

            std_pre = (
                math.sqrt(sum((s - mean_pre) ** 2 for s in pre_scores) / len(pre_scores))
                if len(pre_scores) > 1
                else 0.001
            )
            z_score = (mean_post - mean_pre) / std_pre if std_pre > 0 else 0

            if abs(z_score) >= self._z_score_threshold:
                shifts.append(
                    NarrativeShift(
                        topic=topic,
                        window_start=pre[0][0],
                        window_end=window_end,
                        sentiment_pre=round(mean_pre, 4),
                        sentiment_post=round(mean_post, 4),
                        change_point=window_start,
                        change_magnitude=round(change_magnitude, 4),
                    )
                )

        shifts.sort(key=lambda s: s.change_magnitude, reverse=True)
        return shifts[:10]
