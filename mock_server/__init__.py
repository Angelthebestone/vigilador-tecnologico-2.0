"""Mock server package for Vigilador Tecnológico 2.0.

Simula toda la API sin necesidad de MiniMax, PostgreSQL ni claves externas.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mock_server.routes.config import router as config_router
from mock_server.routes.research import router as research_router

app = FastAPI(title="Vigilador Tecnológico 2.0 — Mock Server", version="2.0.0-mock")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router, prefix="/api/v2")
app.include_router(research_router, prefix="/api/v2")
