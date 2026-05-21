"""DerSimonianLairdMetaAnalyzer — spec 007 T094 (WS-C, FR-C05).

Clase concreta (sin Protocol — YAGNI). Implementa el metodo
DerSimonian-Laird de efectos aleatorios para meta-analisis
usando numpy puro.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy import stats as _stats

from vigilancia_multiagente.domain.evaluation_entities import MetaAnalysisResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DerSimonianLairdMetaAnalyzer:
    """Sin Protocol — calculo puro con numpy.

    aggregate: aplica DerSimonian-Laird random-effects meta-analysis
    sobre una lista de estudios numericos.
    """

    async def aggregate(
        self,
        topic: str,
        numeric_studies: list[dict],
    ) -> MetaAnalysisResult:
        """Agrega estudios via metodo DerSimonian-Laird.

        Args:
            topic: Nombre del fenomeno/topic analizado.
            numeric_studies: Lista de dicts con keys 'effect_size' (float)
                y 'variance' (float, opcional). Si variance no esta presente
                se computa como 1/n.

        Returns:
            MetaAnalysisResult con el agregado.
        """
        if len(numeric_studies) < 2:
            return self._insufficient(topic, numeric_studies)

        effects = []
        variances = []
        study_labels: list[str] = []

        for study in numeric_studies:
            effect = float(study.get("effect_size", 0.0))
            var = float(study.get("variance", 0.0))
            if var <= 0:
                n = max(int(study.get("n", 1)), 1)
                var = 1.0 / n
            effects.append(effect)
            variances.append(var)
            label = str(study.get("label", study.get("id", f"study_{len(study_labels)}")))
            study_labels.append(label)

        effects_arr = np.array(effects, dtype=float)
        variances_arr = np.array(variances, dtype=float)

        # Paso 1: estimacion de efectos fijos (inverse-variance weighting)
        weights_fixed = 1.0 / variances_arr
        fixed_effect = float(np.sum(weights_fixed * effects_arr) / np.sum(weights_fixed))

        # Paso 2: Q-statistic (Cochran's Q)
        q_stat = float(np.sum(weights_fixed * (effects_arr - fixed_effect) ** 2))
        k = len(effects)
        df = k - 1
        if df <= 0:
            return self._insufficient(topic, numeric_studies)

        # Q-test p-value (chi2)
        try:
            q_pvalue = float(1.0 - _stats.chi2.cdf(q_stat, df))
        except Exception:
            q_pvalue = 1.0

        # Paso 3: I^2 (heterogeneidad)
        i_squared = 0.0 if q_stat <= df else min(1.0, (q_stat - df) / q_stat)

        # Paso 4: Tau^2 (DerSimonian-Laird estimator)
        sum_w = float(np.sum(weights_fixed))
        sum_w2 = float(np.sum(weights_fixed**2))
        denominator = sum_w - (sum_w2 / sum_w)
        tau2 = 0.0 if denominator <= 0 or q_stat <= df else max(0.0, (q_stat - df) / denominator)

        # Paso 5: random-effects weights y consensus
        weights_random = 1.0 / (variances_arr + tau2)
        consensus_value = float(np.sum(weights_random * effects_arr) / np.sum(weights_random))

        # Effect size range
        effect_min = float(np.min(effects_arr))
        effect_max = float(np.max(effects_arr))

        # Outliers: studies cuyo effect_size esta fuera de 2*SD del random-effects mean
        weighted_var = 1.0 / np.sum(weights_random)
        se_random = float(np.sqrt(weighted_var))
        outliers: list[str] = []
        if se_random > 0:
            lower = consensus_value - 2.0 * se_random
            upper = consensus_value + 2.0 * se_random
            for label, effect in zip(study_labels, effects, strict=True):
                if effect < lower or effect > upper:
                    outliers.append(label)

        return MetaAnalysisResult(
            topic=topic,
            studies_count=k,
            effect_size_range=(round(effect_min, 4), round(effect_max, 4)),
            consensus_value=round(consensus_value, 4),
            i_squared=round(i_squared, 4),
            q_test_pvalue=round(q_pvalue, 4),
            outliers=outliers,
        )

    @staticmethod
    def _insufficient(topic: str, numeric_studies: list[dict]) -> MetaAnalysisResult:
        effects = [float(s.get("effect_size", 0.0)) for s in numeric_studies]
        if effects:
            effect_min = min(effects)
            effect_max = max(effects)
            consensus = float(np.mean(effects)) if len(effects) > 1 else (effects[0] if effects else 0.0)
        else:
            effect_min = effect_max = consensus = 0.0
        return MetaAnalysisResult(
            topic=topic,
            studies_count=len(numeric_studies),
            effect_size_range=(round(effect_min, 4), round(effect_max, 4)),
            consensus_value=round(consensus, 4),
            i_squared=0.0,
            q_test_pvalue=1.0,
            outliers=[],
        )
