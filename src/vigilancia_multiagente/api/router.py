from fastapi import APIRouter

from vigilancia_multiagente.api.routes.conversation import router as conversation_router
from vigilancia_multiagente.api.routes.reports import router as reports_router
from vigilancia_multiagente.api.routes.research_approve import router as approve_router
from vigilancia_multiagente.api.routes.research_delete import router as delete_router
from vigilancia_multiagente.api.routes.research_governance import router as governance_router
from vigilancia_multiagente.api.routes.research_outputs import router as outputs_router
from vigilancia_multiagente.api.routes.research_start_clarify import router as start_router
from vigilancia_multiagente.api.routes.sessions import router as sessions_router
from vigilancia_multiagente.api.routes.sources import router as sources_router
from vigilancia_multiagente.api.routes.system_base import router as system_base_router
from vigilancia_multiagente.api.routes.upload import router as upload_router

api_router = APIRouter()
api_v2_router = APIRouter(prefix="/api/v2")
api_router.include_router(start_router)
api_router.include_router(approve_router)
api_router.include_router(outputs_router)
api_router.include_router(governance_router)
api_router.include_router(sessions_router)
api_router.include_router(reports_router)
api_router.include_router(conversation_router)
api_router.include_router(delete_router)
api_router.include_router(upload_router)
api_v2_router.include_router(start_router)
api_v2_router.include_router(approve_router)
api_v2_router.include_router(outputs_router)
api_v2_router.include_router(governance_router)
api_v2_router.include_router(system_base_router)
api_v2_router.include_router(sessions_router)
api_v2_router.include_router(sources_router)
api_v2_router.include_router(reports_router)
api_v2_router.include_router(conversation_router)
api_v2_router.include_router(delete_router)
api_v2_router.include_router(upload_router)
