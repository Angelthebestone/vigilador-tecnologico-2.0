import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from vigilancia_multiagente import __version__
from vigilancia_multiagente.api.router import api_router, api_v2_router
from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.infra.db.connection import database


def build_runtime_metadata(settings) -> dict[str, object]:
    closure_status = {
        "api_v2": "ready",
        "graph_analytics": "ready",
        "mcp_runtime": "ready",
        "tests": "ready",
        "quality_gates": "ready",
        "minimax": "blocked" if not settings.minimax_api_key else "ready",
    }
    return {
        "service": settings.app_name,
        "version": __version__,
        "environment": settings.app_env,
        "api_base": "/api/v2",
        "started_at": datetime.now(UTC).isoformat(),
        "closure_status": closure_status,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await database.initialize()
    app.state.runtime_metadata = build_runtime_metadata(settings)
    app.state.started_at = datetime.now(UTC)
    app.state.ready = True

    # Enterprise (3.0) subsystem composition — attaches tool_registry,
    # mode_registry, playbook_registry, skill_registry, dreaming_* onto
    # app.state. Optional + guarded: a failure logs and the core 2.0 app
    # still boots.
    if settings.enterprise_enabled:
        try:
            from vigilancia_multiagente.api.enterprise_composition import (
                attach_to_app_state,
                build_enterprise_services,
            )

            enterprise_services = await build_enterprise_services(settings, database)
            attach_to_app_state(app, enterprise_services)
        except Exception:
            logging.getLogger(__name__).exception(
                "Enterprise composition failed; core app continues without 3.0 subsystems"
            )

    health_monitor = None
    if settings.health_monitor_enabled:
        try:
            from vigilancia_multiagente.enterprise.observability.health_monitor import HealthMonitor
            from vigilancia_multiagente.infra.persistence.tool_health_repository import (
                ToolHealthRepository,
            )

            tool_health_repo = ToolHealthRepository(database)
            # tool_registry may be set externally; use a lazy ref
            if hasattr(app.state, "tool_registry"):
                health_monitor = HealthMonitor(
                    tool_registry=app.state.tool_registry,
                    tool_health_repo=tool_health_repo,
                    settings=settings,
                )
                health_monitor.start()
        except Exception:
            logging.getLogger(__name__).exception(
                "HealthMonitor startup failed; continuing without monitoring"
            )

    yield

    if health_monitor:
        health_monitor.stop()

    if hasattr(app.state, "tool_registry"):
        try:
            await app.state.tool_registry.aclose_all()
        except Exception:
            logging.getLogger(__name__).exception("tool_registry cleanup failed")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, object]:
        runtime_metadata = getattr(app.state, "runtime_metadata", build_runtime_metadata(settings))
        return {
            "status": "ok",
            "ready": bool(getattr(app.state, "ready", False)),
            "database": "initialized",
            "runtime": runtime_metadata,
        }

    app.include_router(api_router)
    app.include_router(api_v2_router)

    if settings.enterprise_enabled:
        try:
            from vigilancia_multiagente.enterprise.observability.metrics import metrics_app

            app.mount("/metrics", metrics_app)
        except Exception:
            pass

    return app


app = create_app()
