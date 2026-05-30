"""PIInterceptor — intercepta contenido entrante y cuarentena si PI detectado (FR-006..FR-008)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from vigilancia_multiagente.enterprise.governance.detection_result import DetectionResult
from vigilancia_multiagente.enterprise.governance.pi_quarantine_repository import (
    PIQuarantineRepository,
)
from vigilancia_multiagente.enterprise.governance.prompt_injection_detector import (
    PromptInjectionDetector,
)

logger = logging.getLogger(__name__)

_AUDIT_DIR = Path.home() / ".vigilador" / "audit"
_EXCERPT_MAX = 500


@dataclass(frozen=True, slots=True)
class InterceptionResult:
    """Resultado de la intercepción."""

    blocked: bool
    content: str | None
    detection: DetectionResult | None = None
    quarantine_id: UUID | None = None


class PIInterceptor:
    """Hook de intercepción PI (FR-006..FR-008, FR-010, FR-013..FR-015)."""

    def __init__(
        self,
        detector: PromptInjectionDetector,
        repository: PIQuarantineRepository,
        audit_dir: Path | None = None,
    ) -> None:
        self._detector = detector
        self._repository = repository
        self._audit_dir = audit_dir or _AUDIT_DIR

    async def intercept(
        self, content: str, source: str, tenant_id: UUID
    ) -> InterceptionResult:
        """Intercepta contenido. Si PI detectado: cuarentena + audit + métrica."""
        detection = self._detector.detect(content, source)

        if not detection.is_suspicious:
            return InterceptionResult(blocked=False, content=content)

        # FR-010: excerpt truncado a 500 chars
        excerpt = content[:_EXCERPT_MAX]

        # Persistir en cuarentena (FR-009)
        quarantine_id = await self._repository.quarantine(
            tenant_id=tenant_id,
            source=source,
            content_excerpt=excerpt,
            detected_patterns=detection.patterns_matched,
            severity=detection.severity,
        )

        # FR-014: audit JSONL
        self._write_audit(tenant_id, source, detection, excerpt)

        # FR-015: métrica Prometheus
        self._increment_metric(source, detection.severity)

        logger.warning(
            "PI detected and quarantined: source=%s severity=%s id=%s",
            source,
            detection.severity,
            quarantine_id,
        )

        return InterceptionResult(
            blocked=True,
            content=None,
            detection=detection,
            quarantine_id=quarantine_id,
        )

    def _write_audit(
        self, tenant_id: UUID, source: str, detection: DetectionResult, excerpt: str
    ) -> None:
        """FR-014: escribe evento en JSONL."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        audit_file = self._audit_dir / f"pi_quarantine_{date_str}.jsonl"
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_id),
            "source": source,
            "severity": detection.severity,
            "patterns_matched": detection.patterns_matched,
            "excerpt": excerpt[:200],
        }
        with audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _increment_metric(self, source: str, severity: str) -> None:
        """FR-015: incrementa counter Prometheus."""
        try:
            from vigilancia_multiagente.enterprise.observability.metrics import (
                pi_quarantined_total,
            )
            pi_quarantined_total.labels(source=source, severity=severity).inc()
        except ImportError:
            logger.debug("Prometheus metrics not available; skipping metric increment")
