"""Test real MCP provider connectivity using backend Settings."""
import os, sys, json, subprocess, asyncio, time
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, UTC

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Use backend Settings to load .env
try:
    from vigilancia_multiagente.api.dependencies import get_settings
    settings = get_settings()
    # Extract keys without displaying them
    KEYS = {
        "TAVILY": str(getattr(settings, "tavily_api_key", "") or ""),
        "EXA": str(getattr(settings, "exa_api_key", "") or ""),
        "JINA": str(getattr(settings, "jina_api_key", "") or ""),
        "SERPER": str(getattr(settings, "serper_api_key", "") or ""),
        "EMBEDDING": str(getattr(settings, "embedding_api_key", "") or ""),
    }
except Exception as e:
    print(f"Settings load error: {e}")
    KEYS = {k: "" for k in ["TAVILY", "EXA", "JINA", "BRAVE", "FIRECRAWL", "SERPER", "EMBEDDING"]}

# ── HTTP Providers ──────────────────────────────────────────────

async def test_tavily():
    key = KEYS.get("TAVILY", "")
    if not key:
        return ("TAVILY", "SKIP", "No API key")
    import httpx
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": "AI manufacturing 2024", "search_depth": "basic", "max_results": 3},
        )
    ms = int((time.time() - t0) * 1000)
    if r.status_code == 200:
        data = r.json()
        n = len(data.get("results", []))
        return ("TAVILY", f"OK ({ms}ms, {n} results)", "")
    return ("TAVILY", "FAIL", f"HTTP {r.status_code}")

async def test_exa():
    key = KEYS.get("EXA", "")
    if not key:
        return ("EXA", "SKIP", "No API key")
    import httpx
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            "https://api.exa.ai/search",
            headers={"x-api-key": key},
            params={"query": "AI manufacturing trends", "numResults": 3, "type": "auto"},
        )
    ms = int((time.time() - t0) * 1000)
    if r.status_code == 200:
        data = r.json()
        n = len(data.get("results", []))
        return ("EXA", f"OK ({ms}ms, {n} results)", "")
    return ("EXA", "FAIL", f"HTTP {r.status_code}")

async def test_jina_read():
    t0 = time.time()
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get("https://r.jina.ai/http://example.com")
    ms = int((time.time() - t0) * 1000)
    if r.status_code == 200:
        return ("JINA_READ", f"OK ({ms}ms, {len(r.text)} chars)", "")
    return ("JINA_READ", "FAIL", f"HTTP {r.status_code}")

async def test_jina_search():
    key = KEYS.get("JINA", "")
    if not key:
        return ("JINA_SEARCH", "SKIP", "No API key")
    t0 = time.time()
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            "https://s.jina.ai/",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"q": "AI manufacturing 2024"},
        )
    ms = int((time.time() - t0) * 1000)
    if r.status_code == 200:
        data = r.json()
        n = len(data.get("data", []))
        return ("JINA_SEARCH", f"OK ({ms}ms, {n} results)", "")
    return ("JINA_SEARCH", "FAIL", f"HTTP {r.status_code}")

async def test_serper():
    key = KEYS.get("SERPER", "")
    if not key:
        return ("SERPER", "SKIP", "No API key")
    import httpx
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": "AI manufacturing", "num": 3},
        )
    ms = int((time.time() - t0) * 1000)
    if r.status_code == 200:
        data = r.json()
        n = len(data.get("organic", []))
        return ("SERPER", f"OK ({ms}ms, {n} organic)", "")
    return ("SERPER", "FAIL", f"HTTP {r.status_code}")

async def test_embedding():
    key = KEYS.get("EMBEDDING", "")
    if not key:
        return ("EMBEDDING", "SKIP", "No API key")
    import httpx
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={key}",
            json={"model": "models/gemini-embedding-2", "content": {"parts": [{"text": "test"}]}},
        )
    ms = int((time.time() - t0) * 1000)
    if r.status_code == 200:
        return ("EMBEDDING", f"OK ({ms}ms)", "")
    body = r.text[:80].replace("\n", " ")
    return ("EMBEDDING", "FAIL", f"HTTP {r.status_code}: {body}")

# ── STDIO Providers ─────────────────────────────────────────────

def test_stdio(name: str, *cmd: str) -> tuple:
    try:
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ms = int((time.time() - t0) * 1000)
        if r.returncode == 0:
            return (name, f"OK ({ms}ms, exit 0)", "")
        return (name, "FAIL", f"exit {r.returncode}: {r.stderr[:120]}")
    except FileNotFoundError:
        return (name, "SKIP", "Binary not found")
    except subprocess.TimeoutExpired:
        return (name, "FAIL", "Timeout 15s")
    except Exception as e:
        return (name, "FAIL", str(e)[:120])

# ── Main ────────────────────────────────────────────────────────

async def main():
    print(f"\n{'='*60}")
    print(f"  MCP PROVIDER CONNECTIVITY TEST - {datetime.now(UTC).isoformat()}")
    print(f"{'='*60}\n")

    http_tests = [
        test_tavily(),
        test_exa(),
        test_jina_read(),
        test_jina_search(),
        test_serper(),
        test_embedding(),
    ]

    stdio_tests = [
        test_stdio("BRAVE", "npx", "-y", "@anthropic-ai/claude-code", "--help"),
        test_stdio("FIRECRAWL", "npx", "-y", "firecrawl-mcp", "--help"),
        test_stdio("SCHOLAR", "uvx", "google-scholar-mcp", "--help") if sys.platform != "win32" else ("SCHOLAR", "SKIP", "uvx not tested on Windows"),
        test_stdio("ARXIV", "npx", "-y", "arxiv-mcp", "--help"),
        test_stdio("FETCH", "npx", "-y", "@anthropic-ai/claude-code", "--help"),
    ]

    print("-- HTTP Providers --")
    for coro in asyncio.as_completed(http_tests):
        name, status, detail = await coro
        icon = {"OK": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status.split()[0], "[?]")
        print(f"  {icon:7s} {name:15s} {status:40s} {detail}")

    print("\n-- STDIO Providers --")
    for name, status, detail in stdio_tests:
        icon = {"OK": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status.split()[0], "[?]")
        print(f"  {icon:7s} {name:15s} {status:40s} {detail}")

    print(f"\n{'-'*60}")
    print("  Done.")

if __name__ == "__main__":
    asyncio.run(main())
