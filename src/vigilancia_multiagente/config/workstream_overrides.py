"""Workstream flag overrides — JSON persistence layer for UI-driven toggles.

Resolution order: JSON override > settings (.env) > False.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from vigilancia_multiagente.config.settings import get_settings

logger = logging.getLogger(__name__)

VALID_WORKSTREAM_KEYS = ("ws_a", "ws_b", "ws_c", "ws_d", "ws_e")


@dataclass(slots=True)
class WorkstreamConfig:
    ws_a: bool = False
    ws_b: bool = False
    ws_c: bool = False
    ws_d: bool = False
    ws_e: bool = False


def load_overrides() -> dict[str, bool]:
    settings = get_settings()
    path = Path(settings.workstream_overrides_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read workstream overrides: %s", exc)
        return {}
    overrides: dict[str, bool] = {}
    for key in VALID_WORKSTREAM_KEYS:
        if key in raw and isinstance(raw[key], bool):
            overrides[key] = raw[key]
    return overrides


def save_overrides(data: dict[str, bool]) -> None:
    settings = get_settings()
    path = Path(settings.workstream_overrides_path)
    filtered = {k: v for k, v in data.items() if k in VALID_WORKSTREAM_KEYS and isinstance(v, bool)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(filtered, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_workstream_config(settings=None) -> WorkstreamConfig:
    if settings is None:
        settings = get_settings()
    overrides = load_overrides()

    def _resolve(key: str, env_flag: bool) -> bool:
        return overrides.get(key, env_flag)

    return WorkstreamConfig(
        ws_a=_resolve("ws_a", settings.eval_ws_a_enabled),
        ws_b=_resolve("ws_b", settings.eval_ws_b_enabled),
        ws_c=_resolve("ws_c", settings.eval_ws_c_enabled),
        ws_d=_resolve("ws_d", settings.eval_ws_d_enabled),
        ws_e=_resolve("ws_e", settings.eval_ws_e_enabled),
    )
