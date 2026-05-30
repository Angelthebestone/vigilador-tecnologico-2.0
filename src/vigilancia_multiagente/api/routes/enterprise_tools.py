from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Query, Request

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry

router = APIRouter(prefix="/enterprise/tools", tags=["enterprise-tools"])


def get_tool_registry(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry


@router.get("")
async def list_tools(request: Request, detail: str = Query(default="card")):
    registry: ToolRegistry = get_tool_registry(request)
    settings = get_settings()
    tenant_id = UUID(settings.default_tenant_id)
    cards = await registry.list_tools_for_role("admin", tenant_id)
    # Filter out DOWN tools from public listing
    cards = [c for c in cards if c.status != "DOWN"]
    if detail == "card":
        return [asdict(c) for c in cards]
    if detail == "summary":
        results = []
        for c in cards:
            s = await registry.get_summary(c.id)
            results.append(asdict(s))
        return results
    if detail == "docs":
        results = []
        for c in cards:
            d = await registry.get_docs(c.id)
            results.append(asdict(d))
        return results
    return [asdict(c) for c in cards]
