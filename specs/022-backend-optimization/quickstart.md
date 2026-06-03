# Quickstart: Backend Optimization 022

**Phase 1 quickstart**. Cómo arrancar la implementación inmediatamente.

## Pre-requisites

- Python 3.11+ (verificar `python --version`)
- pyenv o virtualenv activos
- Tests baseline en verde:
  ```powershell
  python -m pytest tests/test_orchestrator.py tests/application/execution/ tests/application/evaluation/ tests/enterprise/governance/test_audit_log -x
  ```
  → debe ser 100% verde antes de iniciar Ola 1.

## Setup inicial (una sola vez)

```powershell
# 1. Verificar working dir
cd "C:\Users\Lenovo\Desktop\vigilador tecnologico 2.0"

# 2. Snapshot LOC pre-cambios para SC-011
$preLOC = (Get-ChildItem -Recurse src tests -Filter "*.py" | Get-Content | Measure-Object -Line).Lines
$preLOC | Out-File specs\022-backend-optimization\baselines\loc-pre.txt

# 3. Snapshot tests count pre-cambios para SC-008
$preTests = python -m pytest tests/ --collect-only -q 2>&1 | Select-String "tests collected" | ForEach-Object { $_.Line }
$preTests | Out-File specs\022-backend-optimization\baselines\tests-pre.txt

# 4. Snapshot diff de 2.0 (para SC-010)
git diff --stat src/vigilancia_multiagente/application/execution/ src/vigilancia_multiagente/application/evaluation/ | Out-File specs\022-backend-optimization\baselines\baseline-2.0.txt
```

## Comando gate sagrado (ejecutar antes y después de cada ola)

```powershell
$gate = @(
  "tests/test_orchestrator.py",
  "tests/application/execution/",
  "tests/application/evaluation/",
  "tests/enterprise/governance/test_audit_log_wiring.py",
  "tests/enterprise/governance/test_audit_log.py",
  "tests/enterprise/orchestration/test_dispatcher.py",
  "tests/api/routes/"
)
python -m pytest @gate -x --tb=short
```

## Por dónde empezar — Ola 1 (Infra base)

### 1. Crear estructura de directorios

```powershell
mkdir -Force src\vigilancia_multiagente\enterprise\tooling\builtin\_base
ni src\vigilancia_multiagente\enterprise\tooling\builtin\_base\__init__.py -Type File
```

### 2. Implementar `BaseHTTPProvider`

Ver contrato completo en [contracts/base_http_provider.md](contracts/base_http_provider.md).

Snippet inicial (R-04 de research):

```python
# src/vigilancia_multiagente/enterprise/tooling/builtin/_base/http_provider.py
from __future__ import annotations
import os
from typing import Any, ClassVar
import httpx
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


class ProviderError(RuntimeError):
    """Base class for provider errors."""


class ProviderUnconfiguredError(ProviderError):
    """Missing required api_key in environment."""


class BaseHTTPProvider:
    name: ClassVar[str]
    domain: ClassVar[str]
    base_url: ClassVar[str]
    auth_env_var: ClassVar[str | None] = None
    requires_auth: ClassVar[bool] = True
    is_external_mcp: ClassVar[bool] = False

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=5.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _api_key(self) -> str | None:
        return os.environ.get(self.auth_env_var) if self.auth_env_var else None

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    # post(), get(), healthcheck() — implementar con retry policy
```

### 3. Implementar tests primero (TDD)

```python
# tests/enterprise/tooling/test_base_http_provider.py
import respx
from httpx import Response, AsyncClient
import pytest


class _StubProvider(BaseHTTPProvider):
    name = "stub"
    domain = "test"
    base_url = "https://stub.example.com"
    auth_env_var = "STUB_API_KEY"

    async def execute(self, tool_name, args):
        return await self.post("/api/echo", json=args)


@respx.mock
async def test_retry_on_503_recovers(monkeypatch):
    monkeypatch.setenv("STUB_API_KEY", "secret")
    p = _StubProvider()
    route = respx.post("https://stub.example.com/api/echo").mock(
        side_effect=[Response(503), Response(503), Response(200, json={"ok": True})]
    )
    result = await p.execute("test", {"x": 1})
    assert result == {"ok": True}
    assert route.call_count == 3
    await p.aclose()
```

Ejecutar:
```powershell
python -m pytest tests/enterprise/tooling/test_base_http_provider.py -x
```

### 4. Verificar gate sagrado

```powershell
python -m pytest @gate -x
```
→ debe seguir verde. Ola 1 termina aquí.

## Decisiones a confirmar durante implementación

Ver [research.md](research.md) — todos resueltos:
- **R-01**: versiones SDK pinneadas → confirmar al añadir a pyproject.
- **R-02**: Gemini batchEmbedContents → confirmar API shape al implementar Phase 3.
- **R-03**: google-workspace-mcp source repo → verify Taylor Wilsdon en GitHub al implementar Phase 4.

## Si algo se rompe

**Ante test rojo en gate sagrado**:
1. NO continuar a la siguiente ola.
2. Identificar archivo culpable: `python -m pytest <test> --tb=long`.
3. Revertir solo ese archivo: `git checkout <archivo>`.
4. Re-correr tests. Si verde, analizar la diferencia conceptual.
5. Si no, escalar: el cambio era incompatible → re-diseñar la migration.

**Rollback completo de una ola**:
```powershell
# Ola 1: rm los nuevos archivos (no había modificaciones)
rm -r src\vigilancia_multiagente\enterprise\tooling\builtin\_base
rm src\vigilancia_multiagente\infra\embeddings\embedding_cache.py
rm tests\enterprise\tooling\test_base_http_provider.py
rm tests\infra\embeddings\test_embedding_cache.py

# Olas 2-6: cada cambio fue git-tracked, revertir con
git checkout <archivo>
git restore --staged <archivo>  # si fue staged
```

## Verificación final del spec (al cerrar 6 olas)

```powershell
# 1. Todos los SCs medidos
python -m pytest tests/ -q  # SC-008 + SC-013
$postLOC = (Get-ChildItem -Recurse src tests -Filter "*.py" | Get-Content | Measure-Object -Line).Lines
echo "LOC delta: $((($postLOC - $preLOC) / $preLOC) * 100)%"  # SC-011 (-5%)

# 2. 0 archivos >400 LOC
Get-ChildItem -Recurse src -Filter "*.py" | ForEach-Object {
  $loc = (Get-Content $_.FullName | Measure-Object -Line).Lines
  if ($loc -gt 400) { Write-Output "$($_.FullName): $loc" }
}  # SC-009

# 3. 0 cambios en 2.0
git diff --stat src/vigilancia_multiagente/application/execution/ src/vigilancia_multiagente/application/evaluation/  # SC-010

# 4. Layer-imports limpio
python scripts/check-layer-imports.py  # SC-012

# 5. Provider contract
python -m pytest tests/enterprise/tooling/test_provider_contract.py -v  # SC-013

# 6. Capabilities count
curl http://localhost:8000/api/v2/enterprise/tools | jq '. | length'  # SC-014 (>=45)
```

## Recursos

- Spec completo: [spec.md](spec.md)
- Plan técnico: [plan.md](plan.md)
- Research: [research.md](research.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/](contracts/)
- Síntesis técnica previa: [../../docs/optimization/synthesis_plan_v1.md](../../docs/optimization/synthesis_plan_v1.md)

## Siguientes pasos

1. Ejecutar Ola 1 (Phase 1 del plan).
2. Verificar suite gate verde.
3. Avanzar a Ola 2 (`/speckit.tasks` desde el cierre de este plan).

**Política**: NO commits/pushes hasta solicitud explícita del usuario.
