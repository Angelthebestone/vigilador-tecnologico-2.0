"""Config local de los tests enterprise.

En Windows, pytest-asyncio levanta por defecto el `ProactorEventLoop`, que es
incompatible con asyncpg (necesita el `SelectorEventLoop`): las conexiones se
cierran "in the middle of operation". Forzamos la política Selector para estos
tests, que tocan PostgreSQL vía asyncpg. No afecta al resto de la suite.
"""

from __future__ import annotations

import asyncio
import sys

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()
