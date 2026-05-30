"""Phase 5 — Enterprise ingestion sync: incremental document synchronization."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from vigilancia_multiagente.enterprise.dreaming.models import (
    DreamingContext,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.ports import (
    IngestionConnector,
    SyncCheckpointStore,
)

logger = logging.getLogger(__name__)


class IngestionSyncPhase:
    """Iterates configured connectors, syncs only new/modified documents."""

    def __init__(
        self,
        connectors: list[IngestionConnector],
        checkpoint_store: SyncCheckpointStore,
    ) -> None:
        self._connectors = connectors
        self._checkpoint_store = checkpoint_store

    @property
    def name(self) -> str:
        return "ingestion_sync"

    async def execute(self, context: DreamingContext) -> PhaseResult:
        t0 = time.perf_counter()
        total_indexed = 0
        connector_errors: list[str] = []

        for connector in self._connectors:
            try:
                last_sync = await self._checkpoint_store.get_last_sync(connector.connector_id)
                documents = await connector.fetch_new_documents(since=last_sync)
                if documents:
                    indexed = await connector.index_documents(documents)
                    total_indexed += indexed
                await self._checkpoint_store.set_last_sync(
                    connector.connector_id, datetime.now(UTC)
                )
            except Exception as exc:
                msg = f"Connector {connector.connector_id}: {type(exc).__name__}: {exc}"
                logger.error(msg)
                connector_errors.append(msg)

        duration_ms = (time.perf_counter() - t0) * 1000
        metrics: dict[str, Any] = {
            "connectors_total": len(self._connectors),
            "documents_indexed": total_indexed,
            "connector_errors": len(connector_errors),
        }
        return PhaseResult(
            phase_name=self.name,
            status=PhaseStatus.SUCCESS,
            duration_ms=duration_ms,
            metrics_dict=metrics,
        )
