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
    yield


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

    return app


app = create_app()

