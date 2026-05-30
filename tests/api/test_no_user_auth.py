"""T046 — verify spec 021 D4: user authentication is removed.

Asserts:
1. The user-auth route module is gone (`enterprise_auth.py`).
2. The user-auth router is no longer registered in `api.router`.
3. `app.state.active_tokens` is no longer initialized in the lifespan.
4. The OAuth-of-service module (`oauth_manager.py`) is preserved (D4 keeps
   it for ingestion connectors).

These are static module-level assertions — they pass even if the FastAPI app
is not built, so they survive any import error caused by stale references.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_enterprise_auth_module_is_deleted() -> None:
    auth_path = (
        REPO_ROOT
        / "src"
        / "vigilancia_multiagente"
        / "api"
        / "routes"
        / "enterprise_auth.py"
    )
    assert not auth_path.exists(), (
        f"enterprise_auth.py must be deleted by spec 021 D4 (T047). "
        f"Still present at {auth_path}."
    )


def test_router_module_does_not_import_enterprise_auth() -> None:
    router_module = importlib.import_module("vigilancia_multiagente.api.router")
    source = inspect.getsource(router_module)
    assert "enterprise_auth" not in source, (
        "api/router.py still references enterprise_auth (T048 must remove "
        "import + include_router)."
    )


def test_app_lifespan_does_not_initialize_active_tokens() -> None:
    app_module = importlib.import_module("vigilancia_multiagente.api.app")
    source = inspect.getsource(app_module)
    assert "active_tokens" not in source, (
        "api/app.py still references app.state.active_tokens (T051 must "
        "remove user-token state)."
    )


def test_oauth_manager_is_preserved() -> None:
    """D4 keeps service OAuth (Drive/Gmail) — only USER auth is removed."""
    oauth_module = importlib.import_module(
        "vigilancia_multiagente.enterprise.auth.oauth_manager"
    )
    assert oauth_module is not None
    # Smoke check: the module exposes a manager class or function
    members = [name for name in dir(oauth_module) if not name.startswith("_")]
    assert members, "oauth_manager.py must keep its public API for connectors."
