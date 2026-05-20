"""Prompt file loader."""

from functools import lru_cache
from pathlib import Path

import vigilancia_multiagente

_PROMPTS_ROOT = Path(vigilancia_multiagente.__file__).resolve().parent / "prompts"


@lru_cache(maxsize=64)
def load_prompt(path: str) -> str:
    """Load a prompt template from ``src/vigilancia_multiagente/prompts/{path}.txt``.

    Results are cached for the lifetime of the process; prompt files are not
    expected to change at runtime.

    Args:
        path: Relative path without extension (e.g. ``orchestration/clarify``).

    Returns:
        The raw text content of the prompt file.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    return (_PROMPTS_ROOT / f"{path}.txt").read_text(encoding="utf-8")


class FilesystemPromptLoader:
    """Adapter that implements :class:`PromptLoader` against the local filesystem."""

    def load(self, path: str) -> str:
        return load_prompt(path)
