"""Document chunking (Spec 021 F2.C T061).

Char-window chunking with configurable overlap. Tokens are approximated
with the rule-of-thumb 1 token ≈ 4 chars to avoid pulling in ``tiktoken``
(big optional dep). For the MVP this is sufficient — embeddings are robust
to a ±20% chunk-size jitter, and downstream dedup catches near-duplicates.

Constitución:
* SRP: one function (``chunk_text``) + one dataclass (``Chunk``).
* KISS/YAGNI: no semantic boundary detection; that lands in F2 wave 2 if
  needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_DEFAULT_CHARS_PER_TOKEN = 4
_DEFAULT_TOKENS_PER_CHUNK = 512
_DEFAULT_OVERLAP_TOKENS = 64


@dataclass(frozen=True)
class Chunk:
    """Bounded text fragment ready for embedding + indexing.

    ``chunk_id`` is assigned by the caller (orchestrator) so the same id
    can be reused across the embedding gateway and the vector index.
    """

    chunk_id: int
    document_id: str
    text: str
    char_start: int
    char_end: int
    metadata: dict[str, object] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


def chunk_text(
    *,
    document_id: str,
    text: str,
    tokens_per_chunk: int = _DEFAULT_TOKENS_PER_CHUNK,
    overlap_tokens: int = _DEFAULT_OVERLAP_TOKENS,
    chars_per_token: int = _DEFAULT_CHARS_PER_TOKEN,
    base_chunk_id: int = 0,
    metadata: dict[str, object] | None = None,
) -> list[Chunk]:
    """Split ``text`` into overlapping windows.

    Args:
        document_id: stable id of the source document.
        text: raw text to chunk.
        tokens_per_chunk: max tokens per chunk (default 512).
        overlap_tokens: tokens shared with the next chunk (default 64).
        chars_per_token: chars per token approximation (default 4).
        base_chunk_id: starting id; downstream chunks get ``base_chunk_id + i``.
        metadata: copied verbatim into each chunk.

    Returns:
        List of :class:`Chunk` instances (empty if ``text`` is empty).

    Raises:
        ValueError: ``tokens_per_chunk <= overlap_tokens`` (would loop forever).
    """
    if tokens_per_chunk <= overlap_tokens:
        raise ValueError(
            "chunk_text: tokens_per_chunk must be > overlap_tokens "
            f"(got {tokens_per_chunk}, {overlap_tokens})"
        )
    text = text or ""
    if not text.strip():
        return []
    window = tokens_per_chunk * chars_per_token
    step = (tokens_per_chunk - overlap_tokens) * chars_per_token
    out: list[Chunk] = []
    pos = 0
    idx = 0
    md = dict(metadata or {})
    while pos < len(text):
        end = min(pos + window, len(text))
        snippet = text[pos:end].strip()
        if snippet:
            out.append(
                Chunk(
                    chunk_id=base_chunk_id + idx,
                    document_id=document_id,
                    text=snippet,
                    char_start=pos,
                    char_end=end,
                    metadata=dict(md),
                )
            )
            idx += 1
        if end >= len(text):
            break
        pos += step
    return out
