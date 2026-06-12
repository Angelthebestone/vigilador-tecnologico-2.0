"""Chunk dedup (Spec 021 F2.C T062).

Two-stage dedup:

1. **Exact** — SHA-256 hash of the normalized text. Drops verbatim copies.
2. **Near-duplicate** — Jaccard similarity on shingle sets, threshold
   ``0.85``. Catches re-formatted versions of the same content.

KISS: no MinHash sketches; for the MVP corpus size (≤100k chunks/tenant)
naive Jaccard is fine. If we need to scale, MinHash drops in here behind
the same ``DedupResult`` interface.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

_SHINGLE_SIZE = 4  # tokens per shingle
_DEFAULT_NEAR_THRESHOLD = 0.85


@dataclass(frozen=True)
class DedupResult:
    """Result of de-duping a list of chunks."""

    kept: list[object] = field(default_factory=list)  # list[Chunk]
    duplicates: list[tuple[int, int]] = field(default_factory=list)
    """Pairs ``(removed_chunk_id, kept_chunk_id)`` for audit."""


def dedup_chunks(
    chunks: Sequence[object],
    *,
    near_threshold: float = _DEFAULT_NEAR_THRESHOLD,
) -> DedupResult:
    """Remove exact + near-duplicate chunks. Order-preserving.

    The first occurrence of any duplicate group is kept; subsequent
    matches are reported in :attr:`DedupResult.duplicates`.
    """
    kept: list[object] = []
    seen_hashes: dict[str, int] = {}
    seen_shingles: list[tuple[int, frozenset[str]]] = []
    duplicates: list[tuple[int, int]] = []

    for chunk in chunks:
        text = getattr(chunk, "text", "")
        chunk_id = getattr(chunk, "chunk_id", -1)
        digest = _normalized_hash(text)
        if digest in seen_hashes:
            duplicates.append((chunk_id, seen_hashes[digest]))
            continue
        shingles = _shingles(text)
        near_match = _find_near(shingles, seen_shingles, near_threshold)
        if near_match is not None:
            duplicates.append((chunk_id, near_match))
            continue
        seen_hashes[digest] = chunk_id
        seen_shingles.append((chunk_id, shingles))
        kept.append(chunk)

    return DedupResult(kept=kept, duplicates=duplicates)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    # Strip punctuation + collapse whitespace + lowercase.
    no_punct = re.sub(r"[^\w\s]", " ", text or "")
    return re.sub(r"\s+", " ", no_punct).strip().lower()


def _normalized_hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def _shingles(text: str) -> frozenset[str]:
    """Word-level k-shingles of size ``_SHINGLE_SIZE``."""
    tokens = _normalize(text).split()
    if len(tokens) < _SHINGLE_SIZE:
        return frozenset(tokens)
    return frozenset(
        " ".join(tokens[i : i + _SHINGLE_SIZE]) for i in range(len(tokens) - _SHINGLE_SIZE + 1)
    )


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _find_near(
    shingles: frozenset[str],
    seen: list[tuple[int, frozenset[str]]],
    threshold: float,
) -> int | None:
    """Return the chunk_id of the first existing entry above threshold."""
    for chunk_id, other in seen:
        if _jaccard(shingles, other) >= threshold:
            return chunk_id
    return None
