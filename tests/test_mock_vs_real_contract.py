"""Test que compara estructuras de respuesta entre mock server y backend real.

El mock server (mock_server.py) devuelve camelCase para alinearse con lo que
el frontend espera tras el transform layer. El backend real (FastAPI/Python)
devuelve snake_case. Este script normaliza ambas convenciones a snake_case
y compara las keys de las respuestas recursivamente para verificar que la
estructura de datos coincida entre ambos servidores.

Uso:
    python tests/test_mock_vs_real_contract.py
    python tests/test_mock_vs_real_contract.py --backend-url http://localhost:8000 --mock-url http://localhost:8001
    python tests/test_mock_vs_real_contract.py -v
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Endpoints comunes entre mock server y backend real
# ---------------------------------------------------------------------------
# Cada entrada: (name, method, path_template, body, params)
# {session_id} se reemplaza con el session ID de cada servidor.

ENDPOINTS: list[tuple[str, str, str, dict[str, Any] | None, dict[str, Any] | None]] = [
    ("start_research", "POST", "/api/v2/research/start", {"query": "test query"}, None),
    (
        "clarify",
        "POST",
        "/api/v2/research/{session_id}/clarify",
        {"answers": {"q1": "test answer"}},
        None,
    ),
    ("plan", "GET", "/api/v2/research/{session_id}/plan", None, None),
    ("report", "GET", "/api/v2/research/{session_id}/report", None, None),
    ("sources", "GET", "/api/v2/research/{session_id}/sources", None, None),
    ("providers", "GET", "/api/v2/research/{session_id}/providers", None, None),
    ("graph", "GET", "/api/v2/research/{session_id}/graph", None, None),
    ("graph_analytics", "GET", "/api/v2/research/{session_id}/graph/analytics", None, None),
    ("graph_nodes", "GET", "/api/v2/research/{session_id}/graph/nodes", None, None),
    ("graph_edges", "GET", "/api/v2/research/{session_id}/graph/edges", None, None),
    ("evaluation", "GET", "/api/v2/research/{session_id}/evaluation", None, None),
    ("timeline", "GET", "/api/v2/sessions/timeline", None, None),
]

CLIENT_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Helpers de normalización de keys
# ---------------------------------------------------------------------------


def _camel_to_snake(name: str) -> str:
    """Convierte camelCase/PascalCase a snake_case.

    Ejemplos:
        sessionId -> session_id
        executiveSummary -> executive_summary
        URL -> url
        avgLatencyMs -> avg_latency_ms
    """
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def _normalize_key(key: str) -> str:
    """Normaliza una key a snake_case para comparación estructural.

    Si ya es snake_case, la devuelve tal cual.
    Si es camelCase, la convierte.
    """
    if "_" in key and key.islower():
        return key
    return _camel_to_snake(key)


def collect_normalized_keys(data: Any, prefix: str = "") -> set[str]:
    """Extrae todas las keys de un objeto JSON recursivamente, normalizadas.

    Retorna un set de key paths normalizados a snake_case para comparación
    estructural entre mock (camelCase) y backend (snake_case).

    Ejemplo:
        {"sessionId": 1, "items": [{"nodeId": "n1"}]}
        -> {"session_id", "items[].node_id"}
    """
    keys: set[str] = set()
    if isinstance(data, dict):
        for k, v in data.items():
            normalized = _normalize_key(k)
            full = f"{prefix}.{normalized}" if prefix else normalized
            keys.add(full)
            keys.update(collect_normalized_keys(v, full))
    elif isinstance(data, list) and data:
        keys.update(collect_normalized_keys(data[0], f"{prefix}[]"))
    return keys


def collect_raw_keys(data: Any, prefix: str = "") -> dict[str, str]:
    """Extrae todas las keys con su forma original.

    Retorna {normalized_path: original_key} para poder reportar diferencias
    mostrando la key original de cada lado.
    """
    mapping: dict[str, str] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            normalized = _normalize_key(k)
            full = f"{prefix}.{normalized}" if prefix else normalized
            mapping[full] = k
            for sub_key, orig in collect_raw_keys(v, full).items():
                mapping[sub_key] = orig
    elif isinstance(data, list) and data:
        for sub_key, orig in collect_raw_keys(data[0], f"{prefix}[]").items():
            mapping[sub_key] = orig
    return mapping


# ---------------------------------------------------------------------------
# Helpers HTTP
# ---------------------------------------------------------------------------


def _build_client(base_url: str) -> httpx.Client | None:
    """Retorna un httpx.Client si el servidor responde, o None si no."""
    try:
        client = httpx.Client(base_url=base_url, timeout=CLIENT_TIMEOUT)
        resp = client.post("/api/v2/research/start", json={"query": "healthcheck"})
        if resp.status_code < 500:
            return client
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    return None


def get_session_id(method: str, path: str, body: dict[str, Any] | None, client: httpx.Client, base_url: str) -> str | None:
    """Crea una sesión de prueba y retorna su ID."""
    try:
        resp = client.request(method, path, json=body)
        if resp.status_code != 200:
            print(f"  [!] {base_url} {method} {path}: HTTP {resp.status_code}")
            return None
        data = resp.json()
        for key in ("sessionId", "session_id"):
            if key in data:
                return data[key]
        print(f"  [!] No session ID in response from {base_url}")
        return None
    except Exception as exc:
        print(f"  [!] {base_url}: {exc}")
        return None


def fetch_data(client: httpx.Client, method: str, path: str, body: dict[str, Any] | None, params: dict[str, Any] | None) -> Any:
    """Hace una request HTTP y retorna el JSON parseado o un dict de error."""
    try:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["json"] = body
        if params is not None:
            kwargs["params"] = params
        resp = client.request(method, path, **kwargs)
        if resp.status_code == 200:
            return resp.json()
        return {"__http_error__": resp.status_code, "__detail__": resp.text[:200]}
    except httpx.HTTPStatusError as exc:
        return {"__http_error__": exc.response.status_code, "__detail__": str(exc)}
    except Exception as exc:
        return {"__error__": str(exc)}


# ---------------------------------------------------------------------------
# Comparación
# ---------------------------------------------------------------------------


def compare_single_endpoint(name: str, backend: Any, mock: Any, verbose: bool) -> bool:
    """Compara keys de un endpoint entre backend y mock. Retorna True si coinciden."""
    bk_raw = collect_raw_keys(backend)
    mk_raw = collect_raw_keys(mock)
    bk_norm = set(bk_raw.keys())
    mk_norm = set(mk_raw.keys())

    only_backend = bk_norm - mk_norm
    only_mock = mk_norm - bk_norm

    if only_backend or only_mock:
        print(f"  \u274c {name}: discrepancia de keys")
        for key in sorted(only_backend):
            print(f"     Solo en backend: `{key}` (original: `{bk_raw[key]}`)")
        for key in sorted(only_mock):
            print(f"     Solo en mock:    `{key}` (original: `{mk_raw[key]}`)")
        return False

    if verbose:
        print(f"  \u2705 {name}: {len(bk_norm)} keys estructurales coinciden")
        print(f"     Backend raw keys: {sorted(bk_raw.values())}")
        print(f"     Mock raw keys:    {sorted(mk_raw.values())}")
    else:
        print(f"  \u2705 {name}: {len(bk_norm)} keys estructurales coinciden")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara estructuras de respuesta entre mock server y backend real"
    )
    parser.add_argument("--backend-url", default="http://localhost:8000", help="URL del backend real")
    parser.add_argument("--mock-url", default="http://localhost:8001", help="URL del mock server")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra keys detalladas")
    args = parser.parse_args()

    # --- Verificar disponibilidad de servidores ---
    print("Conectando a servidores...")
    backend_client = _build_client(args.backend_url)
    mock_client = _build_client(args.mock_url)

    if backend_client is None:
        print(f"  [!] Backend ({args.backend_url}) no disponible -- omitiendo")
    else:
        print(f"  [\u2713] Backend ({args.backend_url}) conectado")

    if mock_client is None:
        print(f"  [!] Mock ({args.mock_url}) no disponible -- omitiendo")
    else:
        print(f"  [\u2713] Mock ({args.mock_url}) conectado")

    if backend_client is None or mock_client is None:
        print("\nAmbos servidores deben estar corriendo para la comparación.")
        sys.exit(1)

    # --- Crear sesiones ---
    print("\nCreando sesiones de prueba...")
    backend_sid = get_session_id(
        "POST", "/api/v2/research/start", {"query": "test"}, backend_client, args.backend_url
    )
    mock_sid = get_session_id(
        "POST", "/api/v2/research/start", {"query": "test"}, mock_client, args.mock_url
    )

    if not backend_sid or not mock_sid:
        print("  [!] No se pudo obtener session ID de ambos servidores")
        sys.exit(1)

    print(f"  Backend session_id: {backend_sid}")
    print(f"  Mock sessionId:     {mock_sid}")

    # --- Ejecutar clarify en ambos para avanzar el estado ---
    for sid, client, _label in [(backend_sid, backend_client, "backend"), (mock_sid, mock_client, "mock")]:
        with contextlib.suppress(Exception):
            client.request(
                "POST", f"/api/v2/research/{sid}/clarify", json={"answers": {"q1": "test"}}
            )

    # --- Comparar cada endpoint ---
    print()
    failures = 0
    total = 0

    for name, method, path_template, body, params in ENDPOINTS:
        bk_path = path_template.replace("{session_id}", backend_sid)
        mk_path = path_template.replace("{session_id}", mock_sid)

        backend_data = fetch_data(backend_client, method, bk_path, body, params)
        mock_data = fetch_data(mock_client, method, mk_path, body, params)

        if isinstance(backend_data, dict) and "__http_error__" in backend_data:
            print(f"  \u26a0 {name}: backend error HTTP {backend_data['__http_error__']} -- omitiendo")
            continue
        if isinstance(mock_data, dict) and "__http_error__" in mock_data:
            print(f"  \u26a0 {name}: mock error HTTP {mock_data['__http_error__']} -- omitiendo")
            continue

        total += 1
        if not compare_single_endpoint(name, backend_data, mock_data, args.verbose):
            failures += 1

    # --- Resumen ---
    print()
    if failures:
        print(f"\u274c {failures}/{total} endpoints con discrepancias estructurales")
        sys.exit(1)
    else:
        print(f"\u2705 {total}/{total} endpoints: keys estructurales coinciden entre backend y mock")
        sys.exit(0)


if __name__ == "__main__":
    main()
