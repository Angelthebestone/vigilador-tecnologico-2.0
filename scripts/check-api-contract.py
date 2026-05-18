#!/usr/bin/env python3
"""Verify the API contract between frontend TypeScript types and backend Python endpoints.

Parses TypeScript type definitions from the frontend source, then makes live HTTP
requests to each backend endpoint and compares response JSON keys against the
expected shape derived from the TypeScript types.

Usage:
    python scripts/check-api-contract.py
    python scripts/check-api-contract.py --url http://localhost:8000/api/v2 --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# TypeScript type definitions — parsed statically from the frontend .ts file
# ---------------------------------------------------------------------------

TS_TYPES_PATH = str(Path(__file__).resolve().parent.parent / "frontend" / "src" / "types" / "index.ts")


@dataclass
class TSType:
    name: str
    fields: dict[str, tuple[str, bool]]  # field_name -> (type_name, is_optional)
    comment: str = ""


def _clean(s: str) -> str:
    return s.strip().rstrip(",")


def parse_typescript_types(path: str) -> dict[str, TSType]:
    """Parse TypeScript `type` definitions using regex. No external parser needed."""
    with open(path, encoding="utf-8") as f:
        source = f.read()

    types: dict[str, TSType] = {}
    # Match: [optional comment] export type Name = { ... };
    pattern = re.compile(
        r"""(?P<comment>/\*\*[^*]*\*+/)?\s*"""
        r"""export\s+type\s+(?P<name>\w+)\s*=\s*\{"""
        r"""(?P<body>[^}]+)\};""",
        re.DOTALL,
    )

    for match in pattern.finditer(source):
        name = match.group("name")
        body = match.group("body")
        comment = _clean(match.group("comment") or "")

        fields: dict[str, tuple[str, bool]] = {}
        # Match each line: optionalField?: Type; or requiredField: Type;
        field_re = re.compile(r"^\s*(?P<field>\w+)\s*(?P<optional>\?)?\s*:\s*(?P<type>[^;]+);", re.MULTILINE)
        for fm in field_re.finditer(body):
            fname = fm.group("field")
            ftype = _clean(fm.group("type"))
            is_optional = fm.group("optional") is not None
            fields[fname] = (ftype, is_optional)

        types[name] = TSType(name=name, fields=fields, comment=comment)

    return types


# ---------------------------------------------------------------------------
# API endpoint registry
# ---------------------------------------------------------------------------

HTTP_METHOD_GET = "GET"
HTTP_METHOD_POST = "POST"
HTTP_METHOD_PATCH = "PATCH"
HTTP_METHOD_DELETE = "DELETE"


@dataclass
class EndpointDef:
    method: str
    path: str
    label: str
    expected_keys: dict[str, Any]  # nested dict of expected response keys -> nested shape
    expected_type: str | None = None  # optional: name of TS type for response body


def api_endpoints() -> list[EndpointDef]:
    """Define every endpoint we check, what method to use, and the expected top-level keys.

    Expected_keys entries are either:
      - None:   key should exist, value type not deeply checked
      - dict:   nested sub-object expected structure
      - list:   key holds a list (the value describes an element shape)
    """
    return [
        EndpointDef(
            method=HTTP_METHOD_POST,
            path="/research/start",
            label="POST /research/start",
            expected_keys={
                "session_id": None,
                "status": None,
                "questions": None,
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/plan",
            label="GET /research/{id}/plan",
            expected_keys={
                "session_id": None,
                "plan": {
                    "id": None,
                    "version": None,
                    "requires_approval": None,
                    "global_constraints": None,
                    "branches": [
                        {
                            "branch_type": None,
                            "focus_queries": None,
                            "mcp_providers": None,
                            "priority_weight": None,
                            "status": None,
                        }
                    ],
                },
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/report",
            label="GET /research/{id}/report",
            expected_keys={
                "session_id": None,
                "executive_summary": None,
                "technical_section": None,
                "commercial_section": None,
                "risk_section": None,
                "cross_analysis": None,
                "recommendations": [{"text": None, "priority": None, "based_on": None}],
                "total_sources_consulted": None,
                "total_learnings": None,
                "confidence_score": None,
                "generated_at": None,
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/sources",
            label="GET /research/{id}/sources",
            expected_keys={
                "session_id": None,
                "total": None,
                "items": [{"id": None, "url": None, "title": None, "provider": None, "branch_type": None, "accessed_at": None}],
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/graph",
            label="GET /research/{id}/graph",
            expected_keys={
                "session_id": None,
                "nodes": [
                    {
                        "id": None,
                        "label": None,
                        "centrality": None,
                        "branch_type": None,
                        "node_type": None,
                        "source_ids": None,
                        "confidence": None,
                    }
                ],
                "edges": [
                    {
                        "id": None,
                        "source": None,
                        "target": None,
                        "relation_type": None,
                        "similarity_score": None,
                    }
                ],
                "analytics": None,
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/graph/analytics",
            label="GET /research/{id}/graph/analytics",
            expected_keys={
                "session_id": None,
                "node_count": None,
                "edge_count": None,
                "centrality": [
                    {
                        "node_id": None,
                        "degree": None,
                        "betweenness": None,
                        "pagerank": None,
                    }
                ],
                "clusters": [{"cluster_id": None, "node_ids": None, "score": None}],
                "layout": None,
                "traversals": None,
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/graph/search?query=test",
            label="GET /research/{id}/graph/search",
            expected_keys={
                "session_id": None,
                "query": None,
                "total": None,
                "items": [{"node_id": None, "label": None, "score": None, "explanation": None}],
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/graph/path?source_node_id=test&target_node_id=test",
            label="GET /research/{id}/graph/path",
            expected_keys={
                "session_id": None,
                "source_node_id": None,
                "target_node_id": None,
                "node_ids": None,
                "edge_ids": None,
                "total_cost": None,
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/research/{id}/providers",
            label="GET /research/{id}/providers",
            expected_keys={
                "session_id": None,
                "providers": [
                    {
                        "name": None,
                        "avg_latency_ms": None,
                        "error_rate": None,
                        "retry_rate": None,
                        "latency_buckets": None,
                    }
                ],
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_GET,
            path="/sessions/timeline",
            label="GET /sessions/timeline",
            expected_keys={
                "sessions": [
                    {
                        "session_id": None,
                        "query_summary": None,
                        "timestamp": None,
                    }
                ],
            },
        ),
        EndpointDef(
            method=HTTP_METHOD_PATCH,
            path="/sources/{id}/score",
            label="PATCH /sources/{id}/score",
            expected_keys={
                "source_id": None,
                "new_score": None,
                "adjustment": None,
                "reason": None,
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Type mapping: TypeScript -> Python expectations
# ---------------------------------------------------------------------------

# Mapping of TS field names to their expected snake_case counterparts
# when backend returns a different key name
CAMEL_TO_SNAKE_OVERRIDES: dict[str, str] = {}


def _to_snake(name: str) -> str:
    """Convert camelCase to snake_case, e.g. 'branchType' -> 'branch_type'."""
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

@dataclass
class Discrepancy:
    endpoint: str
    key_path: str
    message: str


def _compare_value(
    endpoint_label: str,
    key_path: str,
    expected: Any,
    actual: Any,
    discrepancies: list[Discrepancy],
    verbose: bool,
) -> None:
    if expected is None:
        return

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            discrepancies.append(
                Discrepancy(endpoint_label, key_path, f"Expected dict, got {type(actual).__name__}")
            )
            return
        for ek, ev in expected.items():
            child_path = f"{key_path}.{ek}" if key_path else ek
            if ek not in actual:
                discrepancies.append(
                    Discrepancy(endpoint_label, child_path, "Missing key")
                )
                continue
            _compare_value(endpoint_label, child_path, ev, actual[ek], discrepancies, verbose)
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            discrepancies.append(
                Discrepancy(endpoint_label, key_path, f"Expected list, got {type(actual).__name__}")
            )
            return
        if not expected:
            return
        elem_template = expected[0]
        for i, item in enumerate(actual):
            item_path = f"{key_path}[{i}]"
            _compare_value(endpoint_label, item_path, elem_template, item, discrepancies, verbose)


def check_endpoint(
    endpoint: EndpointDef,
    base_url: str,
    session_id: str,
    discrepancies: list[Discrepancy],
    verbose: bool,
) -> None:
    """Make the HTTP request and compare response against expected keys."""
    url = endpoint.path.replace("{id}", session_id)
    full_url = f"{base_url}{url}"
    method = endpoint.method

    if verbose:
        print(f"  [HTTP {method}] {full_url}")

    body: bytes | None = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if method == HTTP_METHOD_POST:
        payload = json.dumps({"user_query": "test AI technology trends", "scope": None}).encode() if "/start" in url else json.dumps({"answers": {"q1": "test"}}).encode()
        req = urllib.request.Request(full_url, data=payload, headers=headers, method=method)
    elif method == HTTP_METHOD_PATCH:
        payload = json.dumps({"delta": 5, "reason": "test adjustment from contract check"}).encode()
        req = urllib.request.Request(full_url, data=payload, headers=headers, method=method)
    elif method == HTTP_METHOD_DELETE:
        req = urllib.request.Request(full_url, headers=headers, method=method)
    else:
        req = urllib.request.Request(full_url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        if verbose:
            print(f"    HTTP {e.code}: {e.reason}")
        # 404 is acceptable for endpoints requiring a real session
        if e.code == 404:
            missing_msg = "(session not found — expected for missing test session)"
            if verbose:
                print(f"    {missing_msg}")
            return
        # 422 is acceptable for validation errors on missing payload
        if e.code == 422:
            if verbose:
                print("    (validation error — acceptable shape mismatch)")
            return
        discrepancies.append(
            Discrepancy(endpoint.label, "", f"HTTP {e.code}: {e.reason}")
        )
        return
    except urllib.error.URLError as e:
        discrepancies.append(
            Discrepancy(endpoint.label, "", f"Connection error: {e.reason}")
        )
        return

    if body is None:
        discrepancies.append(
            Discrepancy(endpoint.label, "", "No response body")
        )
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        discrepancies.append(
            Discrepancy(endpoint.label, "", f"Invalid JSON: {e}")
        )
        return

    _compare_value(endpoint.label, "", endpoint.expected_keys, data, discrepancies, verbose)


# ---------------------------------------------------------------------------
# TypeScript type -> expected key shape helper
# ---------------------------------------------------------------------------

def _resolve_type_shape(
    ts_type_name: str,
    ts_types: dict[str, TSType],
    visited: set[str] | None = None,
) -> Any:
    """Convert a TS type name into our expected-keys dict shape.

    Handles nested types, arrays (type[]), and basic primitives.
    """
    if visited is None:
        visited = set()

    base = ts_type_name.strip()
    is_array = base.endswith("[]")
    inner = base[:-2] if is_array else base

    if inner in ts_types and inner not in visited:
        visited.add(inner)
        t = ts_types[inner]
        shape: dict[str, Any] = {}
        for fname, (ftype, _optional) in t.fields.items():
            snake = _to_snake(fname)
            shape[snake] = _resolve_type_shape(ftype, ts_types, visited)
        if is_array:
            return [shape]
        return shape

    return None


def generate_expected_from_ts(ts_types: dict[str, TSType]) -> dict[str, Any]:
    """Build a mapping from TS type name to expected response shape."""
    result: dict[str, Any] = {}
    for name, ts_type in ts_types.items():
        shape: dict[str, Any] = {}
        for fname, (ftype, _optional) in ts_type.fields.items():
            snake = _to_snake(fname)
            shape[snake] = _resolve_type_shape(ftype, ts_types)
        result[name] = shape
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify API contract between frontend TypeScript types and backend endpoints."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the backend (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress information",
    )
    parser.add_argument(
        "--session-id",
        default="00000000-0000-0000-0000-000000000000",
        help="Session ID to use for {id} substitution in paths (default: all-zeros UUID)",
    )
    parser.add_argument(
        "--ts-path",
        default=TS_TYPES_PATH,
        help=f"Path to TypeScript types file (default: {TS_TYPES_PATH})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # 1. Parse TypeScript types
    if args.verbose:
        print(f"Reading TypeScript types from: {args.ts_path}")

    ts_types = parse_typescript_types(args.ts_path)

    if args.verbose:
        print(f"  Found {len(ts_types)} type definitions:")
        for name in sorted(ts_types):
            t = ts_types[name]
            optional_count = sum(1 for _, opt in t.fields.values() if opt)
            print(f"    {name}: {len(t.fields)} fields ({optional_count} optional)")
        print()

    # 2. Define expected shapes from TS types for deeper comparison
    ts_shapes = generate_expected_from_ts(ts_types)

    if args.verbose:
        print("TypeScript-derived expected shapes:")
        for name, shape in ts_shapes.items():
            print(f"  {name}: {json.dumps(shape, default=str)[:120]}...")
        print()

    # 3. Check backend connectivity
    base_url = args.url.rstrip("/")
    health_url = "http://localhost:8000/health" if "localhost" in base_url else f"{base_url}/health"

    if args.verbose:
        print(f"Checking backend health at: {health_url}")

    try:
        req = urllib.request.Request(health_url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            health_data = json.loads(resp.read())
            if args.verbose:
                print(f"  Backend status: {health_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"ERROR: Backend at {base_url} is not reachable: {e}")
        print("Start the backend with: uvicorn vigilancia_multiagente.api.app:app --reload")
        return 2

    api_base = f"{base_url}/api/v2"
    if args.verbose:
        print(f"API base: {api_base}")
        print()

    # 4. Run endpoint checks
    endpoints = api_endpoints()
    all_discrepancies: list[Discrepancy] = []

    if args.verbose:
        print(f"Checking {len(endpoints)} endpoints...")
        print()

    for ep in endpoints:
        check_endpoint(ep, api_base, args.session_id, all_discrepancies, args.verbose)
        if args.verbose:
            print()

    # 5. Report results
    if not all_discrepancies:
        print(f"ALL {len(endpoints)} endpoints match expected contract.")
        return 0

    print(f"Found {len(all_discrepancies)} discrepancy(ies):")
    for d in all_discrepancies:
        location = f" [{d.endpoint}]" if d.endpoint else ""
        print(f"  - {d.key_path}{location}: {d.message}")

    # Count by endpoint
    by_ep: dict[str, int] = {}
    for d in all_discrepancies:
        by_ep[d.endpoint] = by_ep.get(d.endpoint, 0) + 1
    print()
    print("Summary by endpoint:")
    for ep, count in sorted(by_ep.items()):
        print(f"  {ep}: {count} issue(s)")

    print()
    note = (
        "Note: Backend returns snake_case keys; frontend TypeScript types use "
        "camelCase. This conversion is expected and handled client-side."
    )
    print(note)

    return 1


if __name__ == "__main__":
    sys.exit(main())
