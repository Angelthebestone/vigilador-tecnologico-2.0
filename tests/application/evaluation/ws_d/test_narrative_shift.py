"""T128: Test VaderNarrativeShiftDetector.

Serie temporal 12 meses con shift de tono -> detecta cambio de narrativa.
"""

from datetime import datetime, timedelta

import pytest

from vigilancia_multiagente.application.evaluation.analytics.vader_narrative_shift import (
    VaderNarrativeShiftDetector,
)


@pytest.fixture
def detector():
    return VaderNarrativeShiftDetector(
        window_days=90, z_score_threshold=1.0, min_samples=3
    )


@pytest.fixture
def twelve_month_timeline_with_shift():
    now = datetime.now()
    timeline = []

    # Months 1-6: positive sentiment
    positive_texts = [
        "This breakthrough technology is revolutionary and promising",
        "Excellent results show great potential for the future",
        "Innovative approach leads to outstanding performance improvements",
        "Remarkable advances in the field are truly impressive",
        "Game changing discovery opens new possibilities",
        "Major breakthrough that will transform the industry",
    ]
    for i, text in enumerate(positive_texts):
        timeline.append((now - timedelta(days=30 * (12 - i)), text))

    # Months 7-12: negative sentiment
    negative_texts = [
        "Serious limitations and concerns about the technology",
        "Disappointing results show major flaws in the approach",
        "Problematic issues raise doubts about viability",
        "Critical failures suggest the technology is not ready",
        "Troubling evidence of fundamental problems emerging",
        "Worst case scenario confirms the approach is failing",
    ]
    for i, text in enumerate(negative_texts):
        timeline.append((now - timedelta(days=30 * (6 - i)), text))

    return timeline


@pytest.mark.asyncio
async def test_detects_narrative_shift(detector, twelve_month_timeline_with_shift):
    shifts = await detector.detect(
        "AI Technology", twelve_month_timeline_with_shift
    )
    assert len(shifts) >= 1, "Should detect at least one narrative shift"

    shift = shifts[0]
    assert shift.topic == "AI Technology"
    assert shift.sentiment_pre > shift.sentiment_post, (
        "Pre-sentiment should be higher than post-sentiment"
    )
    assert shift.change_magnitude > 0


@pytest.mark.asyncio
async def test_returns_empty_for_insufficient_data(detector):
    shifts = await detector.detect("test", [])
    assert shifts == []

    single = await detector.detect("test", [(datetime.now(), "some text")])
    assert single == []


@pytest.mark.asyncio
async def test_detects_positive_to_negative_shift(detector):
    now = datetime.now()
    timeline = [
        (now - timedelta(days=200), "This is excellent and wonderful progress"),
        (now - timedelta(days=180), "Great results from the amazing research team"),
        (now - timedelta(days=150), "Outstanding breakthrough in the field"),
        (now - timedelta(days=120), "Fantastic development for the industry"),
        (now - timedelta(days=90), "Good progress continues to be made"),
        (now - timedelta(days=60), "This is terrible and problematic situation"),
        (now - timedelta(days=30), "Bad outcomes from the failing approach"),
        (now, "Worst results ever seen in this research area"),
    ]
    shifts = await detector.detect("Test Tech", timeline)
    assert len(shifts) >= 1
