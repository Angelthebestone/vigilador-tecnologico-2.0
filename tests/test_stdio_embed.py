"""Test STDIO providers with correct commands + Embedding with new key."""
import sys, asyncio, time
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from vigilancia_multiagente.api.dependencies import get_settings

settings = get_settings()

def _unwrap(val):
    if val is None: return ""
    if hasattr(val, "get_secret_value"):
        return val.get_secret_value()
    return str(val).strip()

import httpx

# ── STDIO: check if npx/uvx/uv are available ────────────────────

import subprocess



# Proper time measurement
def test_stdio(name, cmd_parts):
    try:
        t0 = time.time()
        r = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=30)
        ms = int((time.time() - t0) * 1000)
        out = r.stdout[:200].replace("\n", " ").strip()
        err = r.stderr[:200].replace("\n", " ").strip()
        return (name, f"exit={r.returncode} ({ms}ms)", out or err)
    except FileNotFoundError:
        return (name, "SKIP", f"'{cmd_parts[0]}' not found on PATH")
    except subprocess.TimeoutExpired:
        return (name, "TIMEOUT", "30s")
    except Exception as e:
        return (name, "FAIL", str(e)[:150])

# ── EMBEDDING ────────────────────────────────────────────────────

async def test_embedding():
    key = _unwrap(getattr(settings, "embedding_api_key", None))
    print(f"\n--- EMBEDDING (GEMINI) ---")
    print(f"  Key length: {len(key)}")
    
    # Test with x-goog-api-key header (correct method per docs)
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={"model": "models/gemini-embedding-2", "content": {"parts": [{"text": "test"}]}},
        )
    ms = int((time.time() - t0) * 1000)
    print(f"  x-goog-api-key header: HTTP {r.status_code} ({ms}ms)")
    if r.status_code == 200:
        data = r.json()
        vals = data.get("embedding", {}).get("values", [])
        print(f"  OK! embedding dim={len(vals)}, first 5={vals[:5]}")
    else:
        print(f"  Error: {r.text[:200]}")

asyncio.run(test_embedding())

print()
print("--- STDIO PROVIDERS ---")
tests = [
    ("Brave", ["npx", "-y", "@brave/brave-search-mcp-server", "--help"]),
    ("Firecrawl", ["npx", "-y", "firecrawl-mcp", "--help"]),
    ("Fetch", ["uvx", "mcp-server-fetch", "--help"]),
    ("ArXiv", ["uvx", "arxiv-mcp-server", "--help"]),
]

# Also check python-based Scholar
import os
python_exe = sys.executable
tests.append(("Scholar (python)", [python_exe, "-m", "google_scholar_server", "--help"] if False else None))

for name, cmd in tests:
    if cmd is None:
        print(f"  [SKIP] Scholar: no --help flag available, runs as server")
        continue
    result = test_stdio(name, cmd)
    icon = {"SKIP": "[SKIP]", "TIMEOUT": "[TIMEOUT]", "FAIL": "[FAIL]"}.get(result[1].split()[0].split("=")[0], "[OK]")
    if result[1].startswith("exit=0") or result[1].startswith("exit=1") or result[1].startswith("exit=2"):
        # --help often returns exit=0 or exit=1
        print(f"  {icon:7s} {name:15s} {result[1]:20s} {result[2][:120]}")
    else:
        print(f"  {icon:7s} {name:15s} {result[1]:20s} {result[2][:120]}")
