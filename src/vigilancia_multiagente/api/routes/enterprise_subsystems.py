"""Enterprise 3.0 subsystem routes — skills, modes, playbooks, dreaming.

Read-oriented endpoints backed by services attached to ``app.state`` by the
enterprise composition root. If a subsystem is not wired (enterprise disabled
or init failed), the endpoint returns 503 with an explicit message.
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/enterprise", tags=["enterprise-subsystems"])


def _state(request: Request, name: str) -> Any:
    svc = getattr(request.app.state, name, None)
    if svc is None:
        raise HTTPException(status_code=503, detail=f"Subsystem '{name}' not available")
    return svc


@router.get("/skills")
async def list_skills(request: Request, mode: str | None = Query(default=None)):
    registry = _state(request, "skill_registry")
    return [asdict(c) for c in registry.get_cards(mode)]


@router.get("/skills/discover")
async def discover_skills(
    request: Request,
    intent: str = Query(min_length=1),
    mode: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
):
    registry = _state(request, "skill_registry")
    cards = await registry.discover(intent, mode, limit)
    return [asdict(c) for c in cards]


@router.get("/modes")
async def list_modes(request: Request):
    registry = _state(request, "mode_registry")
    return [
        {"id": m.id, "name": getattr(m, "name", m.id), "status": getattr(m, "status", "active")}
        for m in registry.list_available()
    ]


@router.get("/modes/{mode_id}")
async def get_mode(request: Request, mode_id: str):
    registry = _state(request, "mode_registry")
    mode = registry.get(mode_id)
    if mode is None:
        raise HTTPException(status_code=404, detail=f"Mode '{mode_id}' not found")
    return {
        "id": mode.id,
        "name": getattr(mode, "name", mode.id),
        "status": getattr(mode, "status", "active"),
    }


@router.get("/playbooks")
async def list_playbooks(request: Request):
    registry = _state(request, "playbook_registry")
    return [
        {"id": p.id, "name": p.name, "executor_type": p.executor_type, "parallel": p.parallel}
        for p in registry.list_available()
    ]


@router.get("/dreaming/status")
async def dreaming_status(request: Request):
    scheduler = _state(request, "dreaming_scheduler")
    orchestrator = getattr(request.app.state, "dreaming_orchestrator", None)
    return {
        "enabled": scheduler.enabled,
        "cron_hour": scheduler.config.cron_hour,
        "idle_timeout_min": scheduler.config.idle_timeout_min,
        "orchestrator_status": orchestrator.status.value if orchestrator else "unwired",
    }
