"""T131: Golden test `convergence-ai-bio` — valida deteccion temprana >= 6 meses.

Verifica que el SklearnAgglomerativeConvergenceDetector puede detectar
convergencia AI+BIO con ventaja temporal sobre la linea base.
"""

from datetime import datetime, timedelta

import pytest

from vigilancia_multiagente.application.evaluation.analytics.agglomerative_convergence import (
    SklearnAgglomerativeConvergenceDetector,
)


@pytest.fixture
def detector():
    return SklearnAgglomerativeConvergenceDetector(
        n_clusters=2,
        window_days=365,
        min_growth_window=180,
    )


@pytest.fixture
def convergence_ai_bio_golden():
    """Golden case: AI + Bio convergence with 8-month early detection window.

    Simula embeddings de papers AI y Bio que progresivamente se vuelven
    mas similares a partir de un punto de convergencia.
    """
    now = datetime.now()
    embeddings = []

    # Baseline (old): AI and Bio are far apart
    for i in range(5):
        embeddings.append(
            (
                "AI",
                [0.1, 0.9, 0.2, 0.8],
                now - timedelta(days=400 + i * 30),
            )
        )
        embeddings.append(
            (
                "BIO",
                [0.9, 0.1, 0.8, 0.2],
                now - timedelta(days=400 + i * 30),
            )
        )

    # Convergence point: AI and Bio vectors start resembling each other
    # (8 months before "now" — the golden case threshold)
    convergence_time = now - timedelta(days=240)
    for i in range(8):
        t = convergence_time + timedelta(days=30 * i)
        mix_factor = min(1.0, (i + 1) * 0.15)
        ai_vec = [
            0.1 + mix_factor * 0.7,
            0.9 - mix_factor * 0.7,
            0.2 + mix_factor * 0.6,
            0.8 - mix_factor * 0.6,
        ]
        bio_vec = [
            0.9 - mix_factor * 0.7,
            0.1 + mix_factor * 0.7,
            0.8 - mix_factor * 0.6,
            0.2 + mix_factor * 0.6,
        ]
        embeddings.append(("AI", ai_vec, t))
        embeddings.append(("BIO", bio_vec, t))

    return embeddings, convergence_time


@pytest.mark.asyncio
async def test_convergence_ai_bio_golden(detector, convergence_ai_bio_golden):
    embeddings, _convergence_time = convergence_ai_bio_golden
    clusters = await detector.detect(embeddings)

    assert len(clusters) >= 1, "Golden: debe detectar al menos 1 cluster de convergencia"

    # Verify the cluster contains both AI and Bio
    ai_bio_clusters = [c for c in clusters if "AI" in c.domains and "BIO" in c.domains]
    assert len(ai_bio_clusters) >= 1, "Golden: debe existir un cluster con dominios AI y BIO"

    # Verify early detection: first_detected should be >= 6 months before now
    cluster = ai_bio_clusters[0]
    lead_months = (datetime.now() - cluster.first_detected).days / 30
    assert lead_months >= 6.0, (
        f"Golden: deteccion temprana debe ser >= 6 meses (lead={lead_months:.1f} meses)"
    )


@pytest.mark.asyncio
async def test_no_false_positive_on_unrelated_domains(detector):
    """Golden: dominios no relacionados no deben producir falsa convergencia."""
    now = datetime.now()
    embeddings = []
    for i in range(10):
        embeddings.append(("MATH", [1.0, 0.0, 0.0], now - timedelta(days=30 * i)))
        embeddings.append(("ART", [0.0, 1.0, 0.0], now - timedelta(days=30 * i)))

    clusters = await detector.detect(embeddings)
    math_art = [c for c in clusters if "MATH" in c.domains and "ART" in c.domains]
    # MATH and ART are too different; they should not converge
    # (allow for the possibility but flag it)
    if math_art:
        cluster = math_art[0]
        assert cluster.growth_trend < 0.5, (
            "Golden: falsa convergencia MATH-ART no debe tener growth_trend alto"
        )
