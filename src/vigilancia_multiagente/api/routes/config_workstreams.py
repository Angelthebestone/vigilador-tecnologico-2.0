"""Config endpoints for workstream toggles and health checks.

GET  /config/workstreams        — resolve current flags
PATCH /config/workstreams       — update flags
GET  /config/workstreams/health — external dependency health
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.config.workstream_overrides import (
    VALID_WORKSTREAM_KEYS,
    load_overrides,
    resolve_workstream_config,
    save_overrides,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config")


@router.get("/workstreams")
async def get_workstreams() -> dict:
    config = resolve_workstream_config()
    return {
        "ws_a": config.ws_a,
        "ws_b": config.ws_b,
        "ws_c": config.ws_c,
        "ws_d": config.ws_d,
        "ws_e": config.ws_e,
    }


@router.patch("/workstreams")
async def patch_workstreams(body: dict) -> dict:
    for key in body:
        if key not in VALID_WORKSTREAM_KEYS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid workstream key: {key}. Valid keys: {', '.join(VALID_WORKSTREAM_KEYS)}",
            )
        if not isinstance(body[key], bool):
            raise HTTPException(
                status_code=422,
                detail=f"Value for {key} must be boolean, got {type(body[key]).__name__}",
            )
    current = load_overrides()
    current.update(
        {k: v for k, v in body.items() if k in VALID_WORKSTREAM_KEYS and isinstance(v, bool)}
    )
    try:
        save_overrides(current)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist overrides: {exc}") from exc
    config = resolve_workstream_config()
    return {
        "ws_a": config.ws_a,
        "ws_b": config.ws_b,
        "ws_c": config.ws_c,
        "ws_d": config.ws_d,
        "ws_e": config.ws_e,
        "applies_to": "next_session",
    }


@router.get("/workstreams/health")
async def get_workstreams_health() -> dict:
    settings = get_settings()
    return {
        "ws_a": _ws_a_health(settings),
        "ws_b": _ws_b_health(settings),
        "ws_c": _ws_c_health(settings),
        "ws_d": _ws_d_health(settings),
        "ws_e": _ws_e_health(settings),
    }


def _ws_a_health(settings) -> dict:
    missing = []
    degraded = []
    if settings.google_factcheck_api_key is None:
        missing.append("google_factcheck_api_key")
    if settings.retraction_watch_csv_url is None:
        missing.append("retraction_watch_csv_url")
    return {
        "available": len(missing) == 0,
        "missing_dependencies": missing,
        "degraded_services": degraded,
    }


def _ws_b_health(settings) -> dict:
    return {
        "available": True,
        "missing_dependencies": [],
        "degraded_services": [],
    }


def _ws_c_health(settings) -> dict:
    return {
        "available": True,
        "missing_dependencies": [],
        "degraded_services": [],
    }


def _ws_d_health(settings) -> dict:
    missing = []
    degraded = []
    if settings.openalex_email is None:
        degraded.append("openalex_email_unset")
    return {
        "available": len(missing) == 0,
        "missing_dependencies": missing,
        "degraded_services": degraded,
    }


def _ws_e_health(settings) -> dict:
    missing = []
    if settings.google_factcheck_api_key is None:
        missing.append("google_factcheck_api_key")
    return {
        "available": len(missing) == 0,
        "missing_dependencies": missing,
        "degraded_services": [],
    }
