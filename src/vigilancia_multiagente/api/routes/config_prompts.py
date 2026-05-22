"""Config endpoints for prompt templates.

GET  /config/prompts              — list all templates with metadata
GET  /config/prompts/{name}       — get full content of one template
PUT  /config/prompts/{name}       — update override content
POST /config/prompts/{name}/restore — delete override, restore default
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from vigilancia_multiagente.config.prompt_overrides import (
    _VALID_TEMPLATE_NAMES,
    get_override,
    list_overrides,
    restore_default,
    set_override,
)
from vigilancia_multiagente.infra.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config")

MAX_PROMPT_SIZE_BYTES = 100 * 1024


@router.get("/prompts")
async def get_prompts() -> dict:
    templates = list_overrides()
    return {"templates": templates}


def _default_content(name: str) -> str:
    try:
        return load_prompt(f"evaluation/{name}")
    except FileNotFoundError:
        return ""


@router.get("/prompts/{name}")
async def get_prompt(name: str) -> dict:
    if name not in _VALID_TEMPLATE_NAMES:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    default = _default_content(name)
    override = get_override(name)
    modified = override is not None
    content = override if override is not None else default
    size = len(content.encode("utf-8"))
    return {
        "name": name,
        "content": content,
        "modified": modified,
        "default_content": default,
        "size": size,
    }


@router.put("/prompts/{name}")
async def put_prompt(name: str, body: dict) -> dict:
    if name not in _VALID_TEMPLATE_NAMES:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    content = body.get("content")
    if not content or not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=422, detail="Content is required and must be non-empty")
    if len(content.encode("utf-8")) > MAX_PROMPT_SIZE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Content exceeds max size ({MAX_PROMPT_SIZE_BYTES} bytes)",
        )
    try:
        set_override(name, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist override: {exc}") from exc
    return {
        "name": name,
        "modified": True,
        "size": len(content.encode("utf-8")),
    }


@router.post("/prompts/{name}/restore")
async def restore_prompt(name: str) -> dict:
    if name not in _VALID_TEMPLATE_NAMES:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    try:
        restore_default(name)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete override: {exc}") from exc
    return {
        "name": name,
        "modified": False,
        "restored": True,
    }
