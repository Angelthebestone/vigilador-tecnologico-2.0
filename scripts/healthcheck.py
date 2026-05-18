#!/usr/bin/env python3
"""Healthcheck for Vigilador Tecnologico API v2.

Tests all API endpoints, verifies response structure, and reports status.
Exit code 0 if all pass, 1 otherwise.
"""

import argparse
import contextlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime


def _request(method, url, body=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
            elapsed = time.monotonic() - start
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
        elapsed = time.monotonic() - start
    except urllib.error.URLError as e:
        return 0, b"", time.monotonic() - start, str(e.reason)
    return status, raw, elapsed, None


def main():
    parser = argparse.ArgumentParser(description="Vigilador API healthcheck")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/v2",
        help="Base URL (default: http://localhost:8000/api/v2)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show response keys in detail",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    args = parser.parse_args()

    base = args.url.rstrip("/")
    verbose = args.verbose
    timeout = args.timeout
    started = datetime.now(UTC)

    results = []

    def record(method, path, status, elapsed, ok, present, missing, note=""):
        results.append({
            "method": method,
            "path": path,
            "status": status,
            "elapsed": elapsed,
            "ok": ok,
            "present": present,
            "missing": missing,
            "note": note,
        })

    def check(method, path_template, actual_path, body, expected_keys):
        status, raw, elapsed, err = _request(method, base + actual_path, body, timeout)
        data = None
        if raw:
            with contextlib.suppress(json.JSONDecodeError):
                data = json.loads(raw)
        ok = 200 <= status < 300
        present = []
        missing = []
        if expected_keys is not None:
            if data is None:
                ok = False
                missing = list(expected_keys)
            else:
                for k in expected_keys:
                    (present if k in data else missing).append(k)
                if missing:
                    ok = False
        if err:
            ok = False
        record(method, path_template, status, elapsed, ok, present, missing)
        return data, err

    t0 = time.monotonic()

    # ---------------------------------------------------------------
    # 1. POST /research/start
    # ---------------------------------------------------------------
    session_id = None
    source_id = None
    data, _ = check(
        "POST",
        "/research/start",
        "/research/start",
        {"user_query": "healthcheck"},
        {"session_id", "status", "questions"},
    )
    if data and "session_id" in data:
        session_id = data["session_id"]

    if session_id:
        sid = session_id

        # 2. POST /research/{id}/clarify
        check("POST",
              "/research/{id}/clarify",
              f"/research/{sid}/clarify",
              {"answers": {}},
              {"session_id", "status", "requires_approval", "plan"})

        # 3. GET /research/{id}/plan
        check("GET",
              "/research/{id}/plan",
              f"/research/{sid}/plan",
              None,
              {"session_id", "plan"})

        # 4. POST /research/{id}/approve
        check("POST",
              "/research/{id}/approve",
              f"/research/{sid}/approve",
              {"approved": True},
              {"session_id", "status", "message"})

        # 5. GET /research/{id}/report
        data, _ = check("GET",
                        "/research/{id}/report",
                        f"/research/{sid}/report",
                        None,
                        {"session_id", "executive_summary", "technical_section",
                         "commercial_section", "risk_section", "cross_analysis",
                         "recommendations", "total_sources_consulted",
                         "total_learnings", "confidence_score", "generated_at"})

        # 6. GET /research/{id}/sources  (also extract first source_id)
        source_id = None
        data, _ = check("GET",
                        "/research/{id}/sources",
                        f"/research/{sid}/sources",
                        None,
                        {"session_id", "total", "items"})
        if data and isinstance(data.get("items"), list) and data["items"]:
            source_id = data["items"][0].get("id")

        # 7. GET /research/{id}/graph
        check("GET",
              "/research/{id}/graph",
              f"/research/{sid}/graph",
              None,
              {"session_id", "nodes", "edges", "analytics"})

        # 8. GET /research/{id}/graph/analytics
        check("GET",
              "/research/{id}/graph/analytics",
              f"/research/{sid}/graph/analytics",
              None,
              {"session_id", "node_count", "edge_count", "centrality",
               "clusters", "layout", "traversals"})

        # 9. GET /research/{id}/providers
        check("GET",
              "/research/{id}/providers",
              f"/research/{sid}/providers",
              None,
              {"session_id", "providers"})

        # 10. GET /sessions/timeline
    check("GET",
          "/sessions/timeline",
          "/sessions/timeline",
          None,
          {"sessions"})

    if session_id:
        # 11. POST /sessions/{id}/ask
        data, _ = check("POST",
                        "/sessions/{id}/ask",
                        f"/sessions/{session_id}/ask",
                        {"query": "test"},
                        None)

        # 12. PATCH /sources/{id}/score  (needs source_id from step 6)
        if source_id:
            check("PATCH",
                  "/sources/{id}/score",
                  f"/sources/{source_id}/score",
                  {"delta": 1, "reason": "test"},
                  {"source_id", "new_score", "adjustment", "reason"})
        else:
            record("PATCH", "/sources/{id}/score", 0, 0, False, [],
                   [], "no source_id available (sources empty)")

        # 13. GET /reports/{id}/export
        report_id = session_id
        status, _raw, elapsed, err = _request(
            "GET", base + f"/reports/{report_id}/export?format=md", None, timeout
        )
        ok = 200 <= status < 300
        if err:
            ok = False
        record("GET", "/reports/{id}/export", status, elapsed, ok, [], [])

    total_elapsed = time.monotonic() - t0

    # ---------------------------------------------------------------
    # Print report
    # ---------------------------------------------------------------
    passed = sum(1 for r in results if r["ok"])
    total = len(results)

    col_endpoint = 40
    header = (
        f"{'Endpoint':<{col_endpoint}}  {'Status':<6}  {'Keys':<6}  {'Time':<6}"
    )
    sep = (
        f"{'-' * (col_endpoint - 2):<{col_endpoint}}  "
        f"{'-' * 6:<6}  {'-' * 6:<6}  {'-' * 6:<6}"
    )

    print()
    print("Healthcheck Report")
    print("=" * 18)
    print(f"Base URL: {base}")
    print(f"Started: {started.isoformat()}")
    print()
    print(header)
    print(sep)

    for r in results:
        label = f"{r['method']} {r['path']}"
        status_str = "PASS" if r["ok"] else "FAIL"
        if r["missing"]:
            keys_str = f"miss({len(r['missing'])})"
        elif r["present"]:
            keys_str = "all"
        else:
            keys_str = "n/a"
        time_str = f"{r['elapsed']:.2f}s" if r["elapsed"] > 0 else "-"
        note = f"  [{r['note']}]" if r["note"] else ""
        print(f"{label:<{col_endpoint}}  {status_str:<6}  {keys_str:<6}  {time_str:<6}{note}")

        if verbose:
            if r["present"]:
                print(f"  {'':>{col_endpoint - 2}}  present: {', '.join(r['present'])}")
            if r["missing"]:
                print(f"  {'':>{col_endpoint - 2}}  MISSING: {', '.join(r['missing'])}")

    print()
    print(f"Result: {passed}/{total} endpoints passed ({total_elapsed:.1f}s total)")
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
