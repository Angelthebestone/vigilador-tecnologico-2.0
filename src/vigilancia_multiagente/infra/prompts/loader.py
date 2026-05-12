"""Prompt file loader.

Loads prompt templates from ``src/vigilancia_multiagente/prompts/``.

Usage:
    from vigilancia_multiagente.infra.prompts.loader import load_prompt

    prompt = load_prompt("orchestration/clarify")
    prompt = load_prompt("branches/avances")
"""

from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parent.parent.parent / "prompts"


def load_prompt(path: str) -> str:
    """Load a prompt template from ``src/prompts/{path}.txt``.

    Args:
        path: Relative path without extension (e.g. ``orchestration/clarify``).

    Returns:
        The raw text content of the prompt file.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    file_path = _PROMPTS_ROOT / f"{path}.txt"
    return file_path.read_text(encoding="utf-8")
