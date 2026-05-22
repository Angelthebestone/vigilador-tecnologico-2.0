"""Mock config endpoints: workstream toggles and prompt editor.

Sirve los mismos prompts reales que el backend (los archivos en
src/vigilancia_multiagente/prompts/evaluation/) para que la pestaña 4
del frontend pueda revisarse contra contenido de producción.

Cada prompt tiene tres "variantes" editables:
    - kind="system"        → <name>.txt              (instrucciones)
    - kind="example_user"  → <name>.example_user.txt (few-shot user)
    - kind="example_ai"    → <name>.example_ai.txt   (few-shot assistant)
"""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/config")

# In-memory state
_active_workstreams: dict[str, bool] = {
    "ws_a": True, "ws_b": True, "ws_c": True, "ws_d": True, "ws_e": True,
}

# Overrides indexed by (name, kind) so each variant has its own override.
_prompt_overrides: dict[tuple[str, str], str] = {}

VALID_PROMPT_NAMES = (
    "assumption_detection", "counterfactual", "falsification", "query_expand",
    "stakeholder_academic", "stakeholder_competitor",
    "stakeholder_investor", "stakeholder_regulator",
)

VALID_KINDS = ("system", "example_user", "example_ai")
Kind = Literal["system", "example_user", "example_ai"]


_PROMPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "vigilancia_multiagente"
    / "prompts"
    / "evaluation"
)


def _path_for(name: str, kind: str) -> Path:
    if kind == "system":
        return _PROMPTS_DIR / f"{name}.txt"
    if kind == "example_user":
        return _PROMPTS_DIR / f"{name}.example_user.txt"
    if kind == "example_ai":
        return _PROMPTS_DIR / f"{name}.example_ai.txt"
    raise ValueError(f"Unknown kind: {kind}")


def _load_default(name: str, kind: str = "system") -> str:
    """Carga el archivo real desde disco; si falla, retorna cadena vacía.

    No cachea para que las ediciones en disco se reflejen al instante en la
    pestaña de configuración del frontend durante desarrollo.
    """
    try:
        return _path_for(name, kind).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""


def get_active_workstreams() -> dict[str, bool]:
    return dict(_active_workstreams)


@router.get("/workstreams")
async def get_workstreams() -> dict:
    return dict(_active_workstreams)


@router.patch("/workstreams")
async def patch_workstreams(body: dict) -> dict:
    valid = {"ws_a", "ws_b", "ws_c", "ws_d", "ws_e"}
    for key in body:
        if key not in valid:
            raise HTTPException(status_code=422, detail=f"Invalid key: {key}")
        if not isinstance(body[key], bool):
            raise HTTPException(status_code=422, detail=f"Value for {key} must be boolean")
    _active_workstreams.update({k: v for k, v in body.items() if k in valid})
    return {**_active_workstreams, "applies_to": "next_session"}


@router.get("/workstreams/health")
async def get_health() -> dict:
    return {
        "ws_a": {"available": True, "missing_dependencies": [], "degraded_services": []},
        "ws_b": {"available": True, "missing_dependencies": [], "degraded_services": []},
        "ws_c": {"available": True, "missing_dependencies": [], "degraded_services": []},
        "ws_d": {"available": True, "missing_dependencies": [], "degraded_services": ["openalex_timeout"]},
        "ws_e": {"available": True, "missing_dependencies": ["google_factcheck_api_key"], "degraded_services": []},
    }


def _is_modified(name: str, kind: str) -> bool:
    return (name, kind) in _prompt_overrides


def _content(name: str, kind: str) -> str:
    override = _prompt_overrides.get((name, kind))
    if override is not None:
        return override
    return _load_default(name, kind)


@router.get("/prompts")
async def get_prompts() -> dict:
    """Lista las 8 plantillas con metadatos agregados de las 3 variantes.

    `modified` aquí es True si CUALQUIER variante (system/example_user/
    example_ai) tiene override; `size` cuenta solo el system para mantener
    compatibilidad con el listado original del frontend.
    """
    templates = []
    for name in VALID_PROMPT_NAMES:
        modified_any = any(_is_modified(name, k) for k in VALID_KINDS)
        size = len(_content(name, "system").encode("utf-8"))
        variants = {
            k: {
                "available": bool(_load_default(name, k)) or _is_modified(name, k),
                "modified": _is_modified(name, k),
                "size": len(_content(name, k).encode("utf-8")),
            }
            for k in VALID_KINDS
        }
        templates.append({
            "name": name,
            "modified": modified_any,
            "size": size,
            "variants": variants,
        })
    return {"templates": templates}


@router.get("/prompts/{name}")
async def get_prompt(
    name: str,
    kind: str = Query("system", pattern="^(system|example_user|example_ai)$"),
) -> dict:
    if name not in VALID_PROMPT_NAMES:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    default = _load_default(name, kind)
    override = _prompt_overrides.get((name, kind))
    modified = override is not None
    content = override if override is not None else default
    size = len(content.encode("utf-8"))
    return {
        "name": name,
        "kind": kind,
        "content": content,
        "modified": modified,
        "default_content": default,
        "size": size,
    }


@router.put("/prompts/{name}")
async def put_prompt(
    name: str,
    body: dict,
    kind: str = Query("system", pattern="^(system|example_user|example_ai)$"),
) -> dict:
    if name not in VALID_PROMPT_NAMES:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    content = body.get("content", "")
    if not isinstance(content, str):
        raise HTTPException(status_code=422, detail="Content must be string")
    # example_* puede ser vacío para "deshabilitar el few-shot"; system no.
    if kind == "system" and not content.strip():
        raise HTTPException(status_code=422, detail="Content required for system")
    if len(content.encode("utf-8")) > 100 * 1024:
        raise HTTPException(status_code=422, detail="Content exceeds 100KB")
    _prompt_overrides[(name, kind)] = content
    return {
        "name": name,
        "kind": kind,
        "modified": True,
        "size": len(content.encode("utf-8")),
    }


@router.post("/prompts/{name}/restore")
async def restore_prompt(
    name: str,
    kind: str = Query("system", pattern="^(system|example_user|example_ai)$"),
) -> dict:
    if name not in VALID_PROMPT_NAMES:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    _prompt_overrides.pop((name, kind), None)
    return {"name": name, "kind": kind, "modified": False, "restored": True}
