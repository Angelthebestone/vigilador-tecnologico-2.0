"""Resolución del `database_url` REAL para los tests enterprise.

`tests/conftest.py` (del 2.0) hace
`os.environ.setdefault("VT_DATABASE_URL", "...postgres:postgres@...")` con una
contraseña placeholder, que gana sobre el `.env` real y rompe la autenticación
contra PostgreSQL en los tests que sí tocan la DB. Para no modificar ese
conftest compartido, los tests enterprise resuelven la URL directamente desde
el `.env` con `dotenv_values`, cayendo al entorno solo si no está en el archivo.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values


def resolve_database_url() -> str | None:
    env_path = Path(".env")
    if env_path.exists():
        url = dotenv_values(env_path).get("VT_DATABASE_URL")
        if url:
            return url
    return os.environ.get("VT_DATABASE_URL")
