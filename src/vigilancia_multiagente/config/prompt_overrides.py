"""Prompt overrides — filesystem persistence for custom prompt templates.

Each override is a .txt file in config/prompt_overrides/. Resolution order:
override file > default from prompts/ directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from vigilancia_multiagente.config.settings import get_settings

logger = logging.getLogger(__name__)

_VALID_TEMPLATE_NAMES = (
    "assumption_detection",
    "counterfactual",
    "falsification",
    "query_expand",
    "stakeholder_academic",
    "stakeholder_competitor",
    "stakeholder_investor",
    "stakeholder_regulator",
)

MAX_PROMPT_SIZE_BYTES = 100 * 1024  # 100KB


def _overrides_dir() -> Path:
    return Path(get_settings().prompt_overrides_dir)


def _is_valid_name(name: str) -> bool:
    return name in _VALID_TEMPLATE_NAMES


def get_override(name: str) -> str | None:
    if not _is_valid_name(name):
        return None
    filepath = _overrides_dir() / f"{name}.txt"
    if filepath.exists():
        try:
            return filepath.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to read prompt override %s: %s", name, exc)
            return None
    return None


def set_override(name: str, content: str) -> None:
    if not _is_valid_name(name):
        raise ValueError(f"Unknown template name: {name}")
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_PROMPT_SIZE_BYTES:
        raise ValueError(f"Prompt content exceeds max size ({MAX_PROMPT_SIZE_BYTES} bytes)")
    _overrides_dir().mkdir(parents=True, exist_ok=True)
    (_overrides_dir() / f"{name}.txt").write_text(content, encoding="utf-8")


def restore_default(name: str) -> None:
    if not _is_valid_name(name):
        raise ValueError(f"Unknown template name: {name}")
    filepath = _overrides_dir() / f"{name}.txt"
    if filepath.exists():
        try:
            filepath.unlink()
        except OSError as exc:
            logger.warning("Failed to delete prompt override %s: %s", name, exc)


def list_overrides() -> list[dict]:
    templates: list[dict] = []
    for name in _VALID_TEMPLATE_NAMES:
        override = get_override(name)
        filepath = _overrides_dir() / f"{name}.txt"
        modified = filepath.exists()
        if override is not None:
            size = len(override.encode("utf-8"))
        else:
            # Default size: we don't load the full default here for perf;
            # the caller (API) will compute it from the actual file.
            size = 0
            try:
                from vigilancia_multiagente.infra.prompts.loader import load_prompt

                default_content = load_prompt(f"evaluation/{name}")
                size = len(default_content.encode("utf-8"))
            except Exception:
                pass
        templates.append(
            {
                "name": name,
                "modified": modified,
                "size": size,
            }
        )
    return templates
