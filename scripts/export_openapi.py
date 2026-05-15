"""Export the FastAPI OpenAPI schema to a static file.

The frontend generates its API client and types from this file, so it is the
frozen contract between backend and frontend. Regenerate it whenever routes or
response models change:

    python scripts/export_openapi.py

Output: ``openapi.json`` at the repository root (override with one argument).
"""

import json
import sys
from pathlib import Path

from vigilancia_multiagente.api.app import create_app

_DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


def export(output: Path = _DEFAULT_OUTPUT) -> Path:
    schema = create_app().openapi()
    output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_OUTPUT
    written = export(target)
    print(f"OpenAPI schema written to {written} ({written.stat().st_size} bytes)")
