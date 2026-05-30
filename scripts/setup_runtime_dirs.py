"""Create runtime directories under ``~/.vigilador/`` (Spec 021 Phase 0 / T005).

Idempotent. Creates the directories with mode 0o700 on POSIX (best-effort on
Windows; permissions are handled by the OS user profile). Reads paths from
``config/settings.py`` so the script always reflects the configured layout.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from vigilancia_multiagente.config.settings import get_settings


def expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def ensure_dir(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        # On POSIX, restrict to owner. Failure here is a real problem (read-only
        # filesystem, missing permissions) — propagate per constitucion #4.
        os.chmod(path, 0o700)
    return f"{'created' if not any(path.iterdir()) else 'exists '} {path}"


def main() -> int:
    settings = get_settings()
    targets = [
        Path("~/.vigilador/credentials"),
        Path(settings.mcp_logs_dir),
        Path("~/.vigilador/memories"),
        Path(settings.audit_dir),
        Path("~/.vigilador/audit"),  # parent for events_<date>.jsonl
        Path("~/.vigilador/turbovec"),
    ]
    print(f"Setting up runtime dirs under {expand('~/.vigilador').as_posix()}")
    for raw in targets:
        target = expand(str(raw))
        print(f"  {ensure_dir(target)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
