from fastapi import APIRouter
from starlette.routing import Mount

from vigilancia_multiagente.enterprise.observability.metrics import metrics_app

router = APIRouter(tags=["metrics"])
router.routes.append(Mount("/metrics", app=metrics_app))
