"""F4a.G / T119 — tests for the spec-021 onboarding endpoints (no auth, D4)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from vigilancia_multiagente.infra.persistence.company_profile_repository import (
    CompanyProfileRepository,
)


@pytest.fixture
def mock_company_repo():
    repo = AsyncMock(spec=CompanyProfileRepository)
    repo.upsert = AsyncMock(return_value=None)
    repo.get = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def app(mock_company_repo):
    from vigilancia_multiagente.api.app import create_app

    application = create_app()
    application.state.company_repo = mock_company_repo
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# /providers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_providers_accepts_valid_pair(client):
    resp = await client.post(
        "/api/v2/enterprise/onboarding/providers",
        json={"embedding_provider": "gemini", "reranker_provider": "cohere"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["embedding_provider"] == "gemini"
    assert body["reranker_provider"] == "cohere"


@pytest.mark.asyncio
async def test_post_providers_rejects_unknown_embedding(client):
    resp = await client.post(
        "/api/v2/enterprise/onboarding/providers",
        json={"embedding_provider": "unknown", "reranker_provider": "cohere"},
    )
    assert resp.status_code == 422
    assert "embedding_provider" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_post_providers_rejects_unknown_reranker(client):
    resp = await client.post(
        "/api/v2/enterprise/onboarding/providers",
        json={"embedding_provider": "gemini", "reranker_provider": "unknown"},
    )
    assert resp.status_code == 422
    assert "reranker_provider" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /connectors/drive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_connectors_drive_returns_authorize_url_when_unconfigured(
    client, monkeypatch
):
    """Without VT_GOOGLE_CLIENT_ID set, the endpoint surfaces 503."""
    from vigilancia_multiagente.config import settings as settings_module

    settings_module.get_settings.cache_clear()
    monkeypatch.delenv("VT_GOOGLE_CLIENT_ID", raising=False)
    resp = await client.post(
        "/api/v2/enterprise/onboarding/connectors/drive", json={}
    )
    assert resp.status_code == 503
    assert "google_client_id" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_connectors_drive_returns_url_with_client_id(
    client, monkeypatch
):
    """When VT_GOOGLE_CLIENT_ID is configured, returns an authorize URL."""
    from vigilancia_multiagente.config import settings as settings_module

    monkeypatch.setenv("VT_GOOGLE_CLIENT_ID", "client-abc-123")
    settings_module.get_settings.cache_clear()

    resp = await client.post(
        "/api/v2/enterprise/onboarding/connectors/drive", json={}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "authorize_required"
    assert "client-abc-123" in body["authorization_url"]
    assert "drive.readonly" in body["authorization_url"]

    # Clean cache so other tests get fresh settings.
    monkeypatch.delenv("VT_GOOGLE_CLIENT_ID", raising=False)
    settings_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_post_connectors_drive_with_auth_code_records_intent(
    client, monkeypatch
):
    from vigilancia_multiagente.config import settings as settings_module

    monkeypatch.setenv("VT_GOOGLE_CLIENT_ID", "client-id")
    settings_module.get_settings.cache_clear()

    resp = await client.post(
        "/api/v2/enterprise/onboarding/connectors/drive",
        json={"auth_code": "4/abcdef"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["received_auth_code"] is True

    monkeypatch.delenv("VT_GOOGLE_CLIENT_ID", raising=False)
    settings_module.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# /ingest/initial
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_ingest_initial_accepts_default_connector(client, monkeypatch):
    from vigilancia_multiagente.config import settings as settings_module

    monkeypatch.setenv("VT_INGESTION_ENABLED", "true")
    settings_module.get_settings.cache_clear()

    resp = await client.post(
        "/api/v2/enterprise/onboarding/ingest/initial", json={}
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["connector"] == "google_drive"
    assert "job_id" in body

    monkeypatch.delenv("VT_INGESTION_ENABLED", raising=False)
    settings_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_post_ingest_initial_rejects_unknown_connector(client):
    resp = await client.post(
        "/api/v2/enterprise/onboarding/ingest/initial",
        json={"connector": "dropbox"},
    )
    assert resp.status_code == 422
    assert "dropbox" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# D4 — no user auth on any endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_endpoint_requires_authorization_header(client, mock_company_repo, tmp_path, monkeypatch):
    from vigilancia_multiagente.api.routes import enterprise_onboarding

    monkeypatch.setattr(enterprise_onboarding, "_project_root", lambda: tmp_path)
    monkeypatch.setenv("VT_GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("VT_INGESTION_ENABLED", "true")
    from vigilancia_multiagente.config import settings as settings_module

    settings_module.get_settings.cache_clear()

    # All four endpoints called without any Authorization header.
    payloads = [
        ("/api/v2/enterprise/onboarding/company",
         {"name": "X", "geo": {"country": "CO"}}),
        ("/api/v2/enterprise/onboarding/providers",
         {"embedding_provider": "gemini", "reranker_provider": "cohere"}),
        ("/api/v2/enterprise/onboarding/connectors/drive", {}),
        ("/api/v2/enterprise/onboarding/ingest/initial", {}),
    ]
    for url, payload in payloads:
        resp = await client.post(url, json=payload)
        assert resp.status_code in (200, 201, 202), (
            f"endpoint {url} returned {resp.status_code} — should not require auth"
        )

    monkeypatch.delenv("VT_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("VT_INGESTION_ENABLED", raising=False)
    settings_module.get_settings.cache_clear()
