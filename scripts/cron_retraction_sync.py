#!/usr/bin/env python3
"""Cron job diario para sincronizar retractaciones — spec 007 T059.

Invocar desde cron / systemd timer / Kubernetes CronJob::

    python scripts/cron_retraction_sync.py

Loggea metricas: nuevos registros, tamano del cache, duracion.
Requiere VT_RETRACTION_WATCH_CSV_URL configurado en .env.
"""

from __future__ import annotations

import asyncio
import logging
import time

from vigilancia_multiagente.infra.retraction.retraction_watch_csv import (
    RetractionWatchCSVAdapter,
)

logger = logging.getLogger(__name__)


async def _run() -> None:
    adapter = RetractionWatchCSVAdapter()
    start = time.monotonic()
    try:
        new_count = await adapter.daily_sync()
        elapsed = time.monotonic() - start
        logger.info(
            "RetractionWatch daily sync complete: %d new records, cache=%d, duration=%.2fs",
            new_count,
            len(adapter._cache),  # type: ignore[arg-type]
            elapsed,
        )
    except Exception as exc:
        logger.error("RetractionWatch daily sync failed: %s", exc, exc_info=True)
    finally:
        await adapter.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(_run())


if __name__ == "__main__":
    main()
