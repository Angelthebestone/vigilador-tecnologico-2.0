"""T125: Test SklearnAgglomerativeConvergenceDetector.

Corpus AI+bio con embeddings temporales -> 1 cluster de convergencia.
"""

from datetime import datetime, timedelta

import pytest

from vigilancia_multiagente.application.evaluation.analytics.agglomerative_convergence import (
    SklearnAgglomerativeConvergenceDetector,
)


@pytest.fixture
def detector():
    return SklearnAgglomerativeConvergenceDetector(
        n_clusters=2, window_days=365
    )


@pytest.fixture
def ai_bio_embeddings():
    now = datetime.now()
    embeddings = []
    # AI domain vectors
    for i in range(5):
        embeddings.append((
            "AI",
            [0.1, 0.2, 0.3, 0.4 + i * 0.01],
            now - timedelta(days=30 * i),
        ))
    # Bio domain vectors
    for i in range(5):
        embeddings.append((
            "BIO",
            [0.15, 0.25, 0.35, 0.45 + i * 0.01],
            now - timedelta(days=30 * i),
        ))
    # Unrelated domain (should form separate cluster)
    for i in range(3):
        embeddings.append((
            "CHEM",
            [0.9, 0.8, 0.7, 0.6 + i * 0.01],
            now - timedelta(days=30 * i),
        ))
    return embeddings


@pytest.mark.asyncio
async def test_detects_convergence_between_ai_and_bio(detector, ai_bio_embeddings):
    clusters = await detector.detect(ai_bio_embeddings)
    assert len(clusters) >= 1, "Should detect at least one convergence cluster"

    # Should find a cluster mixing AI and Bio
    has_mixed = any(
        "AI" in c.domains and "BIO" in c.domains
        for c in clusters
    )
    assert has_mixed, "Should detect AI-Bio convergence cluster"


@pytest.mark.asyncio
async def test_returns_empty_for_insufficient_data(detector):
    clusters = await detector.detect([])
    assert clusters == []

    single = await detector.detect([("AI", [0.1, 0.2], datetime.now())])
    assert single == []


@pytest.mark.asyncio
async def test_growth_trend_in_recent_clusters(detector):
    now = datetime.now()
    recent = (now - timedelta(days=10), [0.1, 0.2])
    old = (now - timedelta(days=400), [0.1, 0.2])

    embeddings = [
        ("AI", [0.1, 0.2], old[0]),
        ("BIO", [0.15, 0.25], old[0]),
        ("AI", [0.11, 0.21], recent[0]),
        ("BIO", [0.16, 0.26], recent[0]),
        ("BIO", [0.17, 0.27], recent[0]),
    ]
    clusters = await detector.detect(embeddings)
    if clusters:
        assert all(c.growth_trend != 0 for c in clusters)
