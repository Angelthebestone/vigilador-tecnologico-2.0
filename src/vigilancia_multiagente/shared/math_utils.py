"""Shared math helpers (no layer dependencies)."""

from __future__ import annotations

from math import sqrt


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding vectors must have the same size")
    numerator = sum(x * y for x, y in zip(left, right, strict=True))
    left_norm = sqrt(sum(x * x for x in left))
    right_norm = sqrt(sum(y * y for y in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
