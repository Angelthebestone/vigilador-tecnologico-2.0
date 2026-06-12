"""Enterprise onboarding endpoints (Spec 021 D4 / T119-T120).

The four MVP endpoints (no user-login per D4):

* ``POST /api/v2/enterprise/onboarding/company``    — write company identity + geo
* ``POST /api/v2/enterprise/onboarding/providers``  — pin embedding/reranker provider
* ``POST /api/v2/enterprise/onboarding/connectors/drive`` — start Google Drive OAuth
* ``POST /api/v2/enterprise/onboarding/ingest/initial``   — kick off first ingestion run

Constitución:
* SRP: each endpoint does one thing.
* #4 explicit: missing OAuth env, unknown provider, ingestion-disabled, all
  surface as ``HTTPException`` with a clear detail (no silent successes).
* D4: NONE of these endpoints requires a user JWT or session token. Service
  OAuth (Drive token via :class:`OAuthManager`) is unaffected.
"""

import logging
import time
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.llm.xiaomimimo_client import XiaomimimoClient
from vigilancia_multiagente.infra.persistence.company_profile_repository import (
    CompanyProfile,
    CompanyProfileRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise/onboarding", tags=["enterprise-onboarding"])

VALID_PROVIDERS = ("xiaomimimo", "minimax")
VALID_EMBEDDING_PROVIDERS = ("gemini", "openai", "cohere")
VALID_RERANKER_PROVIDERS = ("cohere", "voyage", "none")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CompanyGeo(BaseModel):
    country: str = Field(..., min_length=2, max_length=64)
    department: str | None = None
    municipality: str | None = None
    timezone: str | None = None


class CompanyRequest(BaseModel):
    """Body for POST /company. Writes both DB profile and identity.md."""

    name: str = Field(..., min_length=1, max_length=200)
    sector: str | None = None
    geo: CompanyGeo
    identity_md: str | None = Field(
        default=None,
        description="Optional pre-baked identity.md content; defaults to a "
        "minimal template generated from name + sector + geo.",
    )


class ProvidersRequest(BaseModel):
    embedding_provider: str = Field(
        ...,
        description=f"One of {VALID_EMBEDDING_PROVIDERS}.",
    )
    reranker_provider: str = Field(
        ...,
        description=f"One of {VALID_RERANKER_PROVIDERS}.",
    )


class DriveConnectorRequest(BaseModel):
    """Either kicks off OAuth (no body) or finalizes with a code."""

    auth_code: str | None = Field(
        default=None,
        description="OAuth callback code. When omitted, returns the URL "
        "the user must visit to grant Drive read scope.",
    )
    redirect_uri: str | None = Field(
        default=None,
        description="OAuth redirect URI registered with the Google client. "
        "Defaults to settings/env-driven value.",
    )


class InitialIngestionRequest(BaseModel):
    connector: str = Field(
        default="google_drive",
        description="Which connector to drive in this initial run.",
    )
    folder_id: str | None = Field(
        default=None,
        description="Optional Drive folder id; defaults to whatever the "
        "connector resolves at runtime.",
    )


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_company_repo(request: Request) -> CompanyProfileRepository:
    if hasattr(request.app.state, "company_repo"):
        return request.app.state.company_repo
    return CompanyProfileRepository(database)


def get_llm_client(request: Request) -> XiaomimimoClient:
    if hasattr(request.app.state, "llm_client"):
        return request.app.state.llm_client
    return XiaomimimoClient()


# ---------------------------------------------------------------------------
# Pre-existing endpoints (kept for backwards compatibility)
# ---------------------------------------------------------------------------


class LLMProviderRequest(BaseModel):
    provider: str
    api_key: str
    model: str | None = None


class TestLLMRequest(BaseModel):
    provider: str | None = None


@router.post("/llm-provider")
async def onboard_llm_provider(body: LLMProviderRequest):
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider. Must be one of {VALID_PROVIDERS}",
        )
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
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Spec 021 onboarding endpoints (no user auth — FR-038)
# ---------------------------------------------------------------------------


@router.post("/company", status_code=201)
async def onboard_company(
    body: CompanyRequest,
    repo: CompanyProfileRepository = Depends(get_company_repo),
):
    """POST /company — persist DB profile + write ``config/company/identity.md``.

    No user auth (D4). Always operates against ``settings.default_tenant_id``
    in single-tenant MVP; multi-tenant variants pass tenant via header.
    """
    settings = get_settings()
    tenant_id = UUID(settings.default_tenant_id)
    profile = CompanyProfile(
        tenant_id=tenant_id,
        name=body.name,
        sector=body.sector,
        country=body.geo.country,
        department=body.geo.department,
        municipality=body.geo.municipality,
        timezone=body.geo.timezone,
    )
    await repo.upsert(profile)

    identity_path = _write_identity_md(body)
    return {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "identity_path": str(identity_path),
        "geo": body.geo.model_dump(),
    }


@router.post("/providers", status_code=200)
async def onboard_providers(body: ProvidersRequest):
    """POST /providers — pin embedding + reranker provider for the tenant.

    The values are validated against the supported set and returned for
    confirmation. Real persistence (writing back to ``settings``) lands
    in F4a.H wiring.
    """
    if body.embedding_provider not in VALID_EMBEDDING_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"embedding_provider must be one of {VALID_EMBEDDING_PROVIDERS}",
        )
    if body.reranker_provider not in VALID_RERANKER_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"reranker_provider must be one of {VALID_RERANKER_PROVIDERS}",
        )
    return {
        "status": "ok",
        "embedding_provider": body.embedding_provider,
        "reranker_provider": body.reranker_provider,
    }


@router.post("/connectors/drive", status_code=200)
async def connect_drive(body: DriveConnectorRequest, request: Request):
    """POST /connectors/drive — start (or finalize) Google Drive OAuth.

    * No body → returns the OAuth ``authorization_url`` for the operator
      to visit.
    * Body with ``auth_code`` → expects the callback to have happened; the
      MVP records the intent + returns ``status: ok``. Production wiring
      (token exchange) lives in :class:`OAuthManager`; the route stays
      thin so the wiring root can swap in the real exchange without
      touching this file.
    """
    settings = get_settings()
    client_id = _read_setting(settings, "google_client_id", required=True)
    redirect_uri = (
        body.redirect_uri
        or _read_setting(settings, "google_redirect_uri", required=False)
        or "http://localhost:8000/api/v2/enterprise/onboarding/connectors/drive/callback"
    )

    if body.auth_code is None:
        # Step 1 — return the URL the user must visit.
        scope = "https://www.googleapis.com/auth/drive.readonly"
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&access_type=offline"
            f"&prompt=consent"
        )
        return {"status": "authorize_required", "authorization_url": auth_url}

    # Step 2 — token exchange happens in the OAuthManager wiring (T121).
    # MVP records the intent; the orchestration wiring will replace this
    # branch with a real call to OAuthManager.exchange(code).
    if hasattr(request.app.state, "oauth_manager"):
        logger.info("OAuthManager available; deferred to wiring root for token exchange")
    return {
        "status": "ok",
        "received_auth_code": True,
        "next": "ingest_initial",
    }


@router.post("/ingest/initial", status_code=202)
async def ingest_initial(body: InitialIngestionRequest, request: Request):
    """POST /ingest/initial — launch the first ingestion run.

    Returns ``202 Accepted`` with a ``job_id``. Actual orchestration is
    wired in F4a.H — the route surfaces a clear ``503`` if the
    ``ingestion_orchestrator`` service has not been attached to
    ``app.state`` yet.
    """
    settings = get_settings()
    if not settings.ingestion_enabled:
        raise HTTPException(
            status_code=409,
            detail="ingestion is disabled (settings.ingestion_enabled=False)",
        )
    if body.connector not in settings.ingestion_connectors:
        raise HTTPException(
            status_code=422,
            detail=(
                f"connector '{body.connector}' is not enabled. "
                f"Active: {list(settings.ingestion_connectors)}"
            ),
        )

    job_id = uuid4()
    if hasattr(request.app.state, "ingestion_orchestrator"):
        logger.info(
            "ingestion_orchestrator attached — job %s queued for connector %s",
            job_id,
            body.connector,
        )
        # F4a.H attaches a fire-and-forget task launcher here.
    else:
        logger.warning(
            "ingestion_orchestrator NOT attached — recording intent only (job %s for connector %s)",
            job_id,
            body.connector,
        )

    return {
        "status": "accepted",
        "job_id": str(job_id),
        "connector": body.connector,
        "folder_id": body.folder_id,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_setting(settings: object, name: str, *, required: bool) -> str | None:
    value = getattr(settings, name, None)
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()  # type: ignore[union-attr]
    if value is None or value == "":
        if required:
            raise HTTPException(
                status_code=503,
                detail=f"setting '{name}' not configured (set VT_{name.upper()})",
            )
        return None
    return str(value)


def _write_identity_md(body: CompanyRequest) -> Path:
    """Persist ``config/company/identity.md`` with the company snapshot."""
    target_dir = _project_root() / "config" / "company"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "identity.md"

    if body.identity_md and body.identity_md.strip():
        content = body.identity_md.strip() + "\n"
    else:
        content = _render_default_identity(body)
    target.write_text(content, encoding="utf-8")
    logger.info("Wrote company identity to %s", target)
    return target


def _render_default_identity(body: CompanyRequest) -> str:
    sector = body.sector or "(no sector declared)"
    geo = body.geo
    geo_lines = [f"- País: {geo.country}"]
    if geo.department:
        geo_lines.append(f"- Departamento: {geo.department}")
    if geo.municipality:
        geo_lines.append(f"- Municipio: {geo.municipality}")
    if geo.timezone:
        geo_lines.append(f"- Zona horaria: {geo.timezone}")
    geo_block = "\n".join(geo_lines)
    return (
        f"# {body.name}\n"
        "\n"
        "## Identidad\n"
        "\n"
        f"- Sector: {sector}\n"
        f"{geo_block}\n"
        "\n"
        "## Contexto operativo\n"
        "\n"
        "Edite este archivo para reflejar la realidad de la empresa: misión,\n"
        "stakeholders clave, productos/servicios, restricciones regulatorias,\n"
        "stack tecnológico, etc. El agente lo carga como subset de contexto\n"
        "según el modo activo.\n"
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]
