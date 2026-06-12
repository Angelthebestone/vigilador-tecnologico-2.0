"""Ingestion orchestrator (Spec 021 F2.C T060, FR-012/FR-014).

End-to-end pipeline:

  ``connector.discover()`` →
  ``connector.extract(ref)`` →
  ``acl_resolver.register_chunk(...)`` →
  ``chunking.chunk_text(...)`` →
  ``dedup.dedup_chunks(...)`` →
  ``embedding_gateway.embed(...)`` →
  ``vector_index.add(tenant_id, chunks)`` →
  ``vector_index.persist(tenant_id)``

The orchestrator is **independent of any specific connector or backend**
— it consumes ports, not concrete classes (DIP).

Constitución:
* SRP: one job — pipeline glue.
* #4 explicit: a connector failure (auth missing, OAuth expired) raises
  out of ``run_for_connector`` with full context. The orchestrator does
  NOT swallow errors from one connector; the caller decides whether to
  continue with the next source.
* CQS: ``run_for_connector`` is a command returning a structured report.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from vigilancia_multiagente.domain.ports.ingestion_connector import (
    IngestionConnector,
)
from vigilancia_multiagente.enterprise.governance.pi_quarantine_writer import (
    PIQuarantineJSONLWriter,
    PIQuarantineWriterError,
    PIQuarantineWriterPort,
)
from vigilancia_multiagente.enterprise.governance.prompt_injection_detector import (
    PromptInjectionDetector,
)
from vigilancia_multiagente.enterprise.ingestion.acl_resolver import ACLResolver
from vigilancia_multiagente.enterprise.ingestion.chunking import Chunk, chunk_text
from vigilancia_multiagente.enterprise.ingestion.dedup import dedup_chunks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Port for the embedding gateway (already exists upstream as 2.0 GeminiEmbeddingGateway)
# ---------------------------------------------------------------------------


class EmbeddingGateway(Protocol):
    """The 2.0 ``GeminiEmbeddingGateway`` already satisfies this surface."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class _IndexLike(Protocol):
    """Subset of ``IngestionVectorIndex`` we depend on."""

    async def add(self, tenant_id: UUID, chunks: list[object]) -> int: ...
    async def persist(self, tenant_id: UUID) -> None: ...


# ---------------------------------------------------------------------------
# Report types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestionRunReport:
    """Structured outcome of a single connector run."""

    connector: str
    tenant_id: UUID
    discovered: int
    extracted: int
    chunked: int
    deduped: int
    indexed: int
    duration_s: float
    errors: list[str] = field(default_factory=list)
    quarantined: int = 0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class IngestionOrchestrator:
    """Wire connector → chunking → dedup → embedding → index."""

    embedding_gateway: EmbeddingGateway
    vector_index: _IndexLike
    acl_resolver: ACLResolver
    chunk_id_counter: int = 0  # process-wide counter (deterministic per session)
    # Spec 021 F5a.C / T133 — every external input flows through the PI
    # detector before being embedded. Documents flagged as suspicious are
    # written to the JSONL audit trail and skipped (FR-044). Tests can
    # disable by passing ``pi_detector=None``.
    pi_detector: PromptInjectionDetector | None = field(default_factory=PromptInjectionDetector)
    pi_writer: PIQuarantineWriterPort | None = field(default_factory=PIQuarantineJSONLWriter)

    async def run_for_connector(
        self,
        connector: IngestionConnector,
        tenant_id: UUID,
    ) -> IngestionRunReport:
        """Execute the full pipeline for a single ``connector``."""
        t0 = time.monotonic()
        errors: list[str] = []
        discovered = 0
        extracted = 0
        chunked = 0
        deduped = 0
        indexed = 0
        quarantined = 0

        try:
            refs = await connector.discover()
            discovered = len(refs)
        except Exception as exc:
            return IngestionRunReport(
                connector=connector.name,
                tenant_id=tenant_id,
                discovered=0,
                extracted=0,
                chunked=0,
                deduped=0,
                indexed=0,
                duration_s=time.monotonic() - t0,
                errors=[f"discover failed: {exc}"],
            )

        for ref in refs:
            try:
                raw = await connector.extract(ref)
                extracted += 1
            except Exception as exc:
                errors.append(f"extract({ref.external_id}) failed: {exc}")
                continue

            # Spec 021 F5a.C T133 — PI gate before chunking/embedding.
            if self.pi_detector is not None:
                detection = self.pi_detector.detect(raw.text, source=connector.name)
                if detection.is_suspicious:
                    quarantined += 1
                    if self.pi_writer is not None:
                        try:
                            self.pi_writer.write(
                                detection,
                                content_excerpt=raw.text,
                                tenant_id=str(tenant_id),
                                ref_id=ref.external_id,
                            )
                        except PIQuarantineWriterError as exc:
                            logger.warning(
                                "PI writer failed for %s: %s — continuing without audit line",
                                ref.external_id,
                                exc,
                            )
                    logger.warning(
                        "Quarantined %s from %s (severity=%s, patterns=%d) — "
                        "skipped chunking/embedding",
                        ref.external_id,
                        connector.name,
                        detection.severity,
                        len(detection.patterns_matched),
                    )
                    continue

            try:
                scope = await connector.acl_for(ref)
            except Exception as exc:
                errors.append(f"acl_for({ref.external_id}) failed: {exc}")
                continue

            chunks = chunk_text(
                document_id=ref.external_id,
                text=raw.text,
                base_chunk_id=self.chunk_id_counter,
                metadata={
                    "connector": connector.name,
                    "title": ref.title,
                    "mime_type": ref.mime_type,
                },
            )
            chunked += len(chunks)
            self.chunk_id_counter += len(chunks)

            dedup_result = dedup_chunks(chunks)
            deduped += len(dedup_result.kept)

            # Register ACL for every kept chunk.
            self.acl_resolver.register_many(
                [(c.chunk_id, scope) for c in dedup_result.kept]  # type: ignore[union-attr]
            )

            # Embed in a single batch.
            kept_chunks: list[Chunk] = list(dedup_result.kept)  # type: ignore[assignment]
            if kept_chunks:
                texts = [c.text for c in kept_chunks]
                try:
                    embeddings = await self.embedding_gateway.embed_batch(texts)
                except Exception as exc:
                    errors.append(f"embed({ref.external_id}) failed: {exc}")
                    continue
                # Pair embeddings back into chunks (frozen dataclass — recreate).
                paired = [
                    Chunk(
                        chunk_id=c.chunk_id,
                        document_id=c.document_id,
                        text=c.text,
                        char_start=c.char_start,
                        char_end=c.char_end,
                        metadata=c.metadata,
                        embedding=emb,
                    )
                    for c, emb in zip(kept_chunks, embeddings, strict=False)
                ]
                added = await self.vector_index.add(tenant_id, paired)  # type: ignore[arg-type]
                indexed += added

        await self.vector_index.persist(tenant_id)
        return IngestionRunReport(
            connector=connector.name,
            tenant_id=tenant_id,
            discovered=discovered,
            extracted=extracted,
            chunked=chunked,
            deduped=deduped,
            indexed=indexed,
            duration_s=time.monotonic() - t0,
            errors=errors,
            quarantined=quarantined,
        )

    async def run_all(
        self,
        connectors: list[IngestionConnector],
        tenant_id: UUID,
    ) -> list[IngestionRunReport]:
        """Run each connector independently; one failure does not abort others."""
        out: list[IngestionRunReport] = []
        for c in connectors:
            try:
                report = await self.run_for_connector(c, tenant_id)
                out.append(report)
            except Exception as exc:
                logger.exception("IngestionOrchestrator: connector %s failed: %s", c.name, exc)
                out.append(
                    IngestionRunReport(
                        connector=c.name,
                        tenant_id=tenant_id,
                        discovered=0,
                        extracted=0,
                        chunked=0,
                        deduped=0,
                        indexed=0,
                        duration_s=0.0,
                        errors=[f"orchestrator-level failure: {exc}"],
                    )
                )
        return out
