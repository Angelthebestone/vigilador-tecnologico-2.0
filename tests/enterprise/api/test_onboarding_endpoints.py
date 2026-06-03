"""T035 - Tests para endpoints de onboarding enterprise."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from vigilancia_multiagente.infra.llm.xiaomimimo_client import ChatResponse, XiaomimimoClient
from vigilancia_multiagente.infra.persistence.company_profile_repository import (
    CompanyProfileRepository,
)

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def mock_company_repo():
    repo = AsyncMock(spec=CompanyProfileRepository)
    repo.upsert = AsyncMock(return_value=None)
    repo.get = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_llm_client():
    client = AsyncMock(spec=XiaomimimoClient)
    client.chat_completion = AsyncMock(
        return_value=ChatResponse(
            content="Hello from Xiaomimimo",
            tool_calls=[],
            model="mimo-v2-flash",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )
    )
    return client


@pytest.fixture
def app(mock_company_repo, mock_llm_client):
    from vigilancia_multiagente.api.app import create_app

    application = create_app()
    # Override dependencies via app state or dependency_overrides
    application.state.company_repo = mock_company_repo
    application.state.llm_client = mock_llm_client
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_post_company_persists_profile(client, mock_company_repo, tmp_path, monkeypatch):
    """POST /api/v2/enterprise/onboarding/company persiste company_profile."""
    # Redirect identity.md write away from the repo tree.
    from vigilancia_multiagente.api.routes import enterprise_onboarding

    monkeypatch.setattr(enterprise_onboarding, "_project_root", lambda: tmp_path)

    payload = {
        "name": "Acme Corp",
        "sector": "Technology",
        "geo": {
            "country": "CO",
            "department": "Antioquia",
            "municipality": "Medellín",
            "timezone": "America/Bogota",
        },
    }
    resp = await client.post("/api/v2/enterprise/onboarding/company", json=payload)
    assert resp.status_code in (200, 201)
    mock_company_repo.upsert.assert_called_once()
    body = resp.json()
    assert body["geo"]["country"] == "CO"
    assert (tmp_path / "config" / "company" / "identity.md").exists()


@pytest.mark.asyncio
async def test_post_llm_provider_validates_and_persists(client):
    """POST /api/v2/enterprise/onboarding/llm-provider valida provider y persiste."""
    payload = {
        "provider": "xiaomimimo",
        "api_key": "sk-test-key-12345",
        "model": "mimo-v2-flash",
    }
    resp = await client.post("/api/v2/enterprise/onboarding/llm-provider", json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data.get("provider") == "xiaomimimo"


@pytest.mark.asyncio
async def test_post_test_llm_calls_xiaomimimo_returns_ok_with_latency(client, mock_llm_client):
    """POST /api/v2/enterprise/onboarding/test-llm llama Xiaomimimo y retorna OK con latencia."""
    resp = await client.post("/api/v2/enterprise/onboarding/test-llm", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "latency_ms" in data
    mock_llm_client.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_partial_flow_step1_then_resume(client, mock_company_repo, tmp_path, monkeypatch):
    """Flujo parcial: solo paso 1, luego retomar (upsert idempotente)."""
    from vigilancia_multiagente.api.routes import enterprise_onboarding

    monkeypatch.setattr(enterprise_onboarding, "_project_root", lambda: tmp_path)

    payload = {
        "name": "Partial Corp",
        "sector": "Finance",
        "geo": {"country": "CO"},
    }
    resp = await client.post("/api/v2/enterprise/onboarding/company", json=payload)
    assert resp.status_code in (200, 201)

    resp2 = await client.post("/api/v2/enterprise/onboarding/company", json=payload)
    assert resp2.status_code in (200, 201)
    assert mock_company_repo.upsert.call_count == 2


@pytest.mark.asyncio
async def test_invalid_fields_return_422(client):
    """Campos inválidos retornan 422."""
    # name es requerido, enviar payload vacío
    resp = await client.post("/api/v2/enterprise/onboarding/company", json={})
    assert resp.status_code == 422
