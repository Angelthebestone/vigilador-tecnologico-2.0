from fastapi import APIRouter

from vigilancia_multiagente.api.routes.config_prompts import router as config_prompts_router
from vigilancia_multiagente.api.routes.config_workstreams import router as config_workstreams_router
from vigilancia_multiagente.api.routes.conversation import router as conversation_router
from vigilancia_multiagente.api.routes.enterprise_metrics import router as enterprise_metrics_router
from vigilancia_multiagente.api.routes.enterprise_onboarding import (
    router as enterprise_onboarding_router,
)
from vigilancia_multiagente.api.routes.enterprise_subsystems import (
    router as enterprise_subsystems_router,
)
from vigilancia_multiagente.api.routes.enterprise_tools import router as enterprise_tools_router
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
api_router.include_router(config_workstreams_router)
api_router.include_router(config_prompts_router)
api_router.include_router(start_router)
api_router.include_router(approve_router)
api_router.include_router(outputs_router)
api_router.include_router(governance_router)
api_router.include_router(sessions_router)
api_router.include_router(reports_router)
api_router.include_router(conversation_router)
api_router.include_router(delete_router)
api_router.include_router(upload_router)
api_v2_router.include_router(config_workstreams_router)
api_v2_router.include_router(config_prompts_router)
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
api_v2_router.include_router(enterprise_onboarding_router)
api_v2_router.include_router(enterprise_tools_router)
api_v2_router.include_router(enterprise_metrics_router)
api_v2_router.include_router(enterprise_subsystems_router)
