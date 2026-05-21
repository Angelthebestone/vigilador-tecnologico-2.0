"""Clustering jerarquico para detectar convergencia tecnologica temprana.

Clase concreta (sin Protocol — YAGNI). Usa sklearn AgglomerativeClustering
sobre embeddings + ventana temporal deslizante. Output: ConvergenceCluster[]
con deteccion de convergencia entre dominios.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast
from uuid import uuid4

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from vigilancia_multiagente.domain.evaluation_entities import ConvergenceCluster


class SklearnAgglomerativeConvergenceDetector:
    """Detecta convergencia entre dominios via clustering jerarquico."""

    def __init__(
        self,
        n_clusters: int = 4,
        distance_threshold: float | None = None,
        window_days: int = 180,
        min_growth_window: int = 90,
    ) -> None:
        self._n_clusters = n_clusters
        self._distance_threshold = distance_threshold
        self._window_days = window_days
        self._min_growth_window = min_growth_window

    async def detect(
        self,
        embeddings: list[tuple[str, list[float], datetime]],
    ) -> list[ConvergenceCluster]:
        if len(embeddings) < 3:
            return []

        terms, vectors, timestamps = zip(*embeddings)
        matrix = np.array(vectors)

        model = AgglomerativeClustering(  # type: ignore[call-overload]
            n_clusters=None if self._distance_threshold else self._n_clusters,
            distance_threshold=self._distance_threshold,
            metric="cosine",
            linkage="average",
        )
        labels = model.fit_predict(matrix)

        clusters_map: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            clusters_map.setdefault(int(label), []).append(idx)

        now = datetime.now()
        window_start = now - timedelta(days=self._window_days)

        results: list[ConvergenceCluster] = []
        for label, indices in clusters_map.items():
            if len(indices) < 2:
                continue
            cluster_terms = [terms[i] for i in indices]
            cluster_times = [timestamps[i] for i in indices]
            cluster_vectors = matrix[list(indices)]

            # Domain diversity signal: more domains within cluster = convergence
            unique_terms = list(set(cluster_terms))
            if len(unique_terms) < 2:
                continue

            # Growth trend: slope of term frequency over time
            recent = sum(1 for t in cluster_times if t >= window_start)
            past = len(cluster_times) - recent
            growth_trend = float(recent - past) / max(len(cluster_times), 1)

            # Temporal diversity: if all vectors have the same timestamp
            first_detected = min(cluster_times)

            results.append(
                ConvergenceCluster(
                    id=uuid4(),
                    domains=unique_terms[:8],
                    representative_terms=unique_terms[:5],
                    growth_trend=growth_trend,
                    first_detected=first_detected,
                )
            )

        results.sort(key=lambda c: c.growth_trend, reverse=True)
        return results
