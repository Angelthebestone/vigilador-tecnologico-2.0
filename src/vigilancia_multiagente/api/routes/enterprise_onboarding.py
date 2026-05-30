import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.llm.xiaomimimo_client import XiaomimimoClient
from vigilancia_multiagente.infra.persistence.company_profile_repository import (
    CompanyProfile,
    CompanyProfileRepository,
)

router = APIRouter(prefix="/enterprise/onboarding", tags=["enterprise-onboarding"])

VALID_PROVIDERS = ("xiaomimimo", "minimax")


class CompanyRequest(BaseModel):
    name: str
    sector: str | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    timezone: str | None = None


class LLMProviderRequest(BaseModel):
    provider: str
    api_key: str
    model: str | None = None


class TestLLMRequest(BaseModel):
    provider: str | None = None


def get_company_repo(request: Request) -> CompanyProfileRepository:
    if hasattr(request.app.state, "company_repo"):
        return request.app.state.company_repo
    return CompanyProfileRepository(database)


def get_llm_client(request: Request) -> XiaomimimoClient:
    if hasattr(request.app.state, "llm_client"):
        return request.app.state.llm_client
    return XiaomimimoClient()


@router.post("/company", status_code=201)
async def onboard_company(
    body: CompanyRequest,
    repo: CompanyProfileRepository = Depends(get_company_repo),
):
    settings = get_settings()
    tenant_id = UUID(settings.default_tenant_id)
    profile = CompanyProfile(
        tenant_id=tenant_id,
        name=body.name,
        sector=body.sector,
        country=body.country,
        department=body.department,
        municipality=body.municipality,
        timezone=body.timezone,
    )
    await repo.upsert(profile)
    return {"status": "ok"}


@router.post("/llm-provider")
async def onboard_llm_provider(body: LLMProviderRequest):
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422, detail=f"Invalid provider. Must be one of {VALID_PROVIDERS}"
        )
    # MVP: just acknowledge — real persistence via OAuthManager deferred
    return {"status": "ok", "provider": body.provider}


@router.post("/test-llm")
async def test_llm(
    body: TestLLMRequest,
    request: Request,
    client: XiaomimimoClient = Depends(get_llm_client),
):
    try:
        start = time.time()
        resp = await client.chat_completion(messages=[{"role": "user", "content": "ping"}])
        latency_ms = round((time.time() - start) * 1000, 1)
        return {"status": "ok", "model": resp.model, "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "error", "error": str(e)}
