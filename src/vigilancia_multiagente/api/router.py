from fastapi import APIRouter

from vigilancia_multiagente.api.routes.research_approve import router as approve_router
from vigilancia_multiagente.api.routes.research_governance import router as governance_router
from vigilancia_multiagente.api.routes.research_outputs import router as outputs_router
from vigilancia_multiagente.api.routes.research_start_clarify import router as start_router
from vigilancia_multiagente.api.routes.system_base import router as system_base_router

api_router = APIRouter()
api_v2_router = APIRouter(prefix="/api/v2")
api_router.include_router(start_router)
api_router.include_router(approve_router)
api_router.include_router(outputs_router)
api_router.include_router(governance_router)
api_v2_router.include_router(start_router)
api_v2_router.include_router(approve_router)
api_v2_router.include_router(outputs_router)
api_v2_router.include_router(governance_router)
api_v2_router.include_router(system_base_router)

