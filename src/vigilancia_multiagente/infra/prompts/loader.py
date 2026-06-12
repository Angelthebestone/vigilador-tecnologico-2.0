"""Prompt file loader with override support.

Resolution order: config/prompt_overrides/{path}.txt > prompts/{path}.txt
"""

from functools import lru_cache
from pathlib import Path

import vigilancia_multiagente

_PROMPTS_ROOT = Path(vigilancia_multiagente.__file__).resolve().parent / "prompts"


def _overrides_root() -> Path:
    from vigilancia_multiagente.config.settings import get_settings

    return Path(get_settings().prompt_overrides_dir)


@lru_cache(maxsize=64)
def load_prompt(path: str) -> str:
    """Load a prompt template. Checks overrides first, then defaults.

    Results are cached for the lifetime of the process.

    Args:
        path: Relative path without extension (e.g. ``orchestration/clarify``).

    Returns:
        The raw text content of the prompt file.

    Raises:
        FileNotFoundError: If neither override nor default file exists.
    """
    override_path = _overrides_root() / f"{path}.txt"
    if override_path.exists():
        return override_path.read_text(encoding="utf-8")
    return (_PROMPTS_ROOT / f"{path}.txt").read_text(encoding="utf-8")


class FilesystemPromptLoader:
    """Adapter that implements :class:`PromptLoader` against the local filesystem."""

    def load(self, path: str) -> str:
        return load_prompt(path)
